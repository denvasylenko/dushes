import Foundation
import Observation

/// One thing in the chat log.
public enum ChatItem: Identifiable, Equatable, Sendable {
    case user(id: String, text: String)
    case assistant(id: String, text: String, done: Bool)
    case step(id: String, name: String, state: StepState)
    case card(ChatCard)
    case host(id: String, name: String, value: JSONValue)      // a CUSTOM the host draws (its own cards)

    public var id: String {
        switch self {
        case .user(let id, _), .assistant(let id, _, _), .step(let id, _, _), .host(let id, _, _): id
        case .card(let c): "card-" + c.id
        }
    }
}

public enum StepState: Equatable, Sendable { case running, done, failed }

/// A card that waits for an answer (`ask`, `confirm`, …). `status` follows the run, not the tap: a refused answer
/// (`card_result not_accepted`) puts it back to `open` (CONTRACT.md, «what a second client usually gets wrong», 2).
public struct ChatCard: Identifiable, Equatable, Sendable {
    public enum Status: Equatable, Sendable { case open, sending, answered, closed, refused(String) }
    public var id: String
    public var type: String
    public var body: JSONValue
    public var status: Status = .open

    public var question: String? { body["question"]?.string ?? body["title"]?.string ?? body["message"]?.string }
    public var options: [(id: String, label: String)] {
        (body["options"]?.array ?? []).compactMap { o in
            guard let id = o["id"]?.string ?? o["value"]?.string else { return nil }
            return (id, o["label"]?.string ?? id)
        }
    }

    public static func == (a: ChatCard, b: ChatCard) -> Bool {
        a.id == b.id && a.type == b.type && a.body == b.body && a.status == b.status
    }
}

/// The chat: sends runs, applies the events, keeps the log. One run at a time; a new message while a card waits
/// closes that card. Thread restore (`GET …/threads/{id}`) is the host's call into `restore(_:)`.
@MainActor
@Observable
public final class ChatStore {
    public private(set) var items: [ChatItem] = []
    public private(set) var suggestions: [String] = []
    public private(set) var running = false
    public private(set) var error: String?
    public private(set) var language: String?
    public var threadId: String

    /// What this client draws (`forwardedProps.capabilities`): the server leaves out the rest.
    public static let capabilities: [JSONValue] = ["ask", "confirm"]

    /// A CUSTOM name the host draws itself (its cards), and what it does with a `site_directive`.
    public var hostEvents: Set<String> = []
    public var onDirective: (@MainActor (JSONValue) -> Void)?
    /// `state` and extra `forwardedProps` the host adds to each run (the page, the language, the voice flag).
    public var state: @MainActor () -> JSONValue = { .object([:]) }
    public var extraProps: @MainActor () -> [String: JSONValue] = { [:] }

    private let transport: AGUITransport
    private var history: [RunAgentInput.Message] = []
    private var task: Task<Void, Never>?
    private var tools: [String: Int] = [:]          // toolCallId → index in items

    public init(transport: AGUITransport, threadId: String = UUID().uuidString) {
        self.transport = transport
        self.threadId = threadId
    }

    // MARK: Sending

    public func send(_ text: String) {
        let text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !running else { return }
        closeOpenCards()
        let message = RunAgentInput.Message(role: "user", content: text)
        history.append(message)
        items.append(.user(id: message.id, text: text))
        start(props: [:])
    }

    /// The answer of a card goes as the next run's `resume` (legacy mode: `forwardedProps.command.resume`).
    public func answer(_ card: ChatCard, with resume: JSONValue) {
        guard !running, let i = cardIndex(card.id) else { return }
        if case .card(var c) = items[i] { c.status = .sending; items[i] = .card(c) }
        start(props: ["command": ["resume": resume]], answering: card.id)
    }

    public func choose(_ card: ChatCard, option id: String) {
        answer(card, with: ["answer": ["ids": [.string(id)]]])
    }

    public func confirm(_ card: ChatCard, _ accepted: Bool) {
        answer(card, with: ["accepted": .bool(accepted)])
    }

    public func tapSuggestion(_ text: String) { send(text) }

    public func retry() {
        guard !running, history.last?.role == "user" else { return }
        error = nil
        start(props: [:])
    }

    public func stop() {
        task?.cancel()
        task = nil
        running = false
    }

    // MARK: The run

    private func start(props: [String: JSONValue], answering cardId: String? = nil) {
        error = nil
        suggestions = []
        running = true
        var forwarded = extraProps()
        forwarded["capabilities"] = .array(Self.capabilities)
        for (k, v) in props { forwarded[k] = v }
        let input = RunAgentInput(threadId: threadId, messages: history, state: state(),
                                  forwardedProps: .object(forwarded))
        let stream = transport.run(input)
        task = Task { [weak self] in
            var sawTerminal = false
            do {
                for try await event in stream {
                    guard let self else { return }
                    self.apply(event)
                    if event.isTerminal { sawTerminal = true }
                }
                if !sawTerminal { self?.fail(String(localized: "The answer was cut off.", bundle: .module)) }
            } catch is CancellationError {
            } catch {
                self?.fail(Self.human(error))
            }
            guard let self else { return }
            self.running = false
            if let cardId, let i = self.cardIndex(cardId), case .card(var c) = self.items[i], c.status == .sending {
                c.status = .answered
                self.items[i] = .card(c)
            }
            self.finishSteps()
        }
    }

