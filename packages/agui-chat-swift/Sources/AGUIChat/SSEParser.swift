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

/// Splits a byte stream into lines on `\n` only (a trailing `\r` is dropped). `URLSession.bytes.lines` also splits on
/// U+2028, U+2029 and U+0085, which the server may write raw inside a JSON string: an event would then be cut in the
/// middle of its JSON (review of f3b7f0f, finding 1).
public struct LineSplitter: Sendable {
    private var buffer: [UInt8] = []

    public init() {}

    /// Returns the line this byte ends, if it ends one.
    public mutating func feed(_ byte: UInt8) -> String? {
        guard byte == 0x0A else { buffer.append(byte); return nil }
        defer { buffer.removeAll(keepingCapacity: true) }
        if buffer.last == 0x0D { buffer.removeLast() }
        return String(decoding: buffer, as: UTF8.self)
    }

    /// The last line when the stream ends without `\n`.
    public mutating func finish() -> String? {
        defer { buffer.removeAll() }
        return buffer.isEmpty ? nil : String(decoding: buffer, as: UTF8.self)
    }

    /// All lines of a whole text, split the same way (tests, recordings).
    public static func lines(_ data: Data) -> [String] {
        var s = LineSplitter()
        var out = data.compactMap { s.feed($0) }
        if let last = s.finish() { out.append(last) }
        return out
    }
}
