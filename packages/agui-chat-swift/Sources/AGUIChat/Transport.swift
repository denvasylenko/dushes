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

/// Where runs go. The host gives the URL and its own headers (the app's token): the package keeps no secrets.
public protocol AGUITransport: Sendable {
    func run(_ input: RunAgentInput) -> AsyncThrowingStream<AGUIEvent, Error>
}

/// POST `<agent>/run`, answered as SSE.
public struct HTTPTransport: AGUITransport {
    public var url: URL
    public var headers: @Sendable () async -> [String: String]
    public var session: URLSession

    public init(url: URL, session: URLSession = .shared,
                headers: @escaping @Sendable () async -> [String: String] = { [:] }) {
        self.url = url
        self.session = session
        self.headers = headers
    }

    public func run(_ input: RunAgentInput) -> AsyncThrowingStream<AGUIEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    var request = URLRequest(url: url)
                    request.httpMethod = "POST"
                    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                    request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                    for (k, v) in await headers() { request.setValue(v, forHTTPHeaderField: k) }
                    request.httpBody = try JSONEncoder().encode(input)
                    let (bytes, response) = try await session.bytes(for: request)
                    if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                        throw AGUIError.http(status: http.statusCode)
                    }
                    var parser = SSEParser()
                    for try await line in bytes.lines {
                        // `lines` drops empty lines, so every data line is treated as a whole event (the servers
                        // send one JSON object per event, on one line)
                        if let payload = parser.feed(line: line) ?? parser.feed(line: "") {
                            continuation.yield(try AGUIEvent.decode(Data(payload.utf8)))
                        }
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

    public init(pause: Duration = .milliseconds(40), script: @escaping @Sendable (RunAgentInput) -> [AGUIEvent]) {
        self.pause = pause
        self.script = script
    }

    /// Events from a recording: JSON lines or SSE `data:` lines.
    public static func events(fromRecording text: String) -> [AGUIEvent] {
        var parser = SSEParser()
        var out: [AGUIEvent] = []
        for line in text.split(separator: "\n", omittingEmptySubsequences: false) {
            let l = String(line)
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
