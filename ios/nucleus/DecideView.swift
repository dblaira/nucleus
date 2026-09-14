import SwiftUI

/// The CowboyAI app's Decide home (Cowboyai/authority-hub/ios/CowboyAI/SavedResultsView.swift): the live answer,
/// then PAST RESULTS as SAVY's horizontal carousel. Tapping a past result opens it as the live answer.
struct DecideView: View {
    var model: AskModel
    @State private var selectedRecord: AnswerParts.Record?
    @State private var selectedWords: AnswerParts.Words?

    var body: some View {
        ScrollViewReader { page in
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    Color.clear.frame(height: 0).id("top")

                    if let problem = model.problem {
                        Text(problem)
                            .foregroundStyle(CowboyTheme.red)
                            .padding(.horizontal, 18)
                            .padding(.top, 24)
                            .accessibilityIdentifier("live-answer-error")
                    }

                    if model.current != nil || model.working {
                        LiveAnswerSection(
                            model: model,
                            selectRecord: { selectedRecord = $0 },
                            selectWords: { selectedWords = $0 }
                        )
                    }

                    HStack(alignment: .firstTextBaseline) {
                        Text("PAST RESULTS")
                            .font(.system(size: 20, weight: .black))
                            .foregroundStyle(.black)
                        Spacer()
                        if !model.recent.isEmpty {
                            Text("\(model.recent.count)")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundStyle(.secondary)
                                .accessibilityLabel("\(model.recent.count) past results")
                        }
                    }
                    .frame(minHeight: 80)
                    .padding(.horizontal, 18)

                    if model.recent.isEmpty {
                        Text("Your past results will appear here.")
                            .font(CowboyTheme.carouselSerif(22))
                            .foregroundStyle(.secondary)
                            .padding(.horizontal, 18)
                            .padding(.bottom, 24)
                    } else {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 16) {
                                ForEach(model.recent) { item in
                                    Button {
                                        Task {
                                            await model.open(item.id)
                                            withAnimation { page.scrollTo("top", anchor: .top) }
                                        }
                                    } label: {
                                        SavedResultCard(item: item)
                                    }
                                    .buttonStyle(.plain)
                                    .accessibilityIdentifier("saved-result-\(item.id)")
                                }
                            }
                            .padding(.horizontal, 2)
                            .padding(.bottom, 24)
                        }
                        .accessibilityIdentifier("pastResultsCarousel")
                    }
                }
                .padding(.bottom, 40)
            }
            .onChange(of: model.current?.question.id) { _, _ in
                withAnimation { page.scrollTo("top", anchor: .top) }
            }
        }
        .refreshable { await model.loadRecent() }
        .background(Color.white.ignoresSafeArea())
        .accessibilityIdentifier("saved-results-home")
        .environment(\.colorScheme, .light)
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

private struct SavedResultCard: View {
    let item: RecentItem
    @ScaledMetric(relativeTo: .body) private var cardHeight: CGFloat = 182

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(item.dateLabel)
                    .font(.system(size: 11, weight: .heavy))
                    .tracking(1.1)
                Spacer(minLength: 8)
                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .semibold))
            }
            .foregroundStyle(CowboyTheme.red)

            Text(item.question)
                .font(CowboyTheme.carouselSerif(24))
                .lineLimit(3)
                .minimumScaleFactor(0.85)
                .foregroundStyle(.black)
                .frame(maxWidth: .infinity, alignment: .leading)

            if item.status != "answered" {
                Text(item.status)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(CowboyTheme.red)
            }

            Text((item.answer ?? item.status).replacingOccurrences(of: "_", with: " "))
                .font(.system(size: 14))
                .foregroundStyle(.black.opacity(0.66))
                .lineLimit(item.status == "answered" ? 2 : 1)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .multilineTextAlignment(.leading)
        .padding(.horizontal, 17)
        .padding(.vertical, 16)
        .frame(width: 282, height: cardHeight, alignment: .topLeading)
        .background(CowboyTheme.cream, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(.black.opacity(0.08), lineWidth: 1)
        }
        .contentShape(RoundedRectangle(cornerRadius: 12))
        .accessibilityElement(children: .combine)
        .accessibilityHint("Opens the complete saved result")
    }
}

private extension RecentItem {
    var dateLabel: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d · h:mm a"
        return formatter.string(from: Date(timeIntervalSince1970: finished)).uppercased()
    }
}
