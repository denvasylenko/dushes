import SwiftUI

/// The voice orb (Head of Design's tokens --hf-voice-*): 84 pt, a sky in the site's colour and one white cloud whose
/// edge goes round in 4 s (2.6 s while thinking); the size moves by ±2% only; with «Reduce Motion» it stands still and
/// the state is in the words under it.
struct VoiceOrb: View {
    let state: VoiceController.State
    let level: Double
    var tint: Color = AGUITheme.link
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        TimelineView(.animation(paused: reduce)) { time in
            let t = time.date.timeIntervalSinceReferenceDate
            let period = state == .thinking ? 2.6 : 4.0
            let angle = reduce ? 0.6 : (t / period).truncatingRemainder(dividingBy: 1) * 2 * .pi
            let breathe = reduce ? 1 : 1 + 0.02 * sin(t * 2 * .pi / 3) + (state == .listening ? 0.02 * level : 0)
            Canvas { ctx, size in
                let r = min(size.width, size.height) / 2
                let c = CGPoint(x: size.width / 2, y: size.height / 2)
                let disc = Path(ellipseIn: CGRect(x: c.x - r, y: c.y - r, width: 2 * r, height: 2 * r))
                ctx.clip(to: disc)
                ctx.fill(disc, with: .linearGradient(Gradient(colors: [tint.opacity(0.75), tint]),
                                                     startPoint: CGPoint(x: c.x, y: c.y - r), endPoint: CGPoint(x: c.x, y: c.y + r)))
                // one white cloud, blurred, going round
                var cloud = ctx
                cloud.addFilter(.blur(radius: r * 0.28))
                let off = CGPoint(x: c.x + cos(angle) * r * 0.42, y: c.y + sin(angle) * r * 0.42)
                cloud.fill(Path(ellipseIn: CGRect(x: off.x - r * 0.85, y: off.y - r * 0.6, width: r * 1.7, height: r * 1.2)),
                           with: .color(.white.opacity(0.92)))
            }
            .frame(width: 84, height: 84)
            .scaleEffect(breathe)
            .shadow(color: tint.opacity(0.35), radius: 18, y: 4)
            .opacity(state == .muted ? 0.55 : 1)
            .overlay {
                if state == .thinking {
                    RoundedRectangle(cornerRadius: 2).strokeBorder(.white, lineWidth: 2).frame(width: 14, height: 14)
                }
            }
        }
        .accessibilityHidden(true)
    }
}
