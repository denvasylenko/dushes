import Foundation

/// One AG-UI event as the Dushes servers send it (site/src/content/docs/reference/agui-events.md).
/// Unknown `type`s and unknown `CUSTOM` names decode too and are ignored by the store: a client must never fail on one.
public enum AGUIEvent: Equatable, Sendable {
    case runStarted(threadId: String?, runId: String?)
    case runFinished(outcome: JSONValue?)
    case runError(message: String, code: String?)
    case textStart(messageId: String, role: String?)
    case textContent(messageId: String, delta: String)
    case textEnd(messageId: String)
    case toolStart(toolCallId: String, name: String, parentId: String?)
    case toolArgs(toolCallId: String, delta: String)
    case toolEnd(toolCallId: String)
    case toolResult(toolCallId: String, content: String)
    case custom(name: String, value: JSONValue)
    case other(type: String)

    /// Decodes one event from its JSON object (one SSE `data:` payload).
    public static func decode(_ data: Data) throws -> AGUIEvent {
        let v = try JSONDecoder().decode(JSONValue.self, from: data)
        guard let type = v["type"]?.string else { throw AGUIError.malformed("an event without a type") }
        func s(_ k: String) -> String? { v[k]?.string }
        switch type {
        case "RUN_STARTED": return .runStarted(threadId: s("threadId"), runId: s("runId"))
        case "RUN_FINISHED": return .runFinished(outcome: v["outcome"])
        case "RUN_ERROR": return .runError(message: s("message") ?? "", code: s("code"))
        case "TEXT_MESSAGE_START": return .textStart(messageId: s("messageId") ?? "", role: s("role"))
        case "TEXT_MESSAGE_CONTENT": return .textContent(messageId: s("messageId") ?? "", delta: s("delta") ?? "")
        case "TEXT_MESSAGE_END": return .textEnd(messageId: s("messageId") ?? "")
        case "TOOL_CALL_START":
            return .toolStart(toolCallId: s("toolCallId") ?? "", name: s("toolCallName") ?? "",
                              parentId: s("parentMessageId") ?? s("parent_id"))
        case "TOOL_CALL_ARGS": return .toolArgs(toolCallId: s("toolCallId") ?? "", delta: s("delta") ?? "")
        case "TOOL_CALL_END": return .toolEnd(toolCallId: s("toolCallId") ?? "")
        case "TOOL_CALL_RESULT": return .toolResult(toolCallId: s("toolCallId") ?? "", content: s("content") ?? "")
        case "CUSTOM": return .custom(name: s("name") ?? "", value: v["value"] ?? .null)
        default: return .other(type: type)
        }
    }

    public var isTerminal: Bool {
        switch self {
        case .runFinished, .runError: true
        default: false
        }
    }
}

public enum AGUIError: Error, Equatable, Sendable {
    case malformed(String)
    case http(status: Int)
    case transport(String)
}
