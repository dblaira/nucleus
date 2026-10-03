import SwiftUI

/// One question and its answer, as its own page with SAVY's back button. id nil: the question being asked now.
struct AnswerPage: View {
    var model: AskModel
    let id: String?
    @State private var selectedRecord: AnswerParts.Record?
    @State private var selectedWords: AnswerParts.Words?

    private var loaded: Bool {
        guard let id else { return true }
        return model.current?.question.id == id
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                SavyBackButton()
                    .padding(.horizontal, SavyLayout.horizontalPadding)
                    .padding(.top, 8)

                if let problem = model.problem {
                    Text(problem)
                        .foregroundStyle(CowboyTheme.red)
                        .padding(.horizontal, 18)
                        .padding(.top, 24)
                        .accessibilityIdentifier("live-answer-error")
                }

                if loaded {
                    LiveAnswerSection(
                        model: model,
                        selectRecord: { selectedRecord = $0 },
                        selectWords: { selectedWords = $0 }
                    )
                } else {
                    ProgressView("reading your words…")
                        .tint(CowboyTheme.red)
                        .padding(SavyLayout.horizontalPadding)
                }
            }
            .padding(.bottom, 40)
        }
        .background(Color.white.ignoresSafeArea())
        .environment(\.colorScheme, .light)
        .navigationBarBackButtonHidden(true)
        .toolbar(.hidden, for: .navigationBar)
        .accessibilityIdentifier("answerPage")
        .task {
            if let id, model.current?.question.id != id {
                await model.open(id)
            }
        }
        .sheet(item: $selectedRecord) { record in
            RecordDetail(record: record, model: model)
                .preferredColorScheme(.light)
        }
        .sheet(item: $selectedWords) { words in
            WordsDetail(words: words)
                .preferredColorScheme(.light)
        }
    }
}
