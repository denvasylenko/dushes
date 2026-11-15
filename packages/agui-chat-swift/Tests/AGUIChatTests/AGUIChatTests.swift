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
    func testRestoreBuildsTheLogAndThePendingCard() async throws {
        let json = #"{"thread_id":"t-5","running":false,"messages":[{"id":"u1","role":"user","content":"Hours?"},{"id":"a1","role":"assistant","content":"12-22"},{"role":"tool","content":"x"}],"pending_card":{"type":"confirm","card_id":"k-2","title":"Publish?"}}"#
        let thread = try JSONDecoder().decode(RestoredThread.self, from: Data(json.utf8))
        let store = ChatStore(transport: ReplayTransport(thread: thread) { _ in [] }, threadId: "t-5")
        await store.restore()
        XCTAssertEqual(store.items.map(\.id), ["u1", "a1", "card-k-2"])
    }

    @MainActor
    func testARunSendsOnlyTheNewMessage() async throws {
        let seen = Captured()
        let store = ChatStore(transport: ReplayTransport(pause: .zero) { input in
            seen.set(input)
            return [.runFinished(outcome: nil)]
        })
        store.send("One")
        for _ in 0..<50 where store.running { try await Task.sleep(for: .milliseconds(10)) }
        store.send("Two")
        for _ in 0..<50 where store.running { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertEqual(seen.value?.messages.last?.content, "Two")
        XCTAssertLessThanOrEqual(seen.value?.messages.count ?? 0, 8)
    }

    func testLineSeparatorsInsideTextDoNotCutTheEvent() throws {
        // U+2028 written raw inside a JSON string (review, finding 1)
        let raw = "data: {\"type\":\"TEXT_MESSAGE_CONTENT\",\"messageId\":\"m\",\"delta\":\"a\u{2028}b\u{85}c\"}\r\n\r\n"
        let lines = LineSplitter.lines(Data(raw.utf8))
        XCTAssertEqual(lines.count, 2)
        var p = SSEParser()
        let payload = try XCTUnwrap(lines.compactMap { p.feed(line: $0) }.first)
        XCTAssertEqual(try AGUIEvent.decode(Data(payload.utf8)), .textContent(messageId: "m", delta: "a\u{2028}b\u{85}c"))
    }

    @MainActor
    func testACardIsOpenAgainWhenItsRunFails() async throws {
        let pending = RestoredThread(thread_id: nil, messages: [], pending_card: ["type": "confirm", "card_id": "k-3"], running: false)
        let store = ChatStore(transport: ReplayTransport(pause: .zero, thread: pending) { _ in
            [.runStarted(threadId: nil, runId: nil), .runError(message: "boom", code: nil)]
        })
        store.apply(.custom(name: "on_interrupt", value: .string(#"{"type":"confirm","card_id":"k-3","title":"Publish?"}"#)))
        guard case .card(let card) = store.items.last else { return XCTFail("no card") }
        store.confirm(card, true)
        for _ in 0..<50 where store.running { try await Task.sleep(for: .milliseconds(10)) }
        for _ in 0..<50 { try await Task.sleep(for: .milliseconds(10)) }
        guard case .card(let after) = store.items.first(where: { $0.id == "card-k-3" }) else { return XCTFail("no card") }
        XCTAssertEqual(after.status, .open)
        XCTAssertNotNil(store.error)
    }

    /// Review 2, finding 2: after a failed answer the card does not reopen when the server waits for another card.
    @MainActor
    func testAFailedAnswerDoesNotReopenACardTheServerNoLongerWaitsFor() async throws {
        let other = RestoredThread(thread_id: nil, messages: [], pending_card: ["type": "confirm", "card_id": "k-other"], running: false)
        let store = ChatStore(transport: ReplayTransport(pause: .zero, thread: other) { _ in
            [.runStarted(threadId: nil, runId: nil)]                      // cut off
        })
        store.apply(.custom(name: "on_interrupt", value: .string(#"{"type":"confirm","card_id":"k-4","title":"Publish?"}"#)))
        guard case .card(let card) = store.items.last else { return XCTFail("no card") }
        store.confirm(card, true)
        for _ in 0..<60 { try await Task.sleep(for: .milliseconds(10)) }
        guard case .card(let after) = store.items.first(where: { $0.id == "card-k-4" }) else { return XCTFail("no card") }
        XCTAssertEqual(after.status, .closed)
        XCTAssertFalse(store.isAnswerable(ChatCard(id: "k-old", type: "confirm", body: [:])))
    }

    /// Review 2, finding 1: «busy» means the server did not take the message — it is sent again once the turn ends.
    @MainActor
    func testABusyMessageIsSentAgainAfterTheRunningTurn() async throws {
        let calls = Captured()
        let count = Counter()
        let idle = RestoredThread(thread_id: "t", messages: [], pending_card: nil, running: false)
        let store = ChatStore(transport: ReplayTransport(pause: .zero, thread: idle) { input in
            calls.set(input)
            if count.next() == 1 { return [.runStarted(threadId: nil, runId: nil), .runError(message: "", code: "busy")] }
            return [.runStarted(threadId: nil, runId: nil), .runFinished(outcome: nil)]
        }, threadId: "t")
        store.send("Hello")
        for _ in 0..<400 where count.value < 2 || store.running { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertEqual(count.value, 2)
        XCTAssertEqual(calls.value?.messages.last?.content, "Hello")
        XCTAssertTrue(store.items.contains { if case .user(_, "Hello") = $0 { true } else { false } })
        XCTAssertNil(store.error)
    }

    @MainActor
    func testRetryDoesNotSendWhatTheServerAlreadyHas() async throws {
        let calls = Captured()
        let thread = RestoredThread(thread_id: "t", messages: [.init(id: "u", role: "user", content: "Hello"),
                                                              .init(id: "a", role: "assistant", content: "Hi")],
                                    pending_card: nil, running: false)
        let store = ChatStore(transport: ReplayTransport(pause: .zero, thread: thread) { input in
            calls.set(input)
            return [.runStarted(threadId: nil, runId: nil)]          // cut off: an error, then «Try again»
        }, threadId: "t")
        store.send("Hello")
        for _ in 0..<50 where store.running { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertNotNil(store.error)
        calls.set(RunAgentInput(threadId: "none", messages: []))
        store.retry()
        for _ in 0..<50 where store.running || store.items.count < 2 { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertEqual(calls.value?.threadId, "none")              // no second run
        XCTAssertEqual(store.items.map(\.id), ["u", "a"])
    }

    /// ef30d5d: an answer to a card that is no longer open comes back as card_gone — the card closes, not «refused».
    @MainActor
    func testACardGoneClosesTheCard() {
        let store = ChatStore(transport: ReplayTransport { _ in [] })
        store.apply(.custom(name: "on_interrupt", value: .string(#"{"type":"confirm","card_id":"k-5","title":"Publish?"}"#)))
        store.apply(.custom(name: "card_result", value: ["card_id": "k-5", "status": "not_accepted", "reason": "x", "code": "card_gone"]))
        guard case .card(let c) = store.items.last else { return XCTFail("no card") }
        XCTAssertEqual(c.status, .closed)
    }

    /// The voice mode: what the person said goes to the agent as an ordinary message in the same thread.
    @MainActor
    func testHeardWordsBecomeAMessage() async throws {
        let store = ChatStore(transport: ReplayTransport(pause: .zero) { _ in [.runFinished(outcome: nil)] }, threadId: "t-v")
        let voice = VoiceController(store: store) { ScriptedVoiceEngine(phrases: ["Sunday until eleven"]) }
        voice.start()
        for _ in 0..<80 where !store.items.contains(where: { if case .user(_, "Sunday until eleven") = $0 { true } else { false } }) {
            try await Task.sleep(for: .milliseconds(50))
        }
        XCTAssertTrue(store.items.contains { if case .user(_, "Sunday until eleven") = $0 { true } else { false } })
        XCTAssertTrue(voice.active)
        await voice.stop()
        XCTAssertFalse(voice.active)
    }

    /// The mock wire «hears» a phrase after about two seconds of 16-bit mono audio has gone up.
    func testMockTransportHearsAfterTwoSecondsOfAudio() async throws {
        let t = MockVoiceTransport(phrases: ["Hello"])
        try await t.connect(threadId: "x")
        t.send(audio: Data(count: Int(t.sampleRate) * 2 * 2))
        var it = t.incoming.makeAsyncIterator()
        let first = await it.next()
        XCTAssertEqual(first, .heard("Hello"))
        await t.close()
    }

    @MainActor
    func testAStreamWithoutTheEndIsAnError() async throws {
        let store = ChatStore(transport: ReplayTransport(pause: .zero) { _ in [.runStarted(threadId: nil, runId: nil)] })
        store.send("Hello")
        for _ in 0..<50 where store.running { try await Task.sleep(for: .milliseconds(10)) }
        XCTAssertNotNil(store.error)
    }
}

final class Counter: @unchecked Sendable {
    private let lock = NSLock()
    private var n = 0
    func next() -> Int { lock.lock(); defer { lock.unlock() }; n += 1; return n }
    var value: Int { lock.lock(); defer { lock.unlock() }; return n }
}

final class Captured: @unchecked Sendable {
    private let lock = NSLock()
    private var input: RunAgentInput?
    func set(_ i: RunAgentInput) { lock.lock(); input = i; lock.unlock() }
    var value: RunAgentInput? { lock.lock(); defer { lock.unlock() }; return input }
}
