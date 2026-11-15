import Foundation
import Observation

/// What a voice engine reports (the server's GET /voice/events, see the voice contract): what the person said, what
/// the voice says, the sound level, the end.
public enum VoiceEngineEvent: Equatable, Sendable {
    case hearing(String)          // a piece of the person's words as they speak
    case echo                     // drop what `hearing` showed: it was the voice's own words
    case heard(String)            // the person's words: sent as an ordinary user message in the same thread
    case spoken(String)           // a piece of what the voice says (its transcript)
    case level(Double)            // 0…1, the person's sound level (the session sends audio all the time, silence too)
    case error(String)
    case ended(reason: String)    // closed, time, money, silence, day, lost
}

/// The audio side of the voice mode. The real one (WebRTC to OpenAI through our server's /voice/session) lives in its
/// own product so this package stays without dependencies; `ScriptedVoiceEngine` plays a talk for previews and tests.
@MainActor
public protocol VoiceEngine: AnyObject {
    var events: AsyncStream<VoiceEngineEvent> { get }
    func start(threadId: String) async throws
    func setMuted(_ muted: Bool)
    /// Ends the talk at once (an open session is billed by the second, silence too).
    func end() async
}

/// The voice mode of a chat: listening → (the person's words go to the agent) thinking → speaking → listening.
/// The agent's turn is the store's ordinary run, so steps, text and cards show as in the chat.
@MainActor
@Observable
public final class VoiceController {
    public enum State: Equatable, Sendable { case off, connecting, listening, thinking, speaking, muted }

    public private(set) var state: State = .off
    public private(set) var level: Double = 0
    public private(set) var problem: String?
    /// The person's words so far, as they speak (cleared when the phrase is handed over).
    public private(set) var hearing = ""

    private let store: ChatStore
    private let makeEngine: @MainActor () -> VoiceEngine
    private var engine: VoiceEngine?
    private var listen: Task<Void, Never>?
    private var watch: Task<Void, Never>?
    private var speakingUntil = Date.distantPast
    private var muted = false

    public init(store: ChatStore, engine: @escaping @MainActor () -> VoiceEngine) {
        self.store = store
        self.makeEngine = engine
    }

    public var active: Bool { state != .off }

    public func start() {
        guard state == .off else { return }
        problem = nil
        state = .connecting
        let e = makeEngine()
        engine = e
        listen = Task { [weak self] in
            for await event in e.events { self?.handle(event) }
            self?.finish()
        }
        Task { [weak self] in
            guard let self else { return }
            do {
                try await e.start(threadId: store.threadId)
                if state == .connecting { state = muted ? .muted : .listening }
            } catch {
                problem = String(localized: "The voice could not start. Try again.", bundle: .module)
                await stop()
            }
        }
        // the agent's run decides «thinking»; the voice's words decide «speaking»
        watch = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(120))
                self?.tick()
            }
        }
    }

    /// Muted or not (typing in the field: it stops listening; the talk stays open).
    public func setMuted(_ on: Bool) {
        guard on != muted else { return }
        toggleMute()
    }

    public func toggleMute() {
        muted.toggle()
        engine?.setMuted(muted)
        if state == .listening || state == .muted { state = muted ? .muted : .listening }
    }

    public func stop() async {
        watch?.cancel()
        listen?.cancel()
        await engine?.end()
        engine = nil
        state = .off
        level = 0
    }

    private func handle(_ event: VoiceEngineEvent) {
        switch event {
        case .hearing(let delta):
            hearing += delta
        case .echo:
            hearing = ""
        case .heard(let text):
            hearing = ""
            let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !t.isEmpty else { return }
            store.send(t)
            state = .thinking
        case .spoken:
            speakingUntil = Date().addingTimeInterval(1.2)
            if state != .thinking || !store.running { state = .speaking }
        case .level(let l):
            level = max(0, min(1, l))
        case .error(let code):
            problem = code
        case .ended(let reason):
            if reason != "closed" {
                problem = reason == "silence"
                    ? String(localized: "The talk ended after a silence.", bundle: .module)
                    : String(localized: "The talk ended.", bundle: .module)
            }
            finish()
        }
    }

    private func tick() {
        guard state != .off, state != .connecting else { return }
        if store.running { state = .thinking; return }
        if Date() < speakingUntil { state = .speaking; return }
        state = muted ? .muted : .listening
    }

    private func finish() {
        watch?.cancel()
        engine = nil
        state = .off
        level = 0
    }
}

/// A talk played from a script: no sound, no server, no cost (previews, tests, the app's example). Each phrase is
/// «heard» after a moment of rising level; after the agent's turn the voice «speaks» a short paraphrase.
@MainActor
public final class ScriptedVoiceEngine: VoiceEngine {
    public let events: AsyncStream<VoiceEngineEvent>
    private let continuation: AsyncStream<VoiceEngineEvent>.Continuation
    private let phrases: [String]
    private let spoken: [String]
    private var task: Task<Void, Never>?
    private var muted = false

    public init(phrases: [String], spoken: [String] = []) {
        (events, continuation) = AsyncStream.makeStream(of: VoiceEngineEvent.self)
        self.phrases = phrases
        self.spoken = spoken
    }

    public func start(threadId: String) async throws {
        try await Task.sleep(for: .milliseconds(500))
        task = Task { [weak self] in
            guard let self else { return }
            for (i, phrase) in phrases.enumerated() {
                // the person speaks: the level rises and falls for about two seconds
                for step in 0..<20 {
                    if Task.isCancelled { return }
                    let l = muted ? 0 : 0.25 + 0.6 * abs(sin(Double(step) * 0.7))
                    continuation.yield(.level(l))
                    try? await Task.sleep(for: .milliseconds(100))
                }
                continuation.yield(.level(0))
                if muted { continue }
                continuation.yield(.heard(phrase))
                try? await Task.sleep(for: .seconds(4))       // the agent's turn
                if i < spoken.count {
                    for word in spoken[i].split(separator: " ") {
                        continuation.yield(.spoken(String(word) + " "))
                        try? await Task.sleep(for: .milliseconds(160))
                    }
                }
                try? await Task.sleep(for: .seconds(2))
            }
            continuation.yield(.ended(reason: "silence"))
            continuation.finish()
        }
    }

    public func setMuted(_ muted: Bool) { self.muted = muted }

    public func end() async {
        task?.cancel()
        continuation.yield(.ended(reason: "closed"))
        continuation.finish()
    }
}
