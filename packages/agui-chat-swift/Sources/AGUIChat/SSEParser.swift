import Foundation

/// Server-sent events, line by line: `data:` lines are joined until an empty line ends the event; comments (`:`) and
/// other fields are skipped. Feed it the lines of the response body in order.
public struct SSEParser: Sendable {
    private var data: [String] = []

    public init() {}

    /// Returns the event's data when this line ends one.
    public mutating func feed(line raw: String) -> String? {
        let line = raw.hasSuffix("\r") ? String(raw.dropLast()) : raw
        if line.isEmpty {
            defer { data.removeAll() }
            return data.isEmpty ? nil : data.joined(separator: "\n")
        }
        if line.hasPrefix(":") { return nil }
        if line.hasPrefix("data:") {
            var value = line.dropFirst(5)
            if value.first == " " { value = value.dropFirst() }
            data.append(String(value))
        }
        return nil
    }

    /// The last event when the stream ends without a final empty line.
    public mutating func finish() -> String? {
        defer { data.removeAll() }
        return data.isEmpty ? nil : data.joined(separator: "\n")
    }
}
