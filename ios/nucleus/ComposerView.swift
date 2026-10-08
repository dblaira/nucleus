import SwiftUI

/// The CowboyAI app's question form (Cowboyai/authority-hub/ios/CowboyAI/CowboyQuestionComposerView.swift), cut
/// to what nucleus takes: the question. The draft is kept on every keystroke (AskModel).
/// 2026-10-07: SAVY's Theme menu and Decide boxes, copied from SAVY-iOS ReminderFormView (postThemeSection,
/// postDecideSection). Adam: "All the themes that I have on the SAVY app, I want added on cowboy AI."
struct ComposerView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var model: AskModel
    let onAsk: () -> Void
    @State private var examplesExpanded = false

    private var isEmpty: Bool { !model.canAsk }

    var body: some View {
        NavigationStack {
            Form {
                themeSection

                if model.theme != nil {
                    decideSection
                }

                Section {
                    TextField("Question", text: $model.question, axis: .vertical)
                        .lineLimit(3...10)
                        .accessibilityIdentifier("new-question-text")
                }
                .listRowBackground(CowboyTheme.cream)

                examplesSection

                Section {
                    Button(action: onAsk) {
                        Label("Ask", systemImage: "paperplane")
                    }
                    .disabled(isEmpty || model.working)
                    .accessibilityIdentifier("ask-nucleus")

                    if model.working {
                        ProgressView("reading your words…")
                            .accessibilityIdentifier("question-answer-progress")
                    }
                }
                .listRowBackground(CowboyTheme.cream)
            }
            .scrollContentBackground(.hidden)
            .background(Color.white.ignoresSafeArea())
            .tint(CowboyTheme.red)
            .navigationTitle(model.question.isEmpty ? (model.theme?.name ?? "Question") : model.question)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle")
                            .font(.system(size: 22))
                    }
                    .tint(.black)
                    .accessibilityLabel("Close")
                    .accessibilityIdentifier("close-question-composer")
                }
            }
            .toolbarBackground(Color.white, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.light, for: .navigationBar)
        }
        .preferredColorScheme(.light)
    }

    private var examplesSection: some View {
        Section {
            DisclosureGroup(isExpanded: $examplesExpanded) {
                ForEach(QuestionExampleCatalog.examples) { example in
                    Button {
                        model.selectExample(example.id)
                        examplesExpanded = false
                    } label: {
                        HStack(alignment: .firstTextBaseline, spacing: 10) {
                            Image(systemName: example.theme?.questions.first?.symbol ?? "lightbulb")
                                .symbolVariant(.none)
                                .foregroundStyle(CowboyTheme.red)
                                .frame(width: 24)
                                .accessibilityHidden(true)
                            VStack(alignment: .leading, spacing: 6) {
                                Text(example.title)
                                Text(example.question)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            .font(.body.weight(.regular))
                            .foregroundStyle(.black)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            Image(systemName: "plus")
                                .foregroundStyle(CowboyTheme.red)
                                .accessibilityHidden(true)
                        }
                        .font(.body.weight(.regular))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 6)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .disabled(model.working)
                    .accessibilityIdentifier("question-example-\(example.id)")
                    .accessibilityLabel("\(model.question.isEmpty ? "Use this question" : "Add below my question"): \(example.question)")
                    .accessibilityHint(model.question.isEmpty
                        ? "Fills the Question field. You can edit it before tapping Ask."
                        : "Adds below your writing and keeps your Theme and Decide answers. You can edit it before tapping Ask.")
                }
            } label: {
                Label("Example questions", systemImage: "lightbulb")
                    .symbolVariant(.none)
                    .font(.body.weight(.regular))
                    .foregroundStyle(.black)
            }
            .accessibilityIdentifier("question-examples")
        }
        .listRowBackground(CowboyTheme.cream)
    }

    // MARK: - Theme + Decide, as SAVY draws them

    private var themeSection: some View {
        Section {
            Menu {
                ForEach(PostThemeCatalog.themes) { theme in
                    Button {
                        model.selectTheme(theme.id)
                    } label: {
                        Label(theme.name, systemImage: theme.questions.first?.symbol ?? "lightbulb")
                    }
                }
            } label: {
                HStack {
                    Label("Theme", systemImage: "list.bullet")
                        .foregroundStyle(.black)
                    Spacer()
                    if let theme = model.theme {
                        Label(theme.name, systemImage: theme.questions.first?.symbol ?? "lightbulb")
                            .lineLimit(1)
                    } else {
                        Text("Theme")
                    }
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.body.weight(.regular))
                }
                .foregroundStyle(CowboyTheme.red)
            }
            .accessibilityIdentifier("PostTheme")
        } header: { sectionHeader("Theme") }
        .listRowBackground(CowboyTheme.cream)
    }

    private var decideSection: some View {
        Section {
            ForEach(model.themeFields.indices, id: \.self) { index in
                let question = model.theme?.questions.indices.contains(index) == true ? model.theme?.questions[index] : nil
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    Image(systemName: question?.symbol ?? "text.bubble")
                        .font(.body.weight(.regular))
                        .foregroundStyle(CowboyTheme.red)
                        .frame(width: 24)
                    TextField("", text: Binding(
                        get: { model.themeFields.indices.contains(index) ? model.themeFields[index] : "" },
                        set: { model.setThemeField($0, at: index) }
                    ), axis: .vertical)
                        .lineLimit(3...12)
                        .foregroundStyle(.black)
                        .accessibilityIdentifier("DecideAnswer\(index)")
                }
                .id("\(model.themeID ?? "")-\(index)")
            }
        } header: { sectionHeader("Decide") }
        .listRowBackground(CowboyTheme.cream)
    }

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.body.weight(.regular))
            .foregroundStyle(CowboyTheme.navy.opacity(0.72))
    }
}
