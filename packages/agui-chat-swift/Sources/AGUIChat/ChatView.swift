import SwiftUI

/// The chat, drawn with the widget's numbers (`--agui-*`, styles.ts) in native SwiftUI: the answer as text on the page
/// (15 pt), the person's words in a soft bubble (radius 20, 10/16, at most 85%), the steps line (13 pt, ink-2), chips
/// (a pill with a line-2 border), cards (radius 14, padding 12, the widget's shadow), options (radius 10, line-2 border,
/// the chosen one ringed), one input line with «+», the microphone and send. The host draws its own cards (`hostCard`)
/// and records the voice (`onMicrophone`).
public struct ChatView<HostCard: View>: View {
    @Bindable var store: ChatStore
    var placeholder: LocalizedStringKey
    var onMicrophone: (() -> Void)?
    var hostCard: (String, JSONValue) -> HostCard
    var voice: VoiceController?
    var voiceTint: Color = AGUITheme.link
    /// The host's own items in the «+» menu (after «New conversation»).
    var menuItems: [ChatMenuItem] = []
    /// False when the host gives the input its own way (a system search field in the tab bar): the log only.
    var showsComposer = true

    @State private var draft = ""
    @State private var sources: [JSONValue]?
    @FocusState private var focused: Bool

    /// `voice`: the voice mode (the microphone starts it); without it the microphone calls `onMicrophone` (dictation).
    public init(store: ChatStore, placeholder: LocalizedStringKey = "Ask AI",
                onMicrophone: (() -> Void)? = nil, voice: VoiceController? = nil, voiceTint: Color? = nil,
                menuItems: [ChatMenuItem] = [], showsComposer: Bool = true,
                @ViewBuilder hostCard: @escaping (String, JSONValue) -> HostCard) {
        self.menuItems = menuItems
        self.showsComposer = showsComposer
        self.store = store
        self.placeholder = placeholder
        self.onMicrophone = onMicrophone
        self.hostCard = hostCard
        self.voice = voice
        if let voiceTint { self.voiceTint = voiceTint }
    }

