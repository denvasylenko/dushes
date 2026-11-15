import SwiftUI

/// The widget's own look (packages/agui-chat/src/styles.ts, `--agui-*`), light and dark: the same numbers, so the
/// native chat and `<agui-chat>` look like one component (owner 15.11: «the same components as in Duchess»).
public enum AGUITheme {
    static func dyn(_ light: UInt32, _ dark: UInt32) -> Color {
        #if canImport(UIKit)
        Color(UIColor { $0.userInterfaceStyle == .dark ? UIColor(hex: dark) : UIColor(hex: light) })
        #else
        Color(red: Double((light >> 16) & 0xFF) / 255, green: Double((light >> 8) & 0xFF) / 255, blue: Double(light & 0xFF) / 255)
        #endif
    }
    static let bg = dyn(0xFFFFFF, 0x1C1C1E)
    static let surface = dyn(0xFAFAFB, 0x242426)
    static let soft = dyn(0xF2F2F5, 0x2C2C2E)
    static let ink = dyn(0x1D1D1F, 0xF5F5F7)
    static let ink2 = dyn(0x6E6E73, 0xAEAEB2)
    static let ink3 = dyn(0x86868B, 0x8E8E93)
    static let line = dyn(0xECECF0, 0x333336)
    static let line2 = dyn(0xE3E3E8, 0x3A3A3C)
    static let accent = dyn(0x1D1D1F, 0xF5F5F7)
    static let onAccent = dyn(0xFFFFFF, 0x1D1D1F)
    static let link = dyn(0x0071E3, 0x4EA1FF)
    static let ok = dyn(0x34C759, 0x30D158)
    static let danger = dyn(0xFF3B30, 0xFF453A)
    static let dangerInk = dyn(0xD70015, 0xFF6961)
    static let cardBg = dyn(0xFFFFFF, 0x242426)       // light: the page's own colour + a shadow; dark: surface, no shadow

    static let radius: CGFloat = 14
    static let radiusSm: CGFloat = 10
    static let radiusLg: CGFloat = 20
}

#if canImport(UIKit)
extension UIColor {
    convenience init(hex: UInt32) {
        self.init(red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                  blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
    }
}
#endif

/// `.card`: radius 14, padding 12 on a phone, the widget's two-layer shadow in light, the surface in dark.
struct AGUICard: ViewModifier {
    @Environment(\.colorScheme) private var scheme
    func body(content: Content) -> some View {
        content
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(AGUITheme.cardBg, in: .rect(cornerRadius: AGUITheme.radius))
            .shadow(color: .black.opacity(scheme == .dark ? 0 : 0.06), radius: 1, y: 1)
            .shadow(color: .black.opacity(scheme == .dark ? 0 : 0.14), radius: 10, y: 6)
    }
}

/// `.btn.pri` / `.btn.sec`: a pill, 13 pt semibold, 44 pt tall on a phone.
struct AGUIButton: ButtonStyle {
    var primary = true
    @Environment(\.isEnabled) private var enabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .opacity(enabled ? 1 : 0.45)
            .font(.system(size: 13, weight: .semibold))
            .padding(.horizontal, 15)
            .frame(minHeight: 44)
            .foregroundStyle(primary ? AGUITheme.onAccent : AGUITheme.ink)
            .background(primary ? AGUITheme.accent : AGUITheme.bg, in: .capsule)
            .overlay(Capsule().strokeBorder(primary ? .clear : AGUITheme.line2, lineWidth: 1))
            .opacity(configuration.isPressed ? 0.7 : 1)
    }
}

extension View {
    func aguiCard() -> some View { modifier(AGUICard()) }
}
