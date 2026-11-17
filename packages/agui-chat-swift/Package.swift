// swift-tools-version: 5.10
// AGUIChat: a native SwiftUI client of the Dushes AG-UI servers (decision D-16). Contract: CONTRACT.md.

import PackageDescription

let package = Package(
    name: "AGUIChat",
    defaultLocalization: "en",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "AGUIChat", targets: ["AGUIChat"]),
        // the voice straight to the provider over WebRTC (D-24, a trial): its own product, so AGUIChat keeps no
        // dependencies (D-20)
        .library(name: "AGUIVoiceWebRTC", targets: ["AGUIVoiceWebRTC"]),
    ],
    targets: [
        .target(name: "AGUIChat", resources: [.process("Resources")]),
        // Google's WebRTC as built by stasel/WebRTC (the widely used Swift package of Google's own build, MIT/BSD),
        // M157 — the exact release and its checksum, the same as that package's own manifest
        .binaryTarget(
            name: "WebRTC",
            url: "https://github.com/stasel/WebRTC/releases/download/157.0.0/WebRTC-M157.xcframework.zip",
            checksum: "ffb1221be2138ecc6bc92300ae4f0157e18694d652db9921e4251992ea91a328"
        ),
        .target(name: "AGUIVoiceWebRTC", dependencies: ["AGUIChat", "WebRTC"]),
        .testTarget(
            name: "AGUIChatTests",
            dependencies: ["AGUIChat", "AGUIVoiceWebRTC"],
            resources: [.copy("Fixtures")]
        ),
    ]
)
