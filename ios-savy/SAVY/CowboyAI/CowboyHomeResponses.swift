import SwiftUI

/// The same SAVY card and right-swipe controls, displaying CowboyAI's saved responses.
struct CowboyResponseCards: View {
    let model: AskModel
    @Binding var armedID: String?
    let onOpen: (ConversationOrigin) -> Void
    @State private var editing: ConversationOrigin?

    private var records: [ArchivedConversation] { model.archive.records(for: NucleusAPI.base) }

    var body: some View {
        SavyCardFlow(spacing: RootHomeLayout.homeBandCardSpacing) {
            if let problem = model.recentProblem {
                Text(problem).font(.callout).foregroundStyle(SavyTheme.deepNavy)
                    .padding(16).background(Brand.card, in: RoundedRectangle(cornerRadius: 8))
            }
            ForEach(Array(records.enumerated()), id: \.element.id) { index, record in
                let origin = record.displayed
                let metadata = model.archive.metadata(for: origin)
                let colors = SavyReminderCardAppearance.colors(for: index)
                SavyUpNextCardRow(
                    reminderId: record.id, armedId: $armedID,
                    actions: [
                        SavySwipeAction(title: metadata.pinned ? "Unpin" : "Pin", icon: "pin", bg: Brand.tileBlue) {
                            withAnimation(.snappy) { _ = model.archive.togglePin(origin) }
                        },
                        SavySwipeAction(title: "Edit", icon: "pencil", bg: SavyTheme.deepNavy) { editing = origin },
                    ],
                    onTap: { onOpen(origin) },
                    onMoveUp: { withAnimation(.snappy) { _ = model.archive.move(origin, direction: .up) } },
                    onMoveDown: { withAnimation(.snappy) { _ = model.archive.move(origin, direction: .down) } },
                    gestureAccessibilityIdentifier: "responseSwipe-\(origin.questionID)"
                ) {
                    SavyBandCard(
                        bg: colors.bg, fg: colors.fg, accent: colors.accent,
                        title: origin.question,
                        signalText: SavyCarouselDetail.values(for: metadata).map(\.text).joined(separator: " · "),
                        secondaryText: "", detailLine: origin.answerPreview,
                        detail: metadata.pinned ? .full : .minimal,
                        isCompact: !metadata.pinned,
                        minimumHeight: metadata.pinned ? 186 : nil,
                        titleAccessibilityIdentifier: "recentResponse-\(origin.questionID)"
                    )
                    .shadow(color: .black.opacity(0.12), radius: 2, y: 1)
                }
                .zIndex(armedID == record.id ? 1 : 0)
                .accessibilityElement(children: .contain)
                .accessibilityIdentifier("recent-\(origin.questionID)")
                .accessibilityValue(metadata.pinned ? "Pinned" : "Unpinned")
            }
        }
        .padding(.horizontal, RootHomeLayout.homeBandHorizontalPadding)
        .padding(.vertical, RootHomeLayout.homeBandTopPadding)
        .sheet(item: $editing) { origin in ConversationDetailsEditor(origin: origin) }
        .alert("Saved response", isPresented: Binding(
            get: { model.archive.errorMessage != nil },
            set: { if !$0 { model.archive.errorMessage = nil } }
        )) { Button("OK") { model.archive.errorMessage = nil } }
        message: { Text(model.archive.errorMessage ?? "") }
    }
}

/// Carousel dimensions and metadata use the original SAVY component. Pinning changes
/// order, never the dimensions of a response preview or the response's source words.
struct CowboyResponseCarouselCard: View {
    let origin: ConversationOrigin
    let metadata: Reminder
    var body: some View {
        SavyBandCard(
            bg: Brand.card, fg: SavyTheme.deepNavy, accent: Brand.crimson,
            title: origin.question, signalText: "", secondaryText: "",
            detail: .full, isCompact: false,
            previewHeight: RootHomeLayout.carouselCardHeight,
            carouselDetails: SavyCarouselDetail.values(for: metadata)
        )
        .frame(width: RootHomeLayout.carouselCardWidth, alignment: .topLeading)
        .accessibilityElement(children: .combine)
    }
}

struct SavedResponsePage: View {
    @State private var model: AskModel
    let origin: ConversationOrigin
    let pinned: Bool

    init(origin: ConversationOrigin, archive: ConversationArchive, pinned: Bool) {
        self.origin = origin
        self.pinned = pinned
        let model = AskModel(archive: archive, keepsComposerDraft: false)
        model.showSnapshot(origin)
        if !pinned { model.isFrozen = false }
        _model = State(initialValue: model)
    }

    var body: some View {
        AnswerPage(model: model, id: nil)
            .task { if !pinned { await model.open(origin.questionID) } }
    }
}
