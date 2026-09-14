import SwiftUI

/// The answer arriving on the Decide home, built from the CowboyAI app's own pieces
/// (Cowboyai/authority-hub/ios/CowboyAI/LiveAnswerView.swift): the cream question panel and red kicker, the
/// cream answer panel, the home's section titles, the results carousel card. The meaning comes right under the
/// question. Adam, 2026-09-14: "I don't wanna have to scroll past 60 fucking rows of my words to get down to
/// the goddamn meaning."
struct LiveAnswerSection: View {
    var model: AskModel
    let selectRecord: (AnswerParts.Record) -> Void
    let selectWords: (AnswerParts.Words) -> Void

    private var current: AskResponse? { model.current }
    private var parts: AnswerParts { AnswerParts(text: current?.answer?.text, rows: current?.rows ?? []) }
    private var answered: Bool { current?.answer?.status == "answered" }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 12) {
                kicker("YOUR QUESTION")
                Text(current?.question.question ?? model.question)
                    .font(CowboyTheme.carouselSerif(23))
                    .foregroundStyle(.black)
                    .fixedSize(horizontal: false, vertical: true)
                    .textSelection(.enabled)
                    .accessibilityIdentifier("live-answer-question")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(20)
            .background(CowboyTheme.cream, in: RoundedRectangle(cornerRadius: 18))
            .padding(.horizontal, 18)
            .padding(.top, 24)

            answer
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(20)
                .background(CowboyTheme.cream, in: RoundedRectangle(cornerRadius: 18))
                .padding(.horizontal, 18)
                .padding(.top, 24)
                .padding(.bottom, 8)

            if answered {
                wordsCarousel(titled: "HE SAID THE WORD ITSELF", parts.words)
                recordsCarousel(titled: "HIS ROUTES SENT IT HERE", parts.records)
                possibility
            }
        }
    }

    @ViewBuilder
    private var answer: some View {
        if let a = current?.answer {
            VStack(alignment: .leading, spacing: 14) {
                if a.status == "answered" {
                    kicker("YOUR ANSWER")
                    if let n = current?.asked_before, n > 0 {
                        Text("asked before · \(n) \(n == 1 ? "time" : "times")")
                            .font(.system(size: 11, weight: .bold))
                            .tracking(1)
                            .foregroundStyle(.secondary)
                    }
                    Text(parts.firstLine)
                        .font(CowboyTheme.readingSerif(22, relativeTo: .body))
                        .foregroundStyle(.black)
                        .lineSpacing(5)
                        .fixedSize(horizontal: false, vertical: true)
                        .textSelection(.enabled)
                        .accessibilityIdentifier("live-answer-text")
                    explanation
                    ForEach(Array(parts.other.enumerated()), id: \.offset) { _, block in
                        Text(block)
                            .font(CowboyTheme.readingSerif(22, relativeTo: .body))
                            .foregroundStyle(.black)
                            .lineSpacing(5)
                            .fixedSize(horizontal: false, vertical: true)
                            .textSelection(.enabled)
                    }
                } else {
                    kicker(a.status.replacingOccurrences(of: "_", with: " ").uppercased())
                    Text(a.text ?? a.gate_reason ?? "")
                        .font(CowboyTheme.readingSerif(22, relativeTo: .body))
                        .foregroundStyle(CowboyTheme.red)
                        .lineSpacing(5)
                        .fixedSize(horizontal: false, vertical: true)
                        .textSelection(.enabled)
                        .accessibilityIdentifier("live-answer-error")
                }
            }
        } else {
            ProgressView("reading your words…")
                .tint(CowboyTheme.red)
                .accessibilityIdentifier("live-answer-progress")
        }
    }

    @ViewBuilder
    private var explanation: some View {
        if let ex = current?.explanation {
            if ex.status == "pending" {
                ProgressView("writing what this says about your question…")
                    .tint(CowboyTheme.red)
            } else if ex.status == "shown", let text = ex.text {
                Text(text)
                    .font(CowboyTheme.readingSerif(22, relativeTo: .body))
                    .foregroundStyle(.black)
                    .lineSpacing(5)
                    .fixedSize(horizontal: false, vertical: true)
                    .textSelection(.enabled)
                    .accessibilityIdentifier("live-explanation-text")
                Thumbs(state: model.explanationThumb ?? ex.thumb) { up in
                    Task { await model.thumbExplanation(up: up) }
                }
            }
        }
    }

    /// The home's own section title over the results carousel card.
    @ViewBuilder
    private func wordsCarousel(titled title: String, _ items: [AnswerParts.Words]) -> some View {
        if !items.isEmpty {
            sectionTitle(title)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 16) {
                    ForEach(items) { words in
                        Button {
                            selectWords(words)
                        } label: {
                            MeaningCard(
                                label: words.word.uppercased(),
                                text: words.meanings.first ?? words.why,
                                secondary: words.meanings.dropFirst().joined(separator: "  ")
                            )
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("live-meaning-\(words.word)")
                    }
                }
                .padding(.horizontal, 2)
            }
            .accessibilityIdentifier("liveMeaningsCarousel")
        }
    }

    @ViewBuilder
    private func recordsCarousel(titled title: String, _ items: [AnswerParts.Record]) -> some View {
        if !items.isEmpty {
            sectionTitle(title)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 16) {
                    ForEach(items) { record in
                        Button {
                            selectRecord(record)
                        } label: {
                            MeaningCard(
                                label: record.label.uppercased(),
                                text: record.quote,
                                secondary: record.why.isEmpty ? record.stamp : record.why
                            ) {
                                Thumbs(state: model.thumbState(record.row)) { up in
                                    Task { await model.thumb(record.row, up: up) }
                                }
                            }
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("live-record-\(record.row.record)")
                    }
                }
                .padding(.horizontal, 2)
            }
            .accessibilityIdentifier("liveRoutesCarousel")
        }
    }

    @ViewBuilder
    private var possibility: some View {
        if !parts.possibility.isEmpty {
            VStack(alignment: .leading, spacing: 14) {
                kicker("POSSIBILITY")
                ForEach(Array(parts.possibility.enumerated()), id: \.offset) { _, block in
                    Text(block)
                        .font(CowboyTheme.readingSerif(22, relativeTo: .body))
                        .foregroundStyle(.black)
                        .lineSpacing(5)
                        .fixedSize(horizontal: false, vertical: true)
                        .textSelection(.enabled)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(20)
            .background(CowboyTheme.cream, in: RoundedRectangle(cornerRadius: 18))
            .padding(.horizontal, 18)
            .padding(.top, 24)
        }
    }

    private func sectionTitle(_ title: String) -> some View {
        Text(title)
            .font(.system(size: 20, weight: .black))
            .foregroundStyle(.black)
            .frame(minHeight: 80)
            .padding(.horizontal, 18)
    }

    private func kicker(_ title: String) -> some View {
        Text(title)
            .font(.system(size: 11, weight: .heavy))
            .tracking(1.4)
            .foregroundStyle(CowboyTheme.red)
    }
}

/// The results carousel card, holding one of Adam's meanings in his words.
private struct MeaningCard<Corner: View>: View {
    let label: String
    let text: String
    let secondary: String
    @ViewBuilder let corner: Corner
    @ScaledMetric(relativeTo: .body) private var cardHeight: CGFloat = 182

    init(label: String, text: String, secondary: String, @ViewBuilder corner: () -> Corner) {
        self.label = label
        self.text = text
        self.secondary = secondary
        self.corner = corner()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(label)
                    .font(.system(size: 11, weight: .heavy))
                    .tracking(1.1)
                    .lineLimit(1)
                Spacer(minLength: 8)
                corner
            }
            .foregroundStyle(CowboyTheme.red)

            Text(text)
                .font(CowboyTheme.carouselSerif(24))
                .lineLimit(3)
                .minimumScaleFactor(0.85)
                .foregroundStyle(.black)
                .frame(maxWidth: .infinity, alignment: .leading)

            if !secondary.isEmpty {
                Text(secondary)
                    .font(.system(size: 14))
                    .foregroundStyle(.black.opacity(0.66))
                    .lineLimit(2)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
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
        .accessibilityHint("Opens the complete words")
    }
}

extension MeaningCard where Corner == AnyView {
    init(label: String, text: String, secondary: String) {
        self.init(label: label, text: text, secondary: secondary) {
            AnyView(Image(systemName: "chevron.right").font(.system(size: 12, weight: .semibold)))
        }
    }
}

/// His thumb on a row or on the meaning, in the app's own red-tinted button style.
struct Thumbs: View {
    let state: Int?
    let choose: (Bool) -> Void

    var body: some View {
        HStack(spacing: 14) {
            Button {
                choose(true)
            } label: {
                Image(systemName: state == 1 ? "hand.thumbsup.fill" : "hand.thumbsup")
                    .font(.system(size: 17, weight: .semibold))
            }
            .accessibilityLabel("Thumbs up")
            Button {
                choose(false)
            } label: {
                Image(systemName: state == 0 ? "hand.thumbsdown.fill" : "hand.thumbsdown")
                    .font(.system(size: 17, weight: .semibold))
            }
            .accessibilityLabel("Thumbs down")
        }
        .buttonStyle(.borderless)
        .tint(CowboyTheme.red)
    }
}

/// The complete words under one record, laid out like a saved result.
struct RecordDetail: View {
    @Environment(\.dismiss) private var dismiss
    let record: AnswerParts.Record
    var model: AskModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(record.label.uppercased())
                            .font(.system(size: 11, weight: .heavy))
                            .tracking(1.4)
                            .foregroundStyle(CowboyTheme.red)
                        Text(record.quote)
                            .font(CowboyTheme.readingSerif(22, relativeTo: .body))
                            .foregroundStyle(.black)
                            .lineSpacing(5)
                            .fixedSize(horizontal: false, vertical: true)
                            .textSelection(.enabled)
                        if !record.why.isEmpty {
                            Text(record.why)
                                .font(CowboyTheme.readingSerif(22, relativeTo: .body))
                                .foregroundStyle(.black)
                                .lineSpacing(5)
                                .fixedSize(horizontal: false, vertical: true)
                                .textSelection(.enabled)
                        }
                        if !record.stamp.isEmpty {
                            Text(record.stamp)
                                .font(.system(size: 11, weight: .bold))
                                .tracking(1)
                                .foregroundStyle(.secondary)
                                .padding(.top, 4)
                        }
                        Thumbs(state: model.thumbState(record.row)) { up in
                            Task { await model.thumb(record.row, up: up) }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(20)
                    .background(CowboyTheme.cream, in: RoundedRectangle(cornerRadius: 18))
                    .accessibilityIdentifier("meaning-detail-words")
                }
                .padding(20)
                .padding(.top, 12)
                .padding(.bottom, 28)
            }
            .background(Color.white)
            .navigationTitle(record.row.word)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Close", systemImage: "xmark.circle") { dismiss() }
                        .labelStyle(.iconOnly)
                        .font(.system(size: 22))
                        .tint(.black)
                        .accessibilityIdentifier("meaning-detail-close")
                }
            }
        }
    }
}

