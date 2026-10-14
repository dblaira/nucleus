import SwiftUI

/// The same SAVY card and right-swipe controls, displaying CowboyAI's saved responses.
struct CowboyResponseCards: View {
    let model: AskModel
    @Binding var armedID: String?
    let onOpen: (ConversationOrigin) -> Void
    @State private var isCompletedExpanded = false

    private var records: [ArchivedConversation] { model.archive.records(for: NucleusAPI.base) }
    private var completed: [ArchivedConversation] { model.archive.records(for: NucleusAPI.base, status: .completed) }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
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
                            SavySwipeAction(title: "Done", icon: "checkmark", bg: SavyTheme.crimson) {
                                withAnimation(.snappy) { _ = model.archive.complete(origin) }
                            },
                            SavySwipeAction(title: metadata.pinned ? "Unpin" : "Pin", icon: "pin", bg: Brand.tileBlue) {
                                withAnimation(.snappy) { _ = model.archive.togglePin(origin) }
                            },
                            SavySwipeAction(title: "Delete", icon: "trash", bg: Color(hex: 0xB00124)) {
                                withAnimation(.snappy) { _ = model.archive.delete(origin) }
                            },
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
            completedSection
        }
        .padding(.horizontal, RootHomeLayout.homeBandHorizontalPadding)
        .padding(.vertical, RootHomeLayout.homeBandTopPadding)
        .alert("Saved response", isPresented: Binding(
            get: { model.archive.errorMessage != nil },
            set: { if !$0 { model.archive.errorMessage = nil } }
        )) { Button("OK") { model.archive.errorMessage = nil } }
        message: { Text(model.archive.errorMessage ?? "") }
    }

    /// Re_Call's CompletedBand uses this same collapsed count and the SAVY completed row.
    @ViewBuilder private var completedSection: some View {
        if !completed.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Button {
                    SavyHapticFeedback.selection()
                    withAnimation(.snappy) { isCompletedExpanded.toggle() }
                } label: {
                    HStack(spacing: 8) {
                        Text("Completed")
                            .font(.system(size: 13, weight: .heavy))
                            .textCase(.uppercase).tracking(1.5)
                            .foregroundStyle(Brand.card)
                        Text("\(completed.count)")
                            .font(.system(size: 12, weight: .heavy))
                            .foregroundStyle(SavyTheme.crimson)
                        Image(systemName: isCompletedExpanded ? "chevron.down" : "chevron.right")
                            .font(.system(size: 11, weight: .heavy))
                            .foregroundStyle(SavyTheme.crimson)
                        Spacer(minLength: 0)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(isCompletedExpanded ? "Hide completed items" : "Show completed items")
                .accessibilityValue("\(completed.count)")
                .accessibilityIdentifier("completedResponsesToggle")

                if isCompletedExpanded {
                    ForEach(completed) { record in
                        let origin = record.displayed
                        SavyCompletedReminderRow(
                            reminder: model.archive.metadata(for: origin),
                            onToggle: { withAnimation(.snappy) { _ = model.archive.uncomplete(origin) } },
                            onTap: { onOpen(origin) },
                            onDelete: { withAnimation(.snappy) { _ = model.archive.delete(origin) } }
                        )
                        .accessibilityElement(children: .contain)
                        .accessibilityIdentifier("completedResponse-\(origin.questionID)")
                    }
                    .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
            .padding(.top, 18)
            .padding(.bottom, 16)
        }
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
