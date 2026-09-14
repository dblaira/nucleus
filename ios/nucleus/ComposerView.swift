import SwiftUI

/// The CowboyAI app's question form (Cowboyai/authority-hub/ios/CowboyAI/CowboyQuestionComposerView.swift), cut
/// to what nucleus takes: the question. The draft is kept on every keystroke (AskModel).
struct ComposerView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var model: AskModel
    let onAsk: () -> Void

    private var isEmpty: Bool { model.question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("Your writing saves automatically on this iPhone.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("question-draft-status")
                }
                .listRowBackground(Color.white)

                Section {
                    TextField("Question", text: $model.question, axis: .vertical)
                        .lineLimit(3...10)
                        .accessibilityIdentifier("new-question-text")
                }
                .listRowBackground(CowboyTheme.cream)

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
            .navigationTitle(isEmpty ? "Question" : model.question)
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
}