    public var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 0) {
                        ForEach(store.items) { item in
                            row(item).id(item.id)
                        }
                        if store.running, !typing {
                            ThinkingDots().padding(.bottom, 8).id("thinking")
                        }
                        if let error = store.error {
                            errorRow(error).id("error")
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
                .scrollDismissesKeyboard(.interactively)
                .onChange(of: store.items.last) { _, _ in
                    withAnimation(.easeOut(duration: 0.2)) { proxy.scrollTo(store.items.last?.id, anchor: .bottom) }
                }
            }
            if let queued = store.queued {
                Text(queued).font(.footnote).foregroundStyle(AGUITheme.ink2).lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .trailing).padding(.horizontal, 16).padding(.bottom, 4)
            }
            if let voice, voice.active {
                voiceArea(voice)
            } else if !store.suggestions.isEmpty, !store.running {
                chips
            }
            if let problem = voice?.problem, voice?.active == false {
                Text(problem).font(.footnote).foregroundStyle(AGUITheme.ink2).padding(.bottom, 6)
            }
            if showsComposer { composer }
        }
        .foregroundStyle(AGUITheme.ink)
        .sheet(isPresented: Binding(get: { sources != nil }, set: { if !$0 { sources = nil } })) {
            SourcesSheet(items: sources ?? [])
                .presentationDetents([.medium, .large])
                .presentationDragIndicator(.visible)
        }
    }

    private var typing: Bool {
        if case .assistant(_, _, false) = store.items.last { return true }
        return false
    }

    @ViewBuilder
    private func row(_ item: ChatItem) -> some View {
        switch item {
        case .user(_, let text):
            HStack {
                Spacer(minLength: 0)
                Text(text)
                    .font(.system(size: 15))
                    .lineSpacing(4)
                    .padding(.vertical, 10)
                    .padding(.horizontal, 16)
                    .background(AGUITheme.soft, in: .rect(cornerRadius: AGUITheme.radiusLg))
                    .textSelection(.enabled)
                    .containerRelativeFrame(.horizontal, alignment: .trailing) { w, _ in w * 0.85 }
            }
            .padding(.bottom, 20)
            .transition(.opacity.combined(with: .move(edge: .bottom)))
        case .assistant(_, let text, _):
            AnswerText(text: text)
                .padding(.bottom, 20)
                .transition(.opacity)
        case .step(_, let name, let state):
            HStack(spacing: 8) {
                switch state {
                case .running: ProgressView().controlSize(.mini)
                case .done: Image(systemName: "checkmark").font(.system(size: 11, weight: .semibold))
                case .failed: Image(systemName: "exclamationmark.circle").foregroundStyle(AGUITheme.dangerInk)
                }
                Text(Self.stepTitle(name)).lineLimit(1)
            }
            .font(.system(size: 13))
            .foregroundStyle(AGUITheme.ink2)
            .frame(minHeight: 26)
            .padding(.bottom, 8)
        case .card(let card):
            CardView(card: card, store: store)
                .padding(.top, 4)
                .padding(.bottom, 20)
        case .sources(_, let list):
            Button { sources = list } label: {
                HStack(spacing: 6) {
                    Image(systemName: "doc.text")
                    Text(String(localized: "Sources", bundle: .module) + " · \(list.count)")
                }
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(AGUITheme.ink2)
                .padding(.horizontal, 10)
                .frame(minHeight: 30)
                .overlay(Capsule().strokeBorder(AGUITheme.line2, lineWidth: 1))
            }
            .buttonStyle(.plain)
            .padding(.top, -12)
            .padding(.bottom, 20)
        case .host(_, let name, let value):
            hostCard(name, value).padding(.bottom, 20)
        }
    }

    private var chips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(store.suggestions, id: \.self) { s in
                    Button(s) { store.tapSuggestion(s) }
                        .font(.system(size: 13))
                        .foregroundStyle(AGUITheme.ink2)
                        .padding(.horizontal, 14)
                        .frame(minHeight: 44)
                        .background(AGUITheme.bg, in: .capsule)
                        .overlay(Capsule().strokeBorder(AGUITheme.line2, lineWidth: 1))
                        .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 1)
        }
        .padding(.bottom, 8)
        .transition(.opacity)
    }

    /// The voice mode above the input line: the orb and one line under it — «Listening», the agent's step, «Speaking».
    private func voiceArea(_ voice: VoiceController) -> some View {
        VStack(spacing: 10) {
            VoiceOrb(state: voice.state, level: voice.level, tint: voiceTint)
                .offset(y: voice.state == .thinking ? -18 : 0)
                .animation(.spring(response: 0.4, dampingFraction: 0.8), value: voice.state)
            Text(voiceLine(voice))
                .font(.system(size: 15))
                .foregroundStyle(AGUITheme.ink2)
                .lineLimit(1)
                .contentTransition(.opacity)
                .animation(.easeOut(duration: 0.2), value: voiceLine(voice))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .transition(.opacity.combined(with: .scale(scale: 0.9)))
    }

    private func voiceLine(_ voice: VoiceController) -> String {
        switch voice.state {
        case .connecting: return String(localized: "Connecting…", bundle: .module)
        case .listening: return String(localized: "Listening", bundle: .module)
        case .muted: return String(localized: "Microphone off", bundle: .module)
        case .speaking: return String(localized: "Speaking", bundle: .module)
        case .thinking:
            if case .step(_, let name, .running)? = store.items.last(where: { if case .step = $0 { true } else { false } }) {
                return Self.stepTitle(name) + "…"
            }
            return String(localized: "Thinking…", bundle: .module)
        case .off: return ""
        }
    }

    /// `.box`: radius 20, a line-2 border, 8/8/8/16 inside, a faint shadow; «+» left, microphone or send right.
    private var composer: some View {
        HStack(alignment: .bottom, spacing: 8) {
            Menu {
                Button(String(localized: "New conversation", bundle: .module), systemImage: "square.and.pencil") {
                    store.newConversation()
                }
                ForEach(menuItems) { item in
                    Button(item.title, systemImage: item.icon, action: item.action)
                }
            } label: {
                Image(systemName: "plus")
                    .font(.system(size: 17, weight: .medium))
                    .foregroundStyle(AGUITheme.ink2)
                    .frame(width: 36, height: 36)
            }
            .accessibilityLabel(Text("More", bundle: .module))
            TextField(placeholder, text: $draft, axis: .vertical)
                .font(.system(size: 15))
                .lineLimit(1...6)
                .focused($focused)
                .padding(.vertical, 8)
                .submitLabel(.send)
                .onSubmit(send)
            if store.running, draft.trimmingCharacters(in: .whitespaces).isEmpty {
                circle("stop.fill", label: "Stop", filled: true) { store.stop() }
            } else if draft.trimmingCharacters(in: .whitespaces).isEmpty, let voice, !voice.active {
                circle("waveform", label: "Voice", action: { voice.start() })
            } else if draft.trimmingCharacters(in: .whitespaces).isEmpty, voice == nil, let onMicrophone {
                circle("mic", label: "Dictate", action: onMicrophone)
            } else if draft.trimmingCharacters(in: .whitespaces).isEmpty, voice?.active == true {
                EmptyView()
            } else {
                circle("arrow.up", label: "Send", filled: true, action: send)
                    .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(.vertical, 6)
        .padding(.leading, 6)
        .padding(.trailing, 6)
        .background(AGUITheme.bg, in: .rect(cornerRadius: AGUITheme.radiusLg))
        .overlay(RoundedRectangle(cornerRadius: AGUITheme.radiusLg).strokeBorder(focused ? AGUITheme.ink3 : AGUITheme.line2, lineWidth: 1))
        .shadow(color: .black.opacity(0.06), radius: 8, y: 3)
        .overlay(alignment: .trailing) { EmptyView() }
        .modifier(VoiceButtons(voice: voice))
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
    }

    private func circle(_ icon: String, label: LocalizedStringKey, filled: Bool = false,
                        action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(filled ? AGUITheme.onAccent : AGUITheme.ink2)
                .frame(width: 36, height: 36)
                .background(filled ? AGUITheme.accent : .clear, in: .circle)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Text(label, bundle: .module))
    }

    private func errorRow(_ text: String) -> some View {
        HStack(spacing: 10) {
            Text(text).foregroundStyle(AGUITheme.ink2)
            Button(String(localized: "Try Again", bundle: .module)) { store.retry() }
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(AGUITheme.link)
        }
        .font(.system(size: 15))
        .padding(.bottom, 20)
    }

    private func send() {
        let text = draft
        draft = ""
        store.send(text)
    }

    /// The steps line names a tool in words; an unknown one shows nothing technical.
    static func stepTitle(_ name: String) -> String {
        switch name {
        case "view_site": String(localized: "Looking at the site", bundle: .module)
        case "site_stats": String(localized: "Checking the visits", bundle: .module)
        case "guest_requests": String(localized: "Reading the requests", bundle: .module)
        default: String(localized: "Working on it", bundle: .module)
        }
    }
}

extension ChatView where HostCard == EmptyView {
    public init(store: ChatStore, placeholder: LocalizedStringKey = "Ask AI", onMicrophone: (() -> Void)? = nil) {
        self.init(store: store, placeholder: placeholder, onMicrophone: onMicrophone) { _, _ in EmptyView() }
    }
}

/// A host's item in the «+» menu.
public struct ChatMenuItem: Identifiable {
    public let id = UUID()
    public let title: String
    public let icon: String
    public let action: () -> Void
    public init(title: String, icon: String, action: @escaping () -> Void) {
        self.title = title; self.icon = icon; self.action = action
    }
}

/// While the voice mode is on: the microphone (off / on) and «✕» (end the talk) beside the input line, as on the web.
struct VoiceButtons: ViewModifier {
    let voice: VoiceController?
    func body(content: Content) -> some View {
        if let voice, voice.active {
            HStack(spacing: 8) {
                content
                Button { voice.toggleMute() } label: {
                    Image(systemName: voice.state == .muted ? "mic.slash" : "mic")
                        .font(.system(size: 17, weight: .medium))
                        .foregroundStyle(AGUITheme.ink)
                        .frame(width: 48, height: 48)
                        .background(AGUITheme.soft, in: .circle)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(Text(voice.state == .muted ? "Microphone on" : "Microphone off", bundle: .module))
                Button { Task { await voice.stop() } } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 17, weight: .medium))
                        .foregroundStyle(AGUITheme.ink)
                        .frame(width: 48, height: 48)
                        .background(AGUITheme.bg, in: .circle)
                        .overlay(Circle().strokeBorder(AGUITheme.line2, lineWidth: 1))
                        .shadow(color: .black.opacity(0.1), radius: 6, y: 2)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(Text("End the voice talk", bundle: .module))
            }
        } else {
            content
        }
    }
}

