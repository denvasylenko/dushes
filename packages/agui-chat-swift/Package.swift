// swift-tools-version: 5.10
// AGUIChat: a native SwiftUI client of the Dushes AG-UI servers (decision D-16). Contract: CONTRACT.md.

import PackageDescription

let package = Package(
    name: "AGUIChat",
    defaultLocalization: "en",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "AGUIChat", targets: ["AGUIChat"]),
    ],
    targets: [
        .target(name: "AGUIChat", resources: [.process("Resources")]),
        .testTarget(
            name: "AGUIChatTests",
            dependencies: ["AGUIChat"],
            resources: [.copy("Fixtures")]
        ),
    ]
)
