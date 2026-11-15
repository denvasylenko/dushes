#if os(iOS)
import AVFoundation
import UIKit

/// The voice mode's sound on iOS without third-party code (D-20): `AVAudioEngine` with Apple's voice processing (echo
/// and noise cancelling, so the voice is not heard back from the speaker), the microphone converted to 16-bit mono PCM
/// at the transport's rate and sent up, the voice's PCM played back, the sound level for the orb. A call, Siri or the
/// app going to the background ends the talk (an open one is billed by the second).
@MainActor
public final class AudioVoiceEngine: VoiceEngine {
    public let events: AsyncStream<VoiceEngineEvent>
    private let continuation: AsyncStream<VoiceEngineEvent>.Continuation
    private let transport: VoiceTransport
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private var converter: AVAudioConverter?
    private var wireFormat: AVAudioFormat!
    private var playFormat: AVAudioFormat!
    private var pump: Task<Void, Never>?
    private var observers: [NSObjectProtocol] = []
    private var muted = false
    private var running = false

    public init(transport: VoiceTransport) {
        (events, continuation) = AsyncStream.makeStream(of: VoiceEngineEvent.self)
        self.transport = transport
    }

    public func start(threadId: String) async throws {
        guard await AVAudioApplication.requestRecordPermission() else { throw VoiceEngineError.microphone }
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetoothHFP])
        try session.setActive(true)

        try await transport.connect(threadId: threadId)
        let rate = transport.sampleRate
        wireFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: rate, channels: 1, interleaved: true)
        playFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: rate, channels: 1, interleaved: false)

        try engine.inputNode.setVoiceProcessingEnabled(true)   // echo and noise cancelling by the system
        engine.attach(player)
        engine.connect(player, to: engine.mainMixerNode, format: playFormat)
        running = true
        watchSystem()                                          // before the start: voice processing reconfigures at once
        try wire()
        pump = Task { [weak self] in
            guard let self else { return }
            for await event in transport.incoming { self.received(event) }
            await self.end()
        }
    }

    /// The microphone tap and the converter for the input's current format, then the engine started. Called again when
    /// the system reconfigures the audio (voice processing switching on, a route change): the engine stops then.
    private func wire() throws {
        let input = engine.inputNode
        input.removeTap(onBus: 0)
        let micFormat = input.outputFormat(forBus: 0)
        guard micFormat.sampleRate > 0, micFormat.channelCount > 0 else { return }
        converter = AVAudioConverter(from: micFormat, to: wireFormat)
        input.installTap(onBus: 0, bufferSize: 2048, format: micFormat) { [weak self] buffer, _ in
            self?.captured(buffer)
        }
        engine.prepare()
        try engine.start()
        player.play()
    }

    public func setMuted(_ muted: Bool) { self.muted = muted }

    public func end() async {
        guard running else { return }
        running = false
        engine.inputNode.removeTap(onBus: 0)
        player.stop()
        engine.stop()
        for o in observers { NotificationCenter.default.removeObserver(o) }
        observers = []
        pump?.cancel()
        await transport.close()
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        continuation.yield(.ended(reason: "closed"))
        continuation.finish()
    }

    // MARK: up: the microphone

    nonisolated private func captured(_ buffer: AVAudioPCMBuffer) {
        // the sound level for the orb (root mean square of the frame)
        var level: Double = 0
        if let ch = buffer.floatChannelData?[0] {
            var sum: Float = 0
            for i in 0..<Int(buffer.frameLength) { sum += ch[i] * ch[i] }
            level = min(1, Double(sqrt(sum / Float(max(1, buffer.frameLength)))) * 8)
        }
        Task { @MainActor [weak self] in self?.up(buffer, level: level) }
    }

    private func up(_ buffer: AVAudioPCMBuffer, level: Double) {
        guard running, let converter, let wireFormat else { return }
        continuation.yield(.level(muted ? 0 : level))
        let ratio = wireFormat.sampleRate / buffer.format.sampleRate
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 32
        guard let out = AVAudioPCMBuffer(pcmFormat: wireFormat, frameCapacity: capacity) else { return }
        var fed = false
        var error: NSError?
        converter.convert(to: out, error: &error) { _, status in
            if fed { status.pointee = .noDataNow; return nil }
            fed = true
            status.pointee = .haveData
            return buffer
        }
        guard error == nil, out.frameLength > 0, let samples = out.int16ChannelData?[0] else { return }
        var data = Data(bytes: samples, count: Int(out.frameLength) * 2)
        if muted { data = Data(count: data.count) }     // silence, so the talk stays open but hears nothing
        transport.send(audio: data)
    }

    // MARK: down: the voice and the talk

    private func received(_ event: VoiceTransportEvent) {
        switch event {
        case .audio(let pcm): play(pcm)
        case .heard(let text): continuation.yield(.heard(text))
        case .spoken(let text): continuation.yield(.spoken(text))
        case .error(let code): continuation.yield(.error(code))
        case .ended(let reason): continuation.yield(.ended(reason: reason))
        }
    }

    private func play(_ pcm: Data) {
        guard running, let playFormat else { return }
        let frames = AVAudioFrameCount(pcm.count / 2)
        guard frames > 0, let buffer = AVAudioPCMBuffer(pcmFormat: playFormat, frameCapacity: frames),
              let out = buffer.floatChannelData?[0] else { return }
        buffer.frameLength = frames
        pcm.withUnsafeBytes { raw in
            let s = raw.bindMemory(to: Int16.self)
            for i in 0..<Int(frames) { out[i] = Float(Int16(littleEndian: s[i])) / 32768 }
        }
        player.scheduleBuffer(buffer)
    }

    // MARK: calls, Siri, background

    private func watchSystem() {
        let nc = NotificationCenter.default
        observers.append(nc.addObserver(forName: AVAudioSession.interruptionNotification, object: nil, queue: .main) { [weak self] note in
            let type = (note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt).flatMap(AVAudioSession.InterruptionType.init)
            if type == .began { Task { @MainActor in await self?.end() } }
        })
        observers.append(nc.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in await self?.end() }
        })
        observers.append(nc.addObserver(forName: AVAudioSession.mediaServicesWereResetNotification, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in await self?.end() }
        })
        // headphones in or out, voice processing taking over: the engine stops — wire it again, the talk goes on
        observers.append(nc.addObserver(forName: .AVAudioEngineConfigurationChange, object: engine, queue: .main) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.running else { return }
                do { try self.wire() } catch { await self.end() }
            }
        })
    }
}

public enum VoiceEngineError: Error { case microphone }
#endif
