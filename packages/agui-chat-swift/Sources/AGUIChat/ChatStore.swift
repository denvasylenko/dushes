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
    public static let capabilities: [JSONValue] = ["ask", "confirm"]   // set_fields is not switched by capabilities

    /// A CUSTOM name the host draws itself (its cards), and what it does with a `site_directive`.
    public var hostEvents: Set<String> = []
    public var onDirective: (@MainActor (JSONValue) -> Void)?
    /// Applies a field-change card through the host's form (`{name: value}` → the form's new `config`). With it the
    /// store draws `set_fields` itself: the client never writes the config on its own authority (CONTRACT.md).
    public var applyFields: (@MainActor ([String: JSONValue]) async throws -> JSONValue)?
    private var handoffAfterRun = false
    /// `state` and extra `forwardedProps` the host adds to each run (the page, the language, the voice flag).
    public var state: @MainActor () -> JSONValue = { .object([:]) }
    public var extraProps: @MainActor () -> [String: JSONValue] = { [:] }

    private let transport: AGUITransport
    /// The person's last message, for «Try again».
    private var lastUser: RunAgentInput.Message?
    /// The last messages of the conversation. The UI and site agents keep the thread by `threadId` and read only the
    /// last user message; the docs assistant reads the last few — so a run sends at most the last 8 (review, 1).
    private var recent: [RunAgentInput.Message] = []
    /// A message typed while a run is going: sent when it ends, as the widget does.
    public private(set) var queued: String?
    private var finished = false                    // this run reached RUN_FINISHED
    private var busy = false                        // RUN_ERROR code "busy": the thread's previous turn still runs
    private var task: Task<Void, Never>?
    private var tools: [String: Int] = [:]          // toolCallId → index in items

    public init(transport: AGUITransport, threadId: String = UUID().uuidString) {
        self.transport = transport
        self.threadId = threadId
    }

    // MARK: Sending

    public func send(_ text: String) {
        let text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        if running { queued = text; return }
        closeOpenCards()
        let message = RunAgentInput.Message(role: "user", content: text)
        lastUser = message
        items.append(.user(id: message.id, text: text))
        remember(message)
        start(messages: Array(recent.suffix(8)), props: [:])
    }

    /// The answer of a card goes as the next run's `resume` (legacy mode: `forwardedProps.command.resume`).
    public func answer(_ card: ChatCard, with resume: JSONValue) {
        guard !running, let i = cardIndex(card.id) else { return }
        if case .card(var c) = items[i] { c.status = .sending; items[i] = .card(c) }
        start(messages: [], props: ["command": ["resume": resume]], answering: card.id)
    }

    public func choose(_ card: ChatCard, option id: String) {
        answer(card, with: ["answer": ["ids": [.string(id)]]])
    }

    public func confirm(_ card: ChatCard, _ accepted: Bool) {
        answer(card, with: ["accepted": .bool(accepted)])
    }

    /// `set_fields`: apply the ticked rows through the host's form, then answer with the names and the new config.
    /// A refusal of the form (a bad value) keeps the card open with the reason.
    public func acceptFields(_ card: ChatCard, names: [String]) {
        guard !running, let applyFields, let i = cardIndex(card.id) else { return }
        var changes: [String: JSONValue] = [:]
        for row in card.body["changes"]?.array ?? [] {
            if let name = row["name"]?.string, names.contains(name) { changes[name] = row["value"] ?? .null }
        }
        if case .card(var c) = items[i] { c.status = .sending; items[i] = .card(c) }
        Task {
            do {
                let config = try await applyFields(changes)
                if let j = cardIndex(card.id), case .card(var c) = items[j] { c.status = .open; items[j] = .card(c) }
                answer(card, with: ["accepted": true, "names": .array(names.map { .string($0) }), "config": config])
            } catch {
                if let j = cardIndex(card.id), case .card(var c) = items[j] {
                    c.status = .refused(String(localized: "This value did not fit. Try another one.", bundle: .module))
                    items[j] = .card(c)
                }
            }
        }
    }

    public func tapSuggestion(_ text: String) { send(text) }

    /// «Try again». The turn may have reached the server before the connection dropped (it runs on there): read the
    /// thread first and send the message again only when the server does not have it (review, 3).
    public func retry() {
        guard !running, let lastUser else { return }
        error = nil
        running = true
        Task {
            let thread = try? await transport.restore(threadId: threadId)
            running = false
            if let thread, thread.messages.last(where: { $0.role == "user" })?.content == lastUser.content {
                await restore(thread)
                if thread.running == true { followLater() }
            } else {
                start(messages: Array(recent.suffix(8)), props: [:])
            }
        }
    }

    /// The hand-off run after a `site_directive` with `form_id` and without `handoff: "done"`: no new message, the
    /// form's agent takes over in the same chat.
    public func handoff() {
        guard !running else { return }
        start(messages: [], props: ["handoff": true])
    }

    /// Stops showing the answer and ends the turn on the server too.
    public func stop() {
        task?.cancel()
        task = nil
        running = false
        finishSteps()
        let transport = transport, thread = threadId
        Task { await transport.stop(threadId: thread) }
    }

    /// The conversation as the person saw it, from the server (on launch). A turn still running there is not
    /// followed yet: the log shows what is done, and a new message starts the next turn.
    public func restore() async {
        guard let thread = try? await transport.restore(threadId: threadId) else { return }
        await restore(thread)
    }

    private func restore(_ thread: RestoredThread) async {
        if let id = thread.thread_id, !id.isEmpty { threadId = id }
        recent = thread.messages.suffix(8).compactMap { m in
            guard let text = m.content, m.role == "user" || m.role == "assistant" else { return nil }
            return .init(id: m.id ?? UUID().uuidString, role: m.role, content: text)
        }
        items = thread.messages.compactMap { m in
            guard let text = m.content, !text.isEmpty else { return nil }
            let id = m.id ?? UUID().uuidString
            switch m.role {
            case "user": return .user(id: id, text: text)
            case "assistant": return .assistant(id: id, text: text, done: true)
            default: return nil
            }
        }
        if let card = thread.pending_card, case .object = card { addCard(card) }
    }

    // MARK: The run

    private func start(messages: [RunAgentInput.Message], props: [String: JSONValue], answering cardId: String? = nil) {
        error = nil
        suggestions = []
        running = true
        finished = false
        busy = false
        var forwarded = extraProps()
        forwarded["capabilities"] = .array(Self.capabilities)
        for (k, v) in props { forwarded[k] = v }
        let input = RunAgentInput(threadId: threadId, messages: messages, state: state(),
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
                guard let self else { return }
                self.running = false
                if let cardId, let i = self.cardIndex(cardId), case .card(var c) = self.items[i], c.status == .sending {
                    c.status = .open
                    self.items[i] = .card(c)
                }
                return
            } catch {
                self?.fail(Self.human(error))
            }
            guard let self else { return }
            self.running = false
            // a card is answered only by a run that reached RUN_FINISHED and did not refuse it; after an error, a cut-off
            // stream or a stop it is open again (review, 2)
            if let cardId, let i = self.cardIndex(cardId), case .card(var c) = self.items[i], c.status == .sending {
                c.status = self.finished ? .answered : .open
                self.items[i] = .card(c)
            }
            self.finishSteps()
            if self.handoffAfterRun, self.error == nil {
                self.handoffAfterRun = false
                self.handoff()
                return
            }
            self.handoffAfterRun = false
            if self.busy { self.followLater() }
            if let next = self.queued, !self.busy {
                self.queued = nil
                self.send(next)
            }
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
                remember(.init(id: id, role: "assistant", content: text))
            }
        case .toolStart(let id, let name, _):
            tools[id] = items.count
            items.append(.step(id: "tool-" + id, name: name, state: .running))
        case .toolResult(let id, let content, let flagged):
            if let i = tools[id], i < items.count, case .step(let sid, let name, _) = items[i] {
                // `error: true` when the server sends it; until then a guess, so the step state is decoration (review, 5)
                let failed = flagged || content.lowercased().contains(" failed")
                items[i] = .step(id: sid, name: name, state: failed ? .failed : .done)
            }
        case .toolArgs, .toolEnd, .other:
            break
        case .custom(let name, let value):
            custom(name, value)
        case .runFinished(let outcome):
            finished = true
            for interrupt in outcome?["interrupts"]?.array ?? [] {
                if let body = interrupt["value"] ?? interrupt["payload"] { addCard(body) }
            }
        case .runError(let message, let code):
            // "busy": the thread's previous turn still runs — not a failure: wait and read the thread (review, 3)
            if code == "busy" { busy = true; return }
            fail(message.isEmpty ? String(localized: "Something went wrong.", bundle: .module) : message)
        }
    }

    private func custom(_ name: String, _ value: JSONValue) {
        switch name {
        case "text_retract":
            if let id = value["messageId"]?.string, let i = itemIndex(id) {
                items.remove(at: i)
                recent.removeAll { $0.id == id }
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
            // with form_id and without handoff "done" the host starts the hand-off run when this run ends
            if value["form_id"]?.string?.isEmpty == false, value["handoff"]?.string != "done" { handoffAfterRun = true }
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

    private func remember(_ m: RunAgentInput.Message) {
        recent.append(m)
        if recent.count > 8 { recent.removeFirst(recent.count - 8) }
    }

    /// The server is still on the previous turn: read the thread again in a moment.
    private func followLater() {
        running = true
        Task {
            try? await Task.sleep(for: .seconds(2))
            running = false
            await restore()
            if let next = queued { queued = nil; send(next) }
        }
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
