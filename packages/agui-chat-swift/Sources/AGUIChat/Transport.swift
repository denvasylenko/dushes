import Foundation

/// AG-UI `RunAgentInput`: what one run sends.
public struct RunAgentInput: Encodable, Sendable {
    public struct Message: Encodable, Sendable, Equatable {
        public var id: String
        public var role: String
        public var content: String
        public init(id: String = UUID().uuidString, role: String, content: String) {
            self.id = id; self.role = role; self.content = content
        }
    }

    public var threadId: String
    public var runId: String = UUID().uuidString
    public var messages: [Message]
    public var state: JSONValue = .object([:])
    public var tools: [JSONValue] = []
    public var context: [JSONValue] = []
    public var forwardedProps: JSONValue = .object([:])

    public init(threadId: String, messages: [Message], state: JSONValue = .object([:]),
                forwardedProps: JSONValue = .object([:])) {
        self.threadId = threadId
        self.messages = messages
        self.state = state
        self.forwardedProps = forwardedProps
    }
}

/// A thread as the server restores it (`GET <agent>/threads/{id}?format=agui`).
public struct RestoredThread: Decodable, Sendable {
    public struct Message: Decodable, Sendable {
        public var id: String?
        public var role: String
        public var content: String?
    }
    public var thread_id: String?
    public var messages: [Message]
    public var pending_card: JSONValue?
    public var running: Bool?
}

/// Where runs go. The host gives the URL and its own headers (the app's token): the package keeps no secrets.
public protocol AGUITransport: Sendable {
    func run(_ input: RunAgentInput) -> AsyncThrowingStream<AGUIEvent, Error>
    /// The thread after a relaunch; nil when there is none. The client restores from it, not from its own cache.
    func restore(threadId: String) async throws -> RestoredThread?
    /// Ends the thread's running turn on the server: a turn outlives its connection.
    func stop(threadId: String) async
}

extension AGUITransport {
    public func restore(threadId: String) async throws -> RestoredThread? { nil }
    public func stop(threadId: String) async {}
}

/// `<agent>/run` (SSE), `<agent>/threads/{id}?format=agui`, `<agent>/stop`.
public struct HTTPTransport: AGUITransport {
    public var agent: URL
    public var headers: @Sendable () async -> [String: String]
    public var session: URLSession

    /// `agent` is the base, e.g. `https://host/app/api/v1/sites/12/assistant`.
    public init(agent: URL, session: URLSession = .shared,
                headers: @escaping @Sendable () async -> [String: String] = { [:] }) {
        self.agent = agent
        self.session = session
        self.headers = headers
    }

    private func request(_ path: String, method: String, body: Data? = nil) async -> URLRequest {
        var r = URLRequest(url: agent.appending(path: path))
        r.httpMethod = method
        if let body {
            r.httpBody = body
            r.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        for (k, v) in await headers() { r.setValue(v, forHTTPHeaderField: k) }
        return r
    }

    public func restore(threadId: String) async throws -> RestoredThread? {
        var r = await request("threads/\(threadId)", method: "GET")
        r.url = r.url.flatMap { URL(string: $0.absoluteString + "?format=agui") }
        let (data, response) = try await session.data(for: r)
        if let http = response as? HTTPURLResponse {
            if http.statusCode == 404 { return nil }
            if !(200..<300).contains(http.statusCode) { throw AGUIError.http(status: http.statusCode) }
        }
        return try JSONDecoder().decode(RestoredThread.self, from: data)
    }

    public func stop(threadId: String) async {
        let body = try? JSONEncoder().encode(["thread_id": threadId])
        _ = try? await session.data(for: await request("stop", method: "POST", body: body))
    }

    public func run(_ input: RunAgentInput) -> AsyncThrowingStream<AGUIEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    var request = await request("run", method: "POST", body: try JSONEncoder().encode(input))
                    request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                    let (bytes, response) = try await session.bytes(for: request)
                    if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                        throw AGUIError.http(status: http.statusCode)
                    }
                    var parser = SSEParser()
                    var splitter = LineSplitter()
                    for try await byte in bytes {
                        guard let line = splitter.feed(byte) else { continue }
                        if let payload = parser.feed(line: line) {
                            continuation.yield(try AGUIEvent.decode(Data(payload.utf8)))
                        }
                    }
                    if let line = splitter.finish(), let payload = parser.feed(line: line) {
                        continuation.yield(try AGUIEvent.decode(Data(payload.utf8)))
                    }
                    if let payload = parser.finish() { continuation.yield(try AGUIEvent.decode(Data(payload.utf8))) }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}

/// Plays a recorded stream (one JSON event per line, or SSE text) with a pause between events: previews, tests,
/// the stand-in mode of a host until its server is up.
public struct ReplayTransport: AGUITransport {
    public var script: @Sendable (RunAgentInput) -> [AGUIEvent]
    public var pause: Duration
    public var thread: RestoredThread?

    public init(pause: Duration = .milliseconds(40), thread: RestoredThread? = nil,
                script: @escaping @Sendable (RunAgentInput) -> [AGUIEvent]) {
        self.pause = pause
        self.thread = thread
        self.script = script
    }

    public func restore(threadId: String) async throws -> RestoredThread? { thread }

    /// Events from a recording: JSON lines or SSE `data:` lines.
    public static func events(fromRecording text: String) -> [AGUIEvent] {
        var parser = SSEParser()
        var out: [AGUIEvent] = []
        for l in LineSplitter.lines(Data(text.utf8)) {
            if l.hasPrefix("data:") {
                if let payload = parser.feed(line: l) ?? parser.feed(line: ""),
                   let e = try? AGUIEvent.decode(Data(payload.utf8)) { out.append(e) }
            } else if l.hasPrefix("{"), let e = try? AGUIEvent.decode(Data(l.utf8)) {
                out.append(e)
            }
        }
        return out
    }

    public func run(_ input: RunAgentInput) -> AsyncThrowingStream<AGUIEvent, Error> {
        let events = script(input)
        let pause = pause
        return AsyncThrowingStream { continuation in
            let task = Task {
                for e in events {
                    try? await Task.sleep(for: pause)
                    if Task.isCancelled { break }
                    continuation.yield(e)
                }
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}