/// The complete meanings under one of his words.
struct WordsDetail: View {
    @Environment(\.dismiss) private var dismiss
    let words: AnswerParts.Words

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(words.word.uppercased())
                            .font(.system(size: 11, weight: .heavy))
                            .tracking(1.4)
                            .foregroundStyle(CowboyTheme.red)
                        ForEach(Array(words.meanings.enumerated()), id: \.offset) { _, line in
                            Text(line)
                                .font(CowboyTheme.readingSerif(22, relativeTo: .body))
                                .foregroundStyle(.black)
                                .lineSpacing(5)
                                .fixedSize(horizontal: false, vertical: true)
                                .textSelection(.enabled)
                        }
                        if !words.why.isEmpty {
                            Text(words.why)
                                .font(.system(size: 11, weight: .bold))
                                .tracking(1)
                                .foregroundStyle(.secondary)
                                .padding(.top, 4)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(20)
                    .background(CowboyTheme.cream, in: RoundedRectangle(cornerRadius: 18))
                    .accessibilityIdentifier("meaning-detail-words")
                }
                .padding(20)
                .padding(.top, 12)
                .padding(.bottom, 28)
            }
            .background(Color.white)
            .navigationTitle(words.word)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Close", systemImage: "xmark.circle") { dismiss() }
                        .labelStyle(.iconOnly)
                        .font(.system(size: 22))
                        .tint(.black)
                        .accessibilityIdentifier("meaning-detail-close")
                }
            }
        }
    }
}
