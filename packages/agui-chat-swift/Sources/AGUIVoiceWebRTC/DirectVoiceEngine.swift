// The voice straight to the provider over WebRTC (D-24, a trial next to the relay): the phone's microphone and the
// voice go peer to peer (Opus, WebRTC's own echo cancelling, gain and jitter); the SDP is exchanged through the host's
// server, so no key of the provider reaches the phone; the provider's events (his words, the hand-over to the agent)
// come from that server — the same as the relay's text frames — so the host's voice mode stays as it is.
import AGUIChat
import Foundation

/// The host's server for one talk (its routes, its token): the engine knows no address.
public struct DirectVoiceLink: Sendable {
    /// The offer → (talk, answer). Throws `VoiceTransportError.refused(reason)` or `.unavailable`.
    public var session: @Sendable (_ offer: String) async throws -> (talk: String, answer: String)
    /// The talk's events (SSE, `data: {…}` lines).
    public var events: @Sendable (_ talk: String) -> URLRequest
    /// The talk ends (the server closes the provider's session and counts it).
    public var end: @Sendable (_ talk: String) async -> Void

    public init(session: @escaping @Sendable (String) async throws -> (talk: String, answer: String),
                events: @escaping @Sendable (String) -> URLRequest,
                end: @escaping @Sendable (String) async -> Void) {
        self.session = session
        self.events = events
        self.end = end
    }
}

/// One event of the server's stream → the voice's event; `nil` for the ones a host does not need (result, quiet).
public func directVoiceEvent(_ json: [String: Any]) -> VoiceEngineEvent? {
    let s = { (k: String) in json[k] as? String ?? "" }
    switch json["type"] as? String {
    case "hearing": return .hearing(s("delta"))
    case "heard":
        if let answers = json["answers"] as? [[String: Any]], let a = answers.first, let id = a["card_id"] as? String {
            return .answer(cardId: id, type: a["type"] as? String ?? "", accepted: a["accepted"] as? Bool ?? false,
                           text: s("text"))
        }
        return .heard(s("text"))
    case "spoken": return .spoken(s("delta"))
    case "interrupted": return .interrupted
    case "echo": return .echo
    case "error": return .error(s("code"))
    case "ended": return .ended(reason: s("reason").isEmpty ? "closed" : s("reason"))
    default: return nil
    }
}

#if os(iOS)
import AVFoundation
import WebRTC

@MainActor
public final class DirectVoiceEngine: NSObject, VoiceEngine {
    public let events: AsyncStream<VoiceEngineEvent>
    private let continuation: AsyncStream<VoiceEngineEvent>.Continuation
    private let link: DirectVoiceLink
    private static let factory: RTCPeerConnectionFactory = {
        RTCInitializeSSL()
        return RTCPeerConnectionFactory(encoderFactory: RTCDefaultVideoEncoderFactory(),
                                        decoderFactory: RTCDefaultVideoDecoderFactory())
    }()
    private var pc: RTCPeerConnection?
    private var mic: RTCAudioTrack?
    private var talk: String?
    private var sse: Task<Void, Never>?
    private var levels: Task<Void, Never>?
    private var lastSpoken = Date.distantPast
    private var cutUntilNewAnswer = false
    private var routeWatch: NSObjectProtocol?
    public var diagnostics: ((String) -> Void)?

    public init(link: DirectVoiceLink) {
        self.link = link
        (events, continuation) = AsyncStream.makeStream(of: VoiceEngineEvent.self)
        super.init()
    }

    public func start(threadId: String) async throws {
        // the phone's audio for a call: the speaker unless headphones, WebRTC's own processing on the microphone
        let audio = RTCAudioSession.sharedInstance()
        audio.lockForConfiguration()
        try? audio.setCategory(.playAndRecord, with: [.defaultToSpeaker, .allowBluetoothHFP])
        try? audio.setMode(.voiceChat)
        audio.unlockForConfiguration()
        speakerUnlessHeadphones()
        // the system drops the speaker override on every route change (WebRTC's own audio unit starting, a call,
        // AirPods): set it again after each one — the owner 17.11, "like talking on the phone"
        routeWatch = NotificationCenter.default.addObserver(forName: AVAudioSession.routeChangeNotification,
                                                            object: nil, queue: .main) { [weak self] note in
            let raw = note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt
            guard raw.flatMap(AVAudioSession.RouteChangeReason.init) != .override else { return }
            Task { @MainActor in self?.speakerUnlessHeadphones("route change \(raw ?? 0)") }
        }

        let config = RTCConfiguration()
        config.sdpSemantics = .unifiedPlan
        let constraints = RTCMediaConstraints(mandatoryConstraints: nil, optionalConstraints: nil)
        guard let pc = Self.factory.peerConnection(with: config, constraints: constraints, delegate: nil) else {
            throw VoiceTransportError.unavailable
        }
        self.pc = pc
        let track = Self.factory.audioTrack(with: Self.factory.audioSource(with: constraints), trackId: "mic")
        pc.add(track, streamIds: ["voice"])
        mic = track
        let offer = try await pc.offer(for: RTCMediaConstraints(
            mandatoryConstraints: ["OfferToReceiveAudio": "true"], optionalConstraints: nil))
        try await pc.setLocalDescription(offer)
        diagnostics?("direct: offer")
        let answer: (talk: String, answer: String)
        do {
            answer = try await link.session(offer.sdp)
        } catch {
            diagnostics?("direct: session failed \(error)")
            pc.close()
            throw error
        }
        talk = answer.talk
        try await pc.setRemoteDescription(RTCSessionDescription(type: .answer, sdp: answer.answer))
        diagnostics?("direct: connected, talk \(answer.talk)")
        listen(answer.talk)
        watchLevel()
    }

