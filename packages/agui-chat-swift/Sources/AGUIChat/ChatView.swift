import SwiftUI

/// The chat, laid out like the Claude app on iOS: the assistant's answer as plain text on the page (no bubble), the
/// person's words in a bubble on the right, a quiet steps line while tools run, quick replies as chips above the input,
/// one input line with the microphone and the send button. The host draws its own cards (`hostCard`) and records the
/// voice (`onMicrophone`): voice goes through the host's own transcription.
public struct ChatView<HostCard: View>: View {
    @Bindable var store: ChatStore
    var placeholder: LocalizedStringKey
    var onMicrophone: (() -> Void)?
    var hostCard: (String, JSONValue) -> HostCard

    @State private var draft = ""
    @FocusState private var focused: Bool

    public init(store: ChatStore, placeholder: LocalizedStringKey = "Ask AI",
                onMicrophone: (() -> Void)? = nil,
                @ViewBuilder hostCard: @escaping (String, JSONValue) -> HostCard) {
        self.store = store
        self.placeholder = placeholder
        self.onMicrophone = onMicrophone
        self.hostCard = hostCard
    }

    public var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 14) {
                        ForEach(store.items) { item in
                            row(item).id(item.id)
                        }
                        if store.running, !typing {
                            ThinkingDots().id("thinking")
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
                Text(queued).font(.footnote).foregroundStyle(.secondary).lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .trailing).padding(.horizontal, 16).padding(.bottom, 4)
            }
            if !store.suggestions.isEmpty, !store.running {
                chips
            }
            composer
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
                Spacer(minLength: 48)
                Text(text)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(.fill.tertiary, in: .rect(cornerRadius: 20))
                    .textSelection(.enabled)
            }
            .transition(.opacity.combined(with: .move(edge: .bottom)))
        case .assistant(_, let text, _):
            Text(LocalizedStringKey(text))
                .frame(maxWidth: .infinity, alignment: .leading)
                .textSelection(.enabled)
                .transition(.opacity)
        case .step(_, let name, let state):
            HStack(spacing: 6) {
                switch state {
                case .running: ProgressView().controlSize(.mini)
                case .done: Image(systemName: "checkmark").foregroundStyle(.secondary)
                case .failed: Image(systemName: "exclamationmark.circle").foregroundStyle(.orange)
                }
                Text(Self.stepTitle(name))
            }
            .font(.footnote)
            .foregroundStyle(.secondary)
        case .card(let card):
            CardView(card: card, store: store)
        case .host(_, let name, let value):
            hostCard(name, value)
        }
    }

    private var chips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(store.suggestions, id: \.self) { s in
                    Button(s) { store.tapSuggestion(s) }
                        .font(.subheadline)
                        .padding(.horizontal, 14)
                        .frame(minHeight: 36)
                        .background(.fill.tertiary, in: .capsule)
                        .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 16)
        }
        .padding(.bottom, 8)
        .transition(.opacity)
    }

    private var composer: some View {
        HStack(alignment: .bottom, spacing: 8) {
            TextField(placeholder, text: $draft, axis: .vertical)
                .lineLimit(1...6)
                .focused($focused)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .submitLabel(.send)
                .onSubmit(send)
            if store.running, draft.trimmingCharacters(in: .whitespaces).isEmpty {
                circle("stop.fill", label: "Stop") { store.stop() }
            } else if draft.trimmingCharacters(in: .whitespaces).isEmpty, let onMicrophone {
                circle("mic.fill", label: "Dictate", action: onMicrophone)
            } else {
                circle("arrow.up", label: "Send", filled: true, action: send)
                    .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(4)
        .background(.fill.tertiary, in: .rect(cornerRadius: 24))
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
    }

    private func circle(_ icon: String, label: LocalizedStringKey, filled: Bool = false,
                        action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.body.weight(.semibold))
                .foregroundStyle(filled ? Color.white : Color.primary)
                .frame(width: 36, height: 36)
                .background(filled ? AnyShapeStyle(Color.accentColor) : AnyShapeStyle(.fill.secondary), in: .circle)
        }
        .buttonStyle(.plain)
        .padding(2)
        .accessibilityLabel(Text(label, bundle: .module))
    }

    private func errorRow(_ text: String) -> some View {
        HStack(spacing: 10) {
            Text(text).foregroundStyle(.secondary)
            Button(String(localized: "Try Again", bundle: .module)) { store.retry() }
                .font(.subheadline.weight(.semibold))
        }
        .font(.subheadline)
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

/// `ask` (options as buttons) and `confirm` (its action named on the button). The card looks answered only once the
/// run that carried the answer has finished.
struct CardView: View {
    let card: ChatCard
    let store: ChatStore

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let q = card.question { Text(q).font(.body.weight(.semibold)) }
            if case .refused(let reason) = card.status, !reason.isEmpty {
                Text(reason).font(.footnote).foregroundStyle(.orange)
            }
            switch card.type {
            case "ask" where !card.options.isEmpty:
                ForEach(card.options, id: \.id) { option in
                    Button { store.choose(card, option: option.id) } label: {
                        Text(option.label).frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .buttonStyle(.bordered)
                }
            case "set_fields" where store.applyFields != nil:
                FieldsCard(card: card, store: store)
            case "confirm":
                HStack {
                    Button(card.body["action"]?.string ?? String(localized: "Confirm", bundle: .module)) {
                        store.confirm(card, true)
                    }
                    .buttonStyle(.borderedProminent)
                    Button(String(localized: "Cancel", bundle: .module)) { store.confirm(card, false) }
                        .buttonStyle(.bordered)
                }
            default:
                // a card this client cannot draw yet (set_fields comes whatever the capabilities say): say so and let
                // the person decline it, so the chat never gets stuck behind it (review, smaller notes)
                Text(String(localized: "This step opens on the web for now.", bundle: .module))
                    .font(.subheadline).foregroundStyle(.secondary)
                Button(String(localized: "Not now", bundle: .module)) { store.answer(card, with: ["accepted": false]) }
                    .buttonStyle(.bordered)
            }
        }
        .disabled(!open || store.running)
        .opacity(open ? 1 : 0.55)
        .padding(14)
        .background(.fill.quaternary, in: .rect(cornerRadius: 18))
    }

    private var open: Bool {
        switch card.status {
        case .open, .refused: true
        default: false
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
        VStack(alignment: .leading, spacing: 8) {
            ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                let name = row["name"]?.string ?? ""
                Button {
                    if ticked.contains(name) { ticked.remove(name) } else { ticked.insert(name) }
                } label: {
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: ticked.contains(name) ? "checkmark.circle.fill" : "circle")
                            .foregroundStyle(ticked.contains(name) ? Color.accentColor : .secondary)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(row["label"]?.string ?? name).font(.subheadline.weight(.semibold))
                            HStack(spacing: 4) {
                                if let before = row["previous"]?.string ?? row["previous_display"]?.string, !before.isEmpty {
                                    Text(before).strikethrough().foregroundStyle(.secondary)
                                    Image(systemName: "arrow.right").font(.caption).foregroundStyle(.secondary)
                                }
                                Text(row["display"]?.string ?? row["value"]?.string ?? "")
                            }
                            .font(.subheadline)
                        }
                        Spacer(minLength: 0)
                    }
                    .contentShape(.rect)
                }
                .buttonStyle(.plain)
            }
            HStack {
                Button(String(localized: "Accept", bundle: .module)) { store.acceptFields(card, names: Array(ticked)) }
                    .buttonStyle(.borderedProminent)
                    .disabled(ticked.isEmpty)
                Button(String(localized: "Cancel", bundle: .module)) { store.confirm(card, false) }
                    .buttonStyle(.bordered)
            }
            .padding(.top, 4)
        }
        .onAppear {
            ticked = Set(rows.compactMap { r in r["consent"]?.bool == true ? nil : r["name"]?.string })
        }
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
        .foregroundStyle(.secondary)
        .onAppear { on = true }
        .accessibilityLabel(Text("Thinking", bundle: .module))
    }
}
