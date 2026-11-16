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
    private var played = 0
    /// Barge-in: the rest of an interrupted answer is dropped until the server says so (`interrupted`), his phrase
    /// is heard, or the voice's audio has paused (a new answer).
    private var silenced = false
    private var droppedAt = Date.distantPast
    private var speakingUntil = Date.distantPast       // when the audio scheduled so far ends
    private var fade: Task<Void, Never>?
    /// A line a second about the sound path (the route, what was scheduled, the level at the mixer): for a check on a
    /// real device, where nobody but the person hears the speaker.
    public var diagnostics: (@Sendable (String) -> Void)?

    /// The microphone opens no earlier than this (a host's start sound must not go to the voice): set before `start`.
    public var microphoneNotBefore: Date?

    public init(transport: VoiceTransport) {
        (events, continuation) = AsyncStream.makeStream(of: VoiceEngineEvent.self)
        self.transport = transport
    }

    public func start(threadId: String) async throws {
        guard await AVAudioApplication.requestRecordPermission() else { throw VoiceEngineError.microphone }
        // off the main thread: activating the session there held the app's frames for up to ~1 s while the system's
        // own animations ran on (a host saw its screen white under the voice)
        try await Task.detached(priority: .userInitiated) {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetoothHFP])
            try session.setActive(true)
        }.value
        speakerUnlessHeadphones()

        try await transport.connect(threadId: threadId)
        let rate = transport.sampleRate
        wireFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: rate, channels: 1, interleaved: true)
        playFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: rate, channels: 1, interleaved: false)

        // echo and noise cancelling by the system; off the main thread too (it reconfigures the audio for ~.3 s)
        nonisolated(unsafe) let input = engine.inputNode
        try await Task.detached(priority: .userInitiated) { try input.setVoiceProcessingEnabled(true) }.value
        engine.attach(player)
        running = true
        if let at = microphoneNotBefore, at.timeIntervalSinceNow > 0 {
            try? await Task.sleep(for: .seconds(at.timeIntervalSinceNow))
        }
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
        // the whole output chain again, by hand: after voice processing switches on, the output's format is new and
        // the connections made before it carry no sound (owner 16.11: the words showed, nothing was heard)
        engine.disconnectNodeOutput(player)
        engine.connect(player, to: engine.mainMixerNode, format: playFormat)
        engine.connect(engine.mainMixerNode, to: engine.outputNode, format: engine.outputNode.inputFormat(forBus: 0))
        engine.mainMixerNode.outputVolume = 1
        player.volume = 1
        watchMixer()
        input.installTap(onBus: 0, bufferSize: 2048, format: micFormat) { [weak self] buffer, _ in
            self?.captured(buffer)
        }
        engine.prepare()
        try engine.start()
        player.play()
        speakerUnlessHeadphones()
        report("wired mic \(Int(micFormat.sampleRate)) Hz, out \(Int(engine.outputNode.inputFormat(forBus: 0).sampleRate)) Hz × \(engine.outputNode.inputFormat(forBus: 0).channelCount), engine \(engine.isRunning), player \(player.isPlaying)")
    }

    /// The loudspeaker, unless headphones or a car are connected: `.voiceChat` alone talks into the earpiece.
    private func speakerUnlessHeadphones() {
        let session = AVAudioSession.sharedInstance()
        let external = session.currentRoute.outputs.contains {
            [.headphones, .bluetoothA2DP, .bluetoothHFP, .bluetoothLE, .carAudio, .airPlay, .usbAudio].contains($0.portType)
        }
        if !external { try? session.overrideOutputAudioPort(.speaker) }
        report("route " + session.currentRoute.outputs.map { $0.portType.rawValue }.joined(separator: ","))
    }

    private var mixerPeak: Float = 0
    private var mixerTapped = false
    private func watchMixer() {
        guard diagnostics != nil, !mixerTapped else { return }
        mixerTapped = true
        let mixer = engine.mainMixerNode
        var frames = 0
        var peak: Float = 0
        mixer.installTap(onBus: 0, bufferSize: 4096, format: nil) { [weak self] buffer, _ in
            if let ch = buffer.floatChannelData?[0] {
                for i in 0..<Int(buffer.frameLength) { peak = max(peak, abs(ch[i])) }
            }
            frames += Int(buffer.frameLength)
            if frames >= Int(buffer.format.sampleRate) {
                let p = peak
                frames = 0; peak = 0
                Task { @MainActor [weak self] in self?.report(String(format: "mixer peak %.3f, scheduled %d", p, self?.played ?? 0)) }
            }
        }
    }

    private func report(_ line: String) { diagnostics?(line) }

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
        // off the main thread, like the activation: it holds the frame of the host's closing animation
        await Task.detached(priority: .userInitiated) {
            try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        }.value
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
        case .hearing(let text):
            // he speaks over the voice: it trails off at once, without waiting for the server
            if Date() < speakingUntil { trailOff() }
            continuation.yield(.hearing(text))
        case .echo: continuation.yield(.echo)
        case .answer(let c, let t, let a, let x): continuation.yield(.answer(cardId: c, type: t, accepted: a, text: x))
        case .interrupted:
            trailOff()
            silenced = false                         // what comes after it is the new answer (server v150)
            continuation.yield(.interrupted)
        case .heard(let text):
            silenced = false
            continuation.yield(.heard(text))
        case .spoken(let text): continuation.yield(.spoken(text))
        case .error(let code): continuation.yield(.error(code))
        case .ended(let reason): continuation.yield(.ended(reason: reason))
        }
    }

    private func play(_ pcm: Data) {
        guard running, let playFormat else { return }
        if silenced {
            // the interrupted answer's tail; a pause in the stream means a new answer has started
            if Date().timeIntervalSince(droppedAt) < 0.8 { droppedAt = Date(); return }
            silenced = false
        }
        let frames = AVAudioFrameCount(pcm.count / 2)
        guard frames > 0, let buffer = AVAudioPCMBuffer(pcmFormat: playFormat, frameCapacity: frames),
              let out = buffer.floatChannelData?[0] else { return }
        buffer.frameLength = frames
        pcm.withUnsafeBytes { raw in
            let s = raw.bindMemory(to: Int16.self)
            for i in 0..<Int(frames) { out[i] = Float(Int16(littleEndian: s[i])) / 32768 }
        }
        if !player.isPlaying { player.play() }
        player.scheduleBuffer(buffer)
        played += 1
        speakingUntil = max(Date(), speakingUntil).addingTimeInterval(Double(frames) / playFormat.sampleRate)
    }

    /// The voice falls silent like a person cut off mid-word (owner 16.11, mobile designer): the volume follows
    /// e^(−t/55 ms) for 200 ms (−32 dB at the end, no click), then the queued audio is dropped.
    private func trailOff() {
        guard fade == nil, Date() < speakingUntil || player.isPlaying else { return }
        silenced = true
        droppedAt = Date()
        let start = Date()
        fade = Task { [weak self] in
            while let self, !Task.isCancelled {
                let t = Date().timeIntervalSince(start)
                if t >= 0.2 { break }
                self.player.volume = Float(exp(-t / 0.055))
                try? await Task.sleep(for: .milliseconds(5))
            }
            guard let self else { return }
            self.player.stop()                         // drops everything scheduled
            self.player.volume = 1
            if self.running { self.player.play() }
            self.speakingUntil = .distantPast
            self.fade = nil
        }
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