    private func listen(_ talk: String) {
        let request = link.events(talk)
        sse = Task { [weak self] in
            do {
                let (bytes, _) = try await URLSession.shared.bytes(for: request)
                for try await line in bytes.lines {
                    guard line.hasPrefix("data:") else { continue }
                    let body = line.dropFirst(5).trimmingCharacters(in: .whitespaces)
                    guard let d = body.data(using: .utf8),
                          let json = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
                          let e = directVoiceEvent(json) else { continue }
                    await self?.received(e)
                }
            } catch {}
            await self?.received(.ended(reason: "closed"))
        }
    }

    private func received(_ e: VoiceEngineEvent) {
        switch e {
        case .interrupted:
            // the voice comes straight from the provider: its tail is cut here, until the next answer
            cutUntilNewAnswer = true
            remoteAudio(on: false)
        case .heard:
            cutUntilNewAnswer = false
            remoteAudio(on: true)
        case .spoken:
            if cutUntilNewAnswer, Date().timeIntervalSince(lastSpoken) > 0.8 {
                cutUntilNewAnswer = false
                remoteAudio(on: true)
            }
            lastSpoken = Date()
        default: break
        }
        continuation.yield(e)
        if case .ended = e { Task { await end() } }
    }

    private func remoteAudio(on: Bool) {
        for t in pc?.transceivers ?? [] where t.mediaType == .audio {
            (t.receiver.track as? RTCAudioTrack)?.isEnabled = on
        }
    }

    /// His level for the light, from WebRTC's own statistics (~10 a second).
    private func watchLevel() {
        levels = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(100))
                guard let self, let pc = self.pc else { return }
                let report = await withCheckedContinuation { (c: CheckedContinuation<RTCStatisticsReport, Never>) in
                    pc.statistics { c.resume(returning: $0) }
                }
                let level = report.statistics.values.first { $0.type == "media-source" }?
                    .values["audioLevel"] as? Double ?? 0
                self.continuation.yield(.level(min(1, level * 4)))
            }
        }
    }

    public func setMuted(_ muted: Bool) { mic?.isEnabled = !muted }

    /// The loudspeaker unless headphones, Bluetooth, a car or AirPlay take the sound (`.voiceChat` alone is the earpiece).
    private func speakerUnlessHeadphones(_ why: String = "") {
        let session = AVAudioSession.sharedInstance()
        let before = session.currentRoute.outputs.map { $0.portType.rawValue }.joined(separator: ",")
        let external = session.currentRoute.outputs.contains {
            [.headphones, .bluetoothA2DP, .bluetoothHFP, .bluetoothLE, .carAudio, .airPlay, .usbAudio].contains($0.portType)
        }
        if !external {
            let audio = RTCAudioSession.sharedInstance()
            audio.lockForConfiguration()
            try? audio.overrideOutputAudioPort(.speaker)
            audio.unlockForConfiguration()
        }
        let after = session.currentRoute.outputs.map { $0.portType.rawValue }.joined(separator: ",")
        diagnostics?("direct: route \(before) → \(after)\(why.isEmpty ? "" : " (" + why + ")")")
    }

    public func end() async {
        if let routeWatch { NotificationCenter.default.removeObserver(routeWatch) }
        routeWatch = nil
        sse?.cancel(); sse = nil
        levels?.cancel(); levels = nil
        pc?.close(); pc = nil
        guard let talk else { return }
        self.talk = nil
        await link.end(talk)
        continuation.yield(.ended(reason: "closed"))
        continuation.finish()
    }
}
#endif