/// An answer: Markdown text (15 pt, line height ≈1.58) and Markdown tables drawn as a table (`.tbl`: 13 pt semibold
/// head in ink-2, 15 pt cells, a line between rows; a wide one scrolls sideways).
struct AnswerText: View {
    let text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(Array(Self.blocks(text).enumerated()), id: \.offset) { _, block in
                switch block {
                case .text(let t):
                    Text(LocalizedStringKey(t))
                        .font(.system(size: 15))
                        .lineSpacing(8)
                        .tint(AGUITheme.link)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                case .table(let head, let rows):
                    ScrollView(.horizontal, showsIndicators: false) {
                        Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 0) {
                            GridRow {
                                ForEach(head.indices, id: \.self) { i in
                                    Text(head[i]).font(.system(size: 13, weight: .semibold)).foregroundStyle(AGUITheme.ink2)
                                        .padding(.vertical, 8)
                                }
                            }
                            ForEach(rows.indices, id: \.self) { r in
                                Divider().overlay(AGUITheme.line)
                                GridRow {
                                    ForEach(rows[r].indices, id: \.self) { i in
                                        Text(LocalizedStringKey(rows[r][i])).font(.system(size: 15)).padding(.vertical, 8)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    enum Block { case text(String), table([String], [[String]]) }

    static func cells(_ line: String) -> [String] {
        var l = line.trimmingCharacters(in: .whitespaces)
        if l.hasPrefix("|") { l.removeFirst() }
        if l.hasSuffix("|") { l.removeLast() }
        return l.split(separator: "|", omittingEmptySubsequences: false).map { $0.trimmingCharacters(in: .whitespaces) }
    }

    static func blocks(_ text: String) -> [Block] {
        let lines = text.components(separatedBy: "\n")
        var out: [Block] = []
        var buffer: [String] = []
        var i = 0
        func flush() {
            let t = buffer.joined(separator: "\n").trimmingCharacters(in: .newlines)
            if !t.isEmpty { out.append(.text(t)) }
            buffer = []
        }
        while i < lines.count {
            let l = lines[i]
            if l.contains("|"), i + 1 < lines.count,
               lines[i + 1].trimmingCharacters(in: .whitespaces).range(of: #"^\|?\s*:?-{2,}"#, options: .regularExpression) != nil {
                flush()
                let head = cells(l)
                var rows: [[String]] = []
                i += 2
                while i < lines.count, lines[i].contains("|") {
                    var r = cells(lines[i])
                    if r.count < head.count { r += Array(repeating: "", count: head.count - r.count) }
                    rows.append(Array(r.prefix(head.count)))
                    i += 1
                }
                out.append(.table(head, rows))
                continue
            }
            buffer.append(l)
            i += 1
        }
        flush()
        return out
    }
}

/// `ask` (options; or 2–3 fields; or one typed answer), `confirm`, `set_fields`; «not accepted» with its cross.
struct CardView: View {
    let card: ChatCard
    let store: ChatStore
    @State private var values: [String: String] = [:]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let title = card.body["title"]?.string, card.body["question"] != nil {
                Text(title).font(.system(size: 13, weight: .semibold)).foregroundStyle(AGUITheme.ink2)
            }
            if let q = card.question {
                Text(q).font(.system(size: 17, weight: .semibold)).tracking(-0.3).lineSpacing(2)
            }
            if case .refused(let reason) = card.status {
                HStack(alignment: .top, spacing: 6) {
                    Image(systemName: "xmark.circle.fill").foregroundStyle(AGUITheme.danger)
                    Text(reason.isEmpty ? String(localized: "Not accepted", bundle: .module) : reason)
                        .foregroundStyle(AGUITheme.dangerInk)
                }
                .font(.system(size: 13, weight: .medium))
            }
            switch card.type {
            case "ask" where !card.options.isEmpty:
                VStack(spacing: 6) {
                    ForEach(card.options, id: \.id) { option in
                        let on = card.chosen == option.id
                        Button { store.choose(card, option: option.id) } label: {
                            Text(option.label)
                                .font(.system(size: 15, weight: on ? .semibold : .regular))
                                .frame(maxWidth: .infinity, minHeight: 24, alignment: .leading)
                                .padding(.vertical, 10)
                                .padding(.horizontal, 12)
                                .background(AGUITheme.bg, in: .rect(cornerRadius: AGUITheme.radiusSm))
                                .overlay(RoundedRectangle(cornerRadius: AGUITheme.radiusSm)
                                    .strokeBorder(on ? AGUITheme.accent : AGUITheme.line2, lineWidth: on ? 2 : 1))
                                .overlay(alignment: .trailing) {
                                    if on { Image(systemName: "checkmark").font(.system(size: 13, weight: .bold)).padding(.trailing, 12) }
                                }
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(AGUITheme.ink)
                    }
                }
            case "ask":
                fields
            case "set_fields" where store.applyFields != nil:
                FieldsCard(card: card, store: store)
            case "confirm":
                HStack(spacing: 8) {
                    Button(card.body["action"]?.string ?? String(localized: "Confirm", bundle: .module)) {
                        store.confirm(card, true)
                    }
                    .buttonStyle(AGUIButton(primary: true))
                    Button(String(localized: "Cancel", bundle: .module)) { store.confirm(card, false) }
                        .buttonStyle(AGUIButton(primary: false))
                }
            default:
                // a card this client cannot draw yet: say so and let the person decline it
                Text(String(localized: "This step opens on the web for now.", bundle: .module))
                    .font(.system(size: 15)).foregroundStyle(AGUITheme.ink2)
                Button(String(localized: "Not now", bundle: .module)) { store.answer(card, with: ["accepted": false]) }
                    .buttonStyle(AGUIButton(primary: false))
            }
        }
        .disabled(!open || store.running)
        .opacity(open || card.chosen != nil ? 1 : 0.6)
        .aguiCard()
    }

    /// 2–3 short fields (`fields: [{name, label, required}]`) or one typed answer; «Send».
    @ViewBuilder private var fields: some View {
        let list = card.body["fields"]?.array ?? []
        let rows: [(name: String, label: String, required: Bool)] = list.isEmpty
            ? [("text", card.body["placeholder"]?.string ?? "", true)]
            : list.compactMap { f in
                guard let n = f["name"]?.string else { return nil }
                return (n, f["label"]?.string ?? n, f["required"]?.bool ?? false)
            }
        VStack(spacing: 8) {
            ForEach(rows, id: \.name) { r in
                TextField(r.label, text: Binding(get: { values[r.name] ?? "" }, set: { values[r.name] = $0 }))
                    .font(.system(size: 15))
                    .padding(.horizontal, 12)
                    .frame(minHeight: 44)
                    .background(AGUITheme.bg, in: .rect(cornerRadius: AGUITheme.radiusSm))
                    .overlay(RoundedRectangle(cornerRadius: AGUITheme.radiusSm).strokeBorder(AGUITheme.line2, lineWidth: 1))
            }
            HStack {
                Button(String(localized: "Send", bundle: .module)) { store.answerFields(card, values) }
                    .buttonStyle(AGUIButton(primary: true))
                    .disabled(rows.contains { $0.required && (values[$0.name] ?? "").trimmingCharacters(in: .whitespaces).isEmpty })
                Spacer()
            }
        }
    }

    private var open: Bool {
        guard store.isAnswerable(card) else { return false }
        switch card.status {
        case .open, .refused: return true
        default: return false
        }
    }
}

/// Field changes: each row «label: before → after» with a tick (consent rows start unticked), «Accept» applies the
/// ticked ones through the host's form, «Cancel» declines.
struct FieldsCard: View {
    let card: ChatCard
    let store: ChatStore
    @State private var ticked: Set<String> = []

    private var rows: [JSONValue] { card.body["changes"]?.array ?? [] }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(Array(rows.enumerated()), id: \.offset) { i, row in
                let name = row["name"]?.string ?? ""
                if i > 0 { Divider().overlay(AGUITheme.line) }
                Button {
                    if ticked.contains(name) { ticked.remove(name) } else { ticked.insert(name) }
                } label: {
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: ticked.contains(name) ? "checkmark.circle.fill" : "circle")
                            .font(.system(size: 18))
                            .foregroundStyle(ticked.contains(name) ? AGUITheme.accent : AGUITheme.ink3)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(row["label"]?.string ?? name).font(.system(size: 13, weight: .semibold)).foregroundStyle(AGUITheme.ink2)
                            HStack(alignment: .firstTextBaseline, spacing: 6) {
                                if let before = row["previous"]?.string ?? row["previous_display"]?.string, !before.isEmpty {
                                    Text(before).strikethrough().foregroundStyle(AGUITheme.ink3)
                                    Image(systemName: "arrow.right").font(.system(size: 11)).foregroundStyle(AGUITheme.ink3)
                                }
                                Text(row["display"]?.string ?? row["value"]?.string ?? "").fontWeight(.medium)
                            }
                            .font(.system(size: 15))
                        }
                        Spacer(minLength: 0)
                    }
                    .padding(.vertical, 10)
                    .contentShape(.rect)
                }
                .buttonStyle(.plain)
            }
            HStack(spacing: 8) {
                Button(String(localized: "Accept", bundle: .module)) { store.acceptFields(card, names: Array(ticked)) }
                    .buttonStyle(AGUIButton(primary: true))
                    .disabled(ticked.isEmpty)
                Button(String(localized: "Cancel", bundle: .module)) { store.confirm(card, false) }
                    .buttonStyle(AGUIButton(primary: false))
            }
            .padding(.top, 8)
        }
        .onAppear {
            ticked = Set(rows.compactMap { r in r["consent"]?.bool == true ? nil : r["name"]?.string })
        }
    }
}

