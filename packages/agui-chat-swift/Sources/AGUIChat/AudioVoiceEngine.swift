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
    /// The voice slows a little as it trails off (barge-in), its pitch kept.
    private let pace = AVAudioUnitTimePitch()
    private var converter: AVAudioConverter?
    private var wireFormat: AVAudioFormat!
    private var playFormat: AVAudioFormat!
    private var pump: Task<Void, Never>?
    private var observers: [NSObjectProtocol] = []
    private var muted = false
    private var running = false
    /// Ended before it was running (✕ while connecting): the socket opened meanwhile is closed at once — left open it
    /// stayed a paid session with no audio until the server's timeout (owner's phone, 16.11).
    private var cancelled = false
    private var played = 0
    /// Barge-in: the rest of an interrupted answer is dropped until the server says so (`interrupted`), his phrase
    /// is heard, or the voice's audio has paused (a new answer).
    private var silenced = false
    private var droppedAt = Date.distantPast
    private var speakingUntil = Date.distantPast       // when the audio scheduled so far ends
    private var fade: Task<Void, Never>?
    private var answerStarted = Date.distantPast       // the current answer's audio: when it began, how long it is
    private var answerLength: TimeInterval = 0
    /// The microphone runs before the socket is up (CPO 17.11: recording ≤ 0.5 s after the tap): its audio waits here
    /// and goes up in order as soon as the transport is connected (at most 10 s of it).
    private var linked = false
    /// The diagnostics' first 3 s of the microphone, piece by piece (its frames and level): where its first words go.
    private var micOnAt: Date?
    private var waiting: [Data] = []
    private var waitingBytes = 0
    /// A line a second about the sound path (the route, what was scheduled, the level at the mixer): for a check on a
    /// real device, where nobody but the person hears the speaker.
    public var diagnostics: (@Sendable (String) -> Void)?
    /// Apple's voice processing (echo and noise cancelling, gain) on the microphone. Off only for a measurement: the
    /// owner's speech reached the provider at about −55 dB (the cabinet team, 17.11) — is it the processing?
    public var voiceProcessing = true
    /// Each piece of the person's audio as it goes up (PCM16 mono at the transport's rate): a host's measurement only.
    public var sentAudio: ((Data) -> Void)?

    /// The microphone opens no earlier than this (a host's start sound must not go to the voice): set before `start`.
    public var microphoneNotBefore: Date?

    public init(transport: VoiceTransport) {
        (events, continuation) = AsyncStream.makeStream(of: VoiceEngineEvent.self)
        self.transport = transport
    }

    public func start(threadId: String) async throws {
        guard await AVAudioApplication.requestRecordPermission() else { throw VoiceEngineError.microphone }
        // the socket opens at once, in parallel with the audio: the microphone does not wait for the server's
        // `started` — what it records meanwhile is kept and sent when the link is up (CPO 17.11)
        let link = Task { [transport] in try await transport.connect(threadId: threadId) }
        // off the main thread: activating the session there held the app's frames for up to ~1 s while the system's
        // own animations ran on (a host saw its screen white under the voice)
        try await Task.detached(priority: .userInitiated) {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetoothHFP])
            try session.setActive(true)
        }.value
        speakerUnlessHeadphones()
        let rate = transport.sampleRate                       // fixed by the transport, known before it connects
        wireFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: rate, channels: 1, interleaved: true)
        playFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: rate, channels: 1, interleaved: false)

        // echo and noise cancelling by the system; off the main thread too (it reconfigures the audio for ~.3 s)
        nonisolated(unsafe) let input = engine.inputNode
        let processing = voiceProcessing
        try await Task.detached(priority: .userInitiated) { try input.setVoiceProcessingEnabled(processing) }.value
        speakerUnlessHeadphones()                             // voice processing re-routes to the earpiece
        if cancelled { link.cancel(); await transport.close(); throw CancellationError() }
        engine.attach(player)
        engine.attach(pace)
        // a time-pitch unit colours the voice even at rate 1 (a phase vocoder: «metallic, robotic» — the owner,
        // 17.11): it is bypassed, and works only for the 350 ms of a trail-off
        pace.bypass = true
        running = true
        watchSystem()                                          // before the start: voice processing reconfigures at once
        try wire(startNow: false)
        // starting the engine takes the audio hardware (up to ~.2 s on a phone): off the main thread, like the
        // session, so the host's opening animation runs on
        nonisolated(unsafe) let audio = engine
        try await Task.detached(priority: .userInitiated) {
            audio.prepare()
            try audio.start()
        }.value
        guard running else {                                  // ended while the engine started: stop it again
            nonisolated(unsafe) let late = engine
            await Task.detached { late.stop() }.value
            link.cancel()
            await transport.close()
            throw CancellationError()
        }
        player.play()
        speakerUnlessHeadphones()
        micOnAt = Date()
        report("microphone on")
        // the link, then what the microphone kept, then the live audio; the server's events from then on
        do {
            try await link.value
        } catch {
            report("end: the link failed \(error)")
            await end()
            throw error
        }
        guard running else { await transport.close(); throw CancellationError() }
        linked = true
        report("linked, \(waitingBytes / 2) samples kept sent")
        for piece in waiting { transport.send(audio: piece) }
        waiting = []
        waitingBytes = 0
        pump = Task { [weak self] in
            guard let self else { return }
            for await event in transport.incoming { self.received(event) }
            self.report("end: the transport's stream finished")
            await self.end()
        }
    }

    /// The microphone tap and the converter for the input's current format, then the engine started. Called again when
    /// the system reconfigures the audio (voice processing switching on, a route change): the engine stops then.
    private func wire(startNow: Bool = true) throws {
        let input = engine.inputNode
        input.removeTap(onBus: 0)
        let micFormat = input.outputFormat(forBus: 0)
        guard micFormat.sampleRate > 0, micFormat.channelCount > 0 else { return }
        converter = AVAudioConverter(from: micFormat, to: wireFormat)
        // the whole output chain again, by hand: after voice processing switches on, the output's format is new and
        // the connections made before it carry no sound (owner 16.11: the words showed, nothing was heard)
        engine.disconnectNodeOutput(player)
        engine.disconnectNodeOutput(pace)
        engine.connect(player, to: pace, format: playFormat)
        engine.connect(pace, to: engine.mainMixerNode, format: playFormat)
        engine.connect(engine.mainMixerNode, to: engine.outputNode, format: engine.outputNode.inputFormat(forBus: 0))
        engine.mainMixerNode.outputVolume = 1
        player.volume = 1
        watchMixer()
        input.installTap(onBus: 0, bufferSize: 2048, format: micFormat) { [weak self] buffer, _ in
            self?.captured(buffer)
        }
        guard startNow else { return }                       // the first start: `startEngine()`, off the main thread
        engine.prepare()
        try engine.start()
        player.play()
        speakerUnlessHeadphones()
        report("wired mic \(Int(micFormat.sampleRate)) Hz, out \(Int(engine.outputNode.inputFormat(forBus: 0).sampleRate)) Hz × \(engine.outputNode.inputFormat(forBus: 0).channelCount), engine \(engine.isRunning), player \(player.isPlaying)")
    }

    /// The loudspeaker, unless headphones or a car are connected: `.voiceChat` alone talks into the earpiece, and the
    /// system drops the override on every route change (voice processing, a short sound's session, a call, AirPods)
    /// — the owner 17.11: "like talking on the phone". So it is set again after each one (`watchSystem`).
    private func speakerUnlessHeadphones(_ why: String = "") {
        let session = AVAudioSession.sharedInstance()
        let before = session.currentRoute.outputs.map { $0.portType.rawValue }.joined(separator: ",")
        let external = session.currentRoute.outputs.contains {
            [.headphones, .bluetoothA2DP, .bluetoothHFP, .bluetoothLE, .carAudio, .airPlay, .usbAudio].contains($0.portType)
        }
        if !external { try? session.overrideOutputAudioPort(.speaker) }
        let after = session.currentRoute.outputs.map { $0.portType.rawValue }.joined(separator: ",")
        report("route \(before) → \(after)\(why.isEmpty ? "" : " (" + why + ")")")
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
        guard running else {
            cancelled = true
            await transport.close()                   // a socket that is opening or open: closed, not left to time out
            return
        }
        running = false
        // stopping the hardware off the main thread: in the frame of the host's closing animation it held it
        // (~.3 s on the owner's phone)
        nonisolated(unsafe) let audio = engine, voice = player
        await Task.detached(priority: .userInitiated) {
            audio.inputNode.removeTap(onBus: 0)
            voice.stop()
            audio.stop()
        }.value
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
        var rms: Float = 0
        if let ch = buffer.floatChannelData?[0], buffer.frameLength > 0 {
            var sum: Float = 0
            for i in 0..<Int(buffer.frameLength) { sum += ch[i] * ch[i] }
            rms = sqrt(sum / Float(buffer.frameLength))
        }
        let db = rms > 0 ? 20 * log10(Double(rms)) : -120
        Task { @MainActor [weak self] in self?.up(buffer, level: level, db: db) }
    }

    private func up(_ buffer: AVAudioPCMBuffer, level: Double, db: Double = 0) {
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
        if let on = micOnAt, Date().timeIntervalSince(on) < 3 {
            report(String(format: "mic piece in %d × %d ch → out %d frames, %.1f dB RMS%@", Int(buffer.frameLength),
                          Int(buffer.format.channelCount), Int(out.frameLength), db, linked ? "" : " (kept)"))
        }
        var data = Data(bytes: samples, count: Int(out.frameLength) * 2)
        if muted { data = Data(count: data.count) }     // silence, so the talk stays open but hears nothing
        // the host's start sound is not sent (it would be heard as his words)
        if let at = microphoneNotBefore, Date() < at { data = Data(count: data.count) }
        sentAudio?(data)
        guard linked else {                             // the link is not up yet: kept, in order
            waiting.append(data)
            waitingBytes += data.count
            while waitingBytes > Int(wireFormat.sampleRate) * 2 * 10, !waiting.isEmpty {
                waitingBytes -= waiting.removeFirst().count
            }
            return
        }
        transport.send(audio: data)
    }

    // MARK: down: the voice and the talk

    private func received(_ event: VoiceTransportEvent) {
        switch event {
        case .audio(let pcm): play(pcm)
        case .hearing(let text):
            // not a barge-in by itself: on a loudspeaker the voice's own echo comes back as «hearing», and trailing off
            // on it cut every answer as it began (owner 17.11: the words showed, nothing was heard). The server's
            // `interrupted` decides (3+ words, not the echo)
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
        let length = Double(frames) / playFormat.sampleRate
        if Date() >= speakingUntil { answerStarted = Date(); answerLength = 0 }   // audio after a pause: a new answer
        answerLength += length
        speakingUntil = max(Date(), speakingUntil).addingTimeInterval(length)
    }

    /// The voice «goes into silence» like a person cut off mid-word (owner 16.11, the mobile designer's curves): over
    /// 350 ms the volume follows (1 − t/350)^2.5 — clearly quieter first, then a soft tail to zero, no click — and the
    /// speech slows 1.0 → 0.9 linearly with its pitch kept; then the queued audio is dropped. The host's light and text
    /// follow `.trailingOff` over the same 350 ms.
    private func trailOff() {
        guard fade == nil, Date() < speakingUntil || player.isPlaying else { return }
        silenced = true
        droppedAt = Date()
        let heard = answerLength > 0 ? min(1, max(0, Date().timeIntervalSince(answerStarted) / answerLength)) : 1
        continuation.yield(.trailingOff(said: heard))
        let start = Date()
        fade = Task { [weak self] in
            while let self, !Task.isCancelled {
                let t = Date().timeIntervalSince(start) / 0.35
                if t >= 1 { break }
                self.player.volume = Float(pow(1 - t, 2.5))
                self.pace.bypass = false
                self.pace.rate = Float(1 - 0.1 * t)
                try? await Task.sleep(for: .milliseconds(5))
            }
            guard let self else { return }
            self.player.volume = 0
            self.player.stop()                         // drops everything scheduled
            self.player.volume = 1
            self.pace.rate = 1
            self.pace.bypass = true
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
            guard type == .began else { return }
            Task { @MainActor in self?.report("end: audio interruption"); await self?.end() }
        })
        observers.append(nc.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in self?.report("end: background"); await self?.end() }
        })
        observers.append(nc.addObserver(forName: AVAudioSession.mediaServicesWereResetNotification, object: nil, queue: .main) { [weak self] _ in
            Task { @MainActor in self?.report("end: media services reset"); await self?.end() }
        })
        // any route change while talking: the loudspeaker again (the override is gone after it), unless the change
        // is our own override or headphones / Bluetooth / a car took the sound
        observers.append(nc.addObserver(forName: AVAudioSession.routeChangeNotification, object: nil, queue: .main) { [weak self] note in
            let raw = note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt
            let reason = raw.flatMap(AVAudioSession.RouteChangeReason.init)
            guard reason != .override else { return }
            Task { @MainActor in
                guard let self, self.running else { return }
                self.speakerUnlessHeadphones("route change \(raw ?? 0)")
            }
        })
        // headphones in or out, voice processing taking over: the engine stops — wire it again, the talk goes on
        observers.append(nc.addObserver(forName: .AVAudioEngineConfigurationChange, object: engine, queue: .main) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.running else { return }
                self.report("configuration change")
                do { try self.wire() } catch { self.report("end: rewire failed \(error)"); await self.end() }
            }
        })
    }
}

public enum VoiceEngineError: Error { case microphone }
#endif
