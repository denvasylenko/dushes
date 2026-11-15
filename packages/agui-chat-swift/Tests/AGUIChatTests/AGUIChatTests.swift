import XCTest
@testable import AGUIChat

final class AGUIChatTests: XCTestCase {
    private func recording(_ name: String) throws -> String {
        let url = try XCTUnwrap(Bundle.module.url(forResource: name, withExtension: "sse", subdirectory: "Fixtures"))
        return try String(contentsOf: url, encoding: .utf8)
    }

    func testSSEJoinsDataLinesAndSkipsComments() {
        var p = SSEParser()
        XCTAssertNil(p.feed(line: ": comment"))
        XCTAssertNil(p.feed(line: "data: {\"a\":"))
        XCTAssertNil(p.feed(line: "data: 1}"))
        XCTAssertEqual(p.feed(line: ""), "{\"a\":\n1}")
        XCTAssertNil(p.feed(line: ""))
    }

    func testDecodesEveryKindAndKeepsUnknownOnes() throws {
        let e = try AGUIEvent.decode(Data(#"{"type":"STATE_DELTA","delta":[]}"#.utf8))
        XCTAssertEqual(e, .other(type: "STATE_DELTA"))
        let c = try AGUIEvent.decode(Data(#"{"type":"CUSTOM","name":"language","value":{"lang":"it"}}"#.utf8))
        XCTAssertEqual(c, .custom(name: "language", value: ["lang": "it"]))
    }

    @MainActor
    func testRecordedTurnBuildsTheLog() throws {
        let events = ReplayTransport.events(fromRecording: try recording("hours-turn"))
        XCTAssertEqual(events.count, 20)
        let store = ChatStore(transport: ReplayTransport { _ in [] })
        store.hostEvents = ["hf_card"]
        events.forEach(store.apply)

        // the lead before the tool was taken back; the answer, the step, the card and the host card stay
        XCTAssertFalse(store.items.contains { $0.id == "m-lead" })
        guard case .assistant(_, let text, true) = store.items.first(where: { $0.id == "m-2" }) else {
            return XCTFail("no finished answer")
        }
        XCTAssertEqual(text, "Sunday until 23:00?")
        XCTAssertTrue(store.items.contains { if case .step(_, "view_site", .done) = $0 { true } else { false } })
        guard case .card(let card) = store.items.first(where: { $0.id == "card-k-1" }) else { return XCTFail("no card") }
        XCTAssertEqual(card.type, "ask")
        XCTAssertEqual(card.options.map(\.id), ["23", "22"])
        XCTAssertTrue(store.items.contains { if case .host(_, "hf_card", _) = $0 { true } else { false } })
        XCTAssertEqual(store.suggestions, ["Menu and prices", "Open the site"])
        XCTAssertNil(store.error)
    }

    @MainActor
    func testRefusedAnswerReopensTheCard() {
        let store = ChatStore(transport: ReplayTransport { _ in [] })
        store.apply(.custom(name: "on_interrupt", value: .string(#"{"type":"confirm","card_id":"k-9","title":"Publish?"}"#)))
        store.apply(.custom(name: "card_result", value: ["card_id": "k-9", "status": "not_accepted", "reason": "Too late"]))
        guard case .card(let c) = store.items.last else { return XCTFail("no card") }
        XCTAssertEqual(c.status, .refused("Too late"))
    }

    @MainActor
    func testSendRunsAndSendsCapabilities() async throws {
        let seen = Captured()
        let transport = ReplayTransport(pause: .zero) { input in
            seen.set(input)
            return [.runStarted(threadId: "t-7", runId: nil),
                    .textStart(messageId: "a", role: "assistant"), .textContent(messageId: "a", delta: "Hi"),
                    .textEnd(messageId: "a"), .runFinished(outcome: nil)]
        }
        let store = ChatStore(transport: transport, threadId: "t-0")
        store.send("Hello")
        for _ in 0..<50 where store.running { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertFalse(store.running)
        XCTAssertEqual(store.threadId, "t-7")
        let input = try XCTUnwrap(seen.value)
        XCTAssertEqual(input.messages.last?.content, "Hello")
        XCTAssertEqual(input.forwardedProps["capabilities"], .array(ChatStore.capabilities))
        XCTAssertEqual(store.items.count, 2)
    }

    @MainActor
    func testAStreamWithoutTheEndIsAnError() async throws {
        let store = ChatStore(transport: ReplayTransport(pause: .zero) { _ in [.runStarted(threadId: nil, runId: nil)] })
        store.send("Hello")
        for _ in 0..<50 where store.running { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertNotNil(store.error)
    }
}

final class Captured: @unchecked Sendable {
    private let lock = NSLock()
    private var input: RunAgentInput?
    func set(_ i: RunAgentInput) { lock.lock(); input = i; lock.unlock() }
    var value: RunAgentInput? { lock.lock(); defer { lock.unlock() }; return input }
}
