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
        ScrollViewReader { proxy in
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
                Color.clear.frame(height: 1).id("answer-bottom")
            }
            .padding(.bottom, 40)
        }
        .task(id: model.current?.question.id) {
            // `-bottom` at launch scrolls to the end of the answer; used by the Mac to see what is under the fold
            if CommandLine.arguments.contains("-bottom"), model.current != nil {
                try? await Task.sleep(nanoseconds: 1_200_000_000)
                proxy.scrollTo("answer-bottom", anchor: .bottom)
            }
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
}
