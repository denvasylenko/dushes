import Foundation

/// The wire of the voice mode (D-20 in the Cheese repo; Dushes TL's yes): one connection to OUR host, which relays to the
/// voice model with its own key — the app never holds a provider key. Microphone audio goes up as 16-bit mono PCM
/// frames; the voice comes down as PCM frames plus the talk's events. The WebSocket implementation follows the relay's
/// contract once it exists (not built against a guess); `MockVoiceTransport` plays a talk for the UI and tests.
public protocol VoiceTransport: AnyObject, Sendable {
    /// The voice's audio and the talk's events, in order.
    var incoming: AsyncStream<VoiceTransportEvent> { get }
    /// The PCM format both ways (the relay decides; 24 kHz is the voice model's default).
    var sampleRate: Double { get }
    func connect(threadId: String) async throws
    /// One frame of the person's audio: 16-bit little-endian mono PCM at `sampleRate`.
    func send(audio: Data)
    /// Ends the talk at once: an open one is billed by the second, silence too.
    func close() async
}

public enum VoiceTransportEvent: Equatable, Sendable {
    case audio(Data)              // the voice speaking: 16-bit mono PCM at the transport's rate
    case hearing(String)          // a piece of the person's words as they speak
    case echo                     // the voice's own words came back through the microphone: drop what `hearing` showed
    case heard(String)            // what the person said: the app sends it to the agent as a message
    case spoken(String)           // a piece of what the voice says (its transcript)
    case error(String)
    case ended(reason: String)    // closed, time, money, silence, day, lost
}

/// A talk without a network (previews, tests, the app's example): it «hears» the scripted phrases one by one after
/// some audio has come up, and «speaks» a short paraphrase back as a quiet tone, so the audio path is exercised too.
public final class MockVoiceTransport: VoiceTransport, @unchecked Sendable {
    public let incoming: AsyncStream<VoiceTransportEvent>
    public let sampleRate: Double = 24_000
    private let continuation: AsyncStream<VoiceTransportEvent>.Continuation
    private let phrases: [String]
    private let spoken: [String]
    private let lock = NSLock()
    private var bytesUp = 0
    private var index = 0
    private var closed = false

    public init(phrases: [String], spoken: [String] = []) {
        (incoming, continuation) = AsyncStream.makeStream(of: VoiceTransportEvent.self)
        self.phrases = phrases
        self.spoken = spoken
    }

    public func connect(threadId: String) async throws {
        try await Task.sleep(for: .milliseconds(300))
    }

    /// About two seconds of audio up = one phrase heard.
    public func send(audio: Data) {
        lock.lock()
        guard !closed else { lock.unlock(); return }
        bytesUp += audio.count
        let due = bytesUp >= Int(sampleRate) * 2 * 2 && index < phrases.count
        let i = index
        if due { bytesUp = 0; index += 1 }
        lock.unlock()
        guard due else { return }
        continuation.yield(.heard(phrases[i]))
        if i < spoken.count {
            let words = spoken[i]
            Task { [weak self] in
                try? await Task.sleep(for: .seconds(4))
                self?.speak(words)
            }
        }
    }

    private func speak(_ text: String) {
        for word in text.split(separator: " ") {
            continuation.yield(.spoken(String(word) + " "))
            continuation.yield(.audio(Self.tone(seconds: 0.16, rate: sampleRate)))
        }
    }

    /// A soft 220 Hz tone as 16-bit PCM: stands in for the voice.
    static func tone(seconds: Double, rate: Double) -> Data {
        let n = Int(seconds * rate)
        var data = Data(count: n * 2)
        data.withUnsafeMutableBytes { raw in
            let p = raw.bindMemory(to: Int16.self)
            for i in 0..<n { p[i] = Int16(sin(Double(i) * 2 * .pi * 220 / rate) * 2500).littleEndian }
        }
        return data
    }

    public func close() async {
        lock.lock()
        let wasClosed = closed
        closed = true
        lock.unlock()
        guard !wasClosed else { return }
        continuation.yield(.ended(reason: "closed"))
        continuation.finish()
    }
}
