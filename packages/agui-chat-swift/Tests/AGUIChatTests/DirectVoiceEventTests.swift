import XCTest
@testable import AGUIChat
import AGUIVoiceWebRTC

/// The server's SSE events of the direct voice (D-26) read as the relay's frames.
final class DirectVoiceEventTests: XCTestCase {
    func testTheRelaysEventsMapTheSame() {
        XCTAssertEqual(directVoiceEvent(["type": "hearing", "delta": "Ciao"]), .hearing("Ciao"))
        XCTAssertEqual(directVoiceEvent(["type": "heard", "text": "Ciao a tutti"]), .heard("Ciao a tutti"))
        XCTAssertEqual(directVoiceEvent(["type": "spoken", "delta": "Ok"]), .spoken("Ok"))
        XCTAssertEqual(directVoiceEvent(["type": "interrupted"]), .interrupted)
        XCTAssertEqual(directVoiceEvent(["type": "echo"]), .echo)
        XCTAssertEqual(directVoiceEvent(["type": "error", "code": "busy"]), .error("busy"))
        XCTAssertEqual(directVoiceEvent(["type": "ended", "reason": "silence"]), .ended(reason: "silence"))
        XCTAssertEqual(directVoiceEvent(["type": "ended"]), .ended(reason: "closed"))
    }

    func testAYesToACardIsAnAnswer() {
        let e = directVoiceEvent(["type": "heard", "text": "sì",
                                  "answers": [["card_id": "c1", "type": "confirm", "accepted": true]]])
        XCTAssertEqual(e, .answer(cardId: "c1", type: "confirm", accepted: true, text: "sì"))
    }

    func testWhatTheHostDoesNotNeedIsSkipped() {
        XCTAssertNil(directVoiceEvent(["type": "result", "text": "x"]))
        XCTAssertNil(directVoiceEvent(["type": "quiet"]))
    }
}