/// Sources of an answer, variant A — a sheet: each with its title, section and the passage it came from.
struct SourcesSheet: View {
    let items: [JSONValue]

    var body: some View {
        NavigationStack {
            List(Array(items.enumerated()), id: \.offset) { _, s in
                VStack(alignment: .leading, spacing: 4) {
                    Text(s["title"]?.string ?? "").font(.system(size: 15, weight: .semibold))
                    if let section = s["section"]?.string, !section.isEmpty {
                        Text(section).font(.system(size: 13)).foregroundStyle(AGUITheme.ink2)
                    }
                    if let excerpt = s["excerpt"]?.string ?? s["quote"]?.string ?? s["text"]?.string, !excerpt.isEmpty {
                        Text("«\(excerpt)»").font(.system(size: 15)).foregroundStyle(AGUITheme.ink).padding(.top, 4)
                    }
                }
                .padding(.vertical, 4)
            }
            .navigationTitle(Text("Sources", bundle: .module))
            .navigationBarTitleDisplayModeInline()
        }
    }
}

extension View {
    @ViewBuilder func navigationBarTitleDisplayModeInline() -> some View {
        #if os(iOS)
        navigationBarTitleDisplayMode(.inline)
        #else
        self
        #endif
    }
}

/// Three dots while the answer has not started.
struct ThinkingDots: View {
    @State private var on = false
    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3) { i in
                Circle().frame(width: 6, height: 6)
                    .opacity(on ? 1 : 0.3)
                    .animation(.easeInOut(duration: 0.6).repeatForever().delay(Double(i) * 0.2), value: on)
            }
        }
        .foregroundStyle(AGUITheme.ink3)
        .frame(minHeight: 26)
        .onAppear { on = true }
        .accessibilityLabel(Text("Thinking", bundle: .module))
    }
}
