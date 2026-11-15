import Foundation

/// The voice mode's wire to the host's relay (CONTRACT.md «Voice mode (experimental)», a native client): one
/// WebSocket `GET <stream>?thread_id=<the chat's threadId>`. The person is named by the host — its own session
/// (a cookie in `headers`) or a pass from `POST /voice/unlock` in `X-Voice-Pass`; never in the address.
/// Up: binary frames of PCM16 LE mono at 24 kHz in ~100 ms pieces; `{"type": "end"}` ends the talk.
/// Down: binary frames of the voice's audio, text frames of JSON events.
public final class WebSocketVoiceTransport: NSObject, VoiceTransport, @unchecked Sendable {
    public let incoming: AsyncStream<VoiceTransportEvent>
    public let sampleRate: Double = 24_000
    /// What the relay said in `started`: the talk's limits (seconds, silence_seconds).
    public private(set) var limits: [String: Int] = [:]

    private let continuation: AsyncStream<VoiceTransportEvent>.Continuation
    private let stream: URL
    private let headers: [String: String]
    private let lock = NSLock()
    private var task: URLSessionWebSocketTask?
    private var pending = Data()
    private var connected = false
    private var finished = false

    /// `stream`: the relay's address, e.g. `https://<host>/app/api/voice/stream` (http(s) becomes ws(s)).
    public init(stream: URL, headers: [String: String] = [:]) {
        (incoming, continuation) = AsyncStream.makeStream(of: VoiceTransportEvent.self)
        self.stream = stream
        self.headers = headers
    }

    /// Opens the socket and waits for `started`. Throws `.refused(reason)` (pass, busy, day, person_day,
    /// unavailable) or `.unavailable` when the host has no voice (404) or cannot be reached. Called twice, it
    /// connects once: the app may connect first to choose the mode, then hand the transport to the engine.
    public func connect(threadId: String) async throws {
        if lock.withLock({ connected }) { return }
        var parts = URLComponents(url: stream, resolvingAgainstBaseURL: false)
        parts?.scheme = stream.scheme == "http" ? "ws" : (stream.scheme == "https" ? "wss" : stream.scheme)
        parts?.queryItems = [URLQueryItem(name: "thread_id", value: threadId)]
        guard let url = parts?.url else { throw VoiceTransportError.unavailable }
        var request = URLRequest(url: url)
        for (k, v) in headers { request.setValue(v, forHTTPHeaderField: k) }
        let task = URLSession.shared.webSocketTask(with: request)
        task.maximumMessageSize = 4 << 20
        lock.withLock { self.task = task }
        task.resume()
        let first: URLSessionWebSocketTask.Message
        let patience = Task {          // a host that accepts the socket and never answers
            try await Task.sleep(for: .seconds(10))
            task.cancel(with: .goingAway, reason: nil)
        }
        defer { patience.cancel() }
        do {
            first = try await task.receive()
        } catch {
            // the host's own frame closes before `started`: 4401 — the token is not accepted
            let unauthorized = task.closeCode.rawValue == 4401
            task.cancel(with: .goingAway, reason: nil)
            throw unauthorized ? VoiceTransportError.refused("pass") : VoiceTransportError.unavailable
        }
        guard case .string(let text) = first, let event = Self.json(text) else {
            task.cancel(with: .goingAway, reason: nil)
            throw VoiceTransportError.unavailable
        }
        switch event["type"] as? String {
        case "started":
            limits = (event["limits"] as? [String: Any])?.compactMapValues { $0 as? Int } ?? [:]
            lock.withLock { connected = true }
            Task { await self.read(task) }
        case "refused":
            task.cancel(with: .normalClosure, reason: nil)
            throw VoiceTransportError.refused(event["reason"] as? String ?? "unavailable")
        default:
            task.cancel(with: .goingAway, reason: nil)
            throw VoiceTransportError.unavailable
        }
    }

    /// Microphone audio, gathered into ~100 ms pieces (4 800 bytes at 24 kHz).
    public func send(audio: Data) {
        let piece: Data? = lock.withLock {
            guard connected, !finished else { return nil }
            pending.append(audio)
            guard pending.count >= Int(sampleRate / 10) * 2 else { return nil }
            defer { pending.removeAll(keepingCapacity: true) }
            return pending
        }
        guard let piece, let task = lock.withLock({ task }) else { return }
        task.send(.data(piece)) { _ in }
    }

    /// Ends the talk at once (it is billed by the second, silence too).
    public func close() async {
        guard let task = lock.withLock({ () -> URLSessionWebSocketTask? in
            guard !finished else { return nil }
            return task
        }) else { return }
        try? await task.send(.string(#"{"type":"end"}"#))
        for _ in 0..<15 where !lock.withLock({ finished }) {     // the server's own `ended` (its cost) comes first
            try? await Task.sleep(for: .milliseconds(100))
        }
        task.cancel(with: .normalClosure, reason: nil)
        finish(.ended(reason: "closed"))
    }

    private func read(_ task: URLSessionWebSocketTask) async {
        while true {
            let message: URLSessionWebSocketTask.Message
            do { message = try await task.receive() } catch {
                finish(.ended(reason: "lost"))
                return
            }
            switch message {
            case .data(let pcm):
                continuation.yield(.audio(pcm))
            case .string(let text):
                guard let ev = Self.json(text) else { continue }
                let s = { (key: String) in ev[key] as? String ?? "" }
                switch ev["type"] as? String {
                case "hearing": continuation.yield(.hearing(s("delta")))
                case "heard": continuation.yield(Self.heard(ev))
                case "interrupted": continuation.yield(.interrupted)
                case "spoken": continuation.yield(.spoken(s("delta")))
                case "echo": continuation.yield(.echo)
                case "error": continuation.yield(.error(s("code")))
                case "ended":
                    task.cancel(with: .normalClosure, reason: nil)
                    finish(.ended(reason: s("reason").isEmpty ? "closed" : s("reason")))
                    return
                default: break       // result, quiet: the chat's own run shows them
                }
            @unknown default:
                break
            }
        }
    }

    private func finish(_ last: VoiceTransportEvent) {
        let first = lock.withLock { () -> Bool in
            defer { finished = true }
            return !finished
        }
        guard first else { return }
        continuation.yield(last)
        continuation.finish()
    }

    /// `heard` → the words, or the answer to a waiting card when it carries `answers: {card_id, type, accepted}`.
    static func heard(_ ev: [String: Any]) -> VoiceTransportEvent {
        let text = ev["text"] as? String ?? ""
        if let a = ev["answers"] as? [String: Any], let id = a["card_id"] as? String, let accepted = a["accepted"] as? Bool {
            return .answer(cardId: id, type: a["type"] as? String ?? "", accepted: accepted, text: text)
        }
        return .heard(text)
    }

    private static func json(_ text: String) -> [String: Any]? {
        (try? JSONSerialization.jsonObject(with: Data(text.utf8))) as? [String: Any]
    }
}

public enum VoiceTransportError: Error, Equatable {
    case refused(String)       // pass, busy, day, person_day, unavailable
    case unavailable           // no voice on this host (404), or it cannot be reached
}