    /// Applies one event to the log. Public so a host can feed a restored stream or a test can drive it.
    public func apply(_ event: AGUIEvent) {
        switch event {
        case .runStarted(let thread, _):
            if let thread, !thread.isEmpty { threadId = thread }
        case .textStart(let id, _):
            if itemIndex(id) == nil { items.append(.assistant(id: id, text: "", done: false)) }
        case .textContent(let id, let delta):
            if let i = itemIndex(id), case .assistant(_, let text, _) = items[i] {
                items[i] = .assistant(id: id, text: text + delta, done: false)
            } else {
                items.append(.assistant(id: id, text: delta, done: false))
            }
        case .textEnd(let id):
            if let i = itemIndex(id), case .assistant(_, let text, _) = items[i] {
                items[i] = .assistant(id: id, text: text, done: true)
                history.append(.init(id: id, role: "assistant", content: text))
            }
        case .toolStart(let id, let name, _):
            tools[id] = items.count
            items.append(.step(id: "tool-" + id, name: name, state: .running))
        case .toolResult(let id, let content):
            if let i = tools[id], i < items.count, case .step(let sid, let name, _) = items[i] {
                let failed = content.lowercased().contains(" failed")
                items[i] = .step(id: sid, name: name, state: failed ? .failed : .done)
            }
        case .toolArgs, .toolEnd, .other:
            break
        case .custom(let name, let value):
            custom(name, value)
        case .runFinished(let outcome):
            for interrupt in outcome?["interrupts"]?.array ?? [] {
                if let body = interrupt["value"] ?? interrupt["payload"] { addCard(body) }
            }
        case .runError(let message, _):
            fail(message.isEmpty ? String(localized: "Something went wrong.", bundle: .module) : message)
        }
    }

    private func custom(_ name: String, _ value: JSONValue) {
        switch name {
        case "text_retract":
            if let id = value["messageId"]?.string, let i = itemIndex(id) {
                items.remove(at: i)
                history.removeAll { $0.id == id }
                tools = tools.mapValues { $0 > i ? $0 - 1 : $0 }
            }
        case "on_interrupt":
            if let text = value.string, let body = JSONValue.parse(text) { addCard(body) }
            else if case .object = value { addCard(value) }
        case "card_result":
            if value["status"]?.string == "not_accepted", let id = value["card_id"]?.string, let i = cardIndex(id),
               case .card(var c) = items[i] {
                c.status = .refused(value["reason"]?.string ?? "")
                items[i] = .card(c)
            }
        case "suggestions":
            suggestions = (value["items"]?.array ?? []).compactMap { $0.string ?? $0["text"]?.string ?? $0["label"]?.string }
        case "language":
            language = value["lang"]?.string
        case "site_directive":
            onDirective?(value)
        default:
            if hostEvents.contains(name) {
                items.append(.host(id: "host-\(items.count)-\(name)", name: name, value: value))
            }
            // any other CUSTOM is ignored: a client must not fail on a name it does not know
        }
    }

    private func addCard(_ body: JSONValue) {
        guard let type = body["type"]?.string else { return }
        let id = body["card_id"]?.string ?? UUID().uuidString
        let card = ChatCard(id: id, type: type, body: body)
        if let i = cardIndex(id) { items[i] = .card(card) } else { items.append(.card(card)) }
    }

    private func fail(_ message: String) {
        error = message
        running = false
    }

    private func closeOpenCards() {
        for i in items.indices {
            if case .card(var c) = items[i], c.status == .open || { if case .refused = c.status { true } else { false } }() {
                c.status = .closed
                items[i] = .card(c)
            }
        }
    }

    private func finishSteps() {
        for i in items.indices {
            if case .step(let id, let name, .running) = items[i] { items[i] = .step(id: id, name: name, state: .done) }
        }
    }

    private func itemIndex(_ id: String) -> Int? { items.firstIndex { $0.id == id } }
    private func cardIndex(_ id: String) -> Int? { items.firstIndex { $0.id == "card-" + id } }

    private static func human(_ error: Error) -> String {
        if let e = error as? AGUIError, case .http(let status) = e, status == 429 {
            return String(localized: "Too many questions for now. Try again later.", bundle: .module)
        }
        if (error as? URLError) != nil {
            return String(localized: "No connection. Try again.", bundle: .module)
        }
        return String(localized: "Something went wrong.", bundle: .module)
    }
}
