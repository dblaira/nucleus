import SwiftUI

struct ArchivedAnswerPage: View {
    @State private var model: AskModel
    init(origin: ConversationOrigin, archive: ConversationArchive) {
        let model = AskModel(archive: archive)
        model.showSnapshot(origin)
        _model = State(initialValue: model)
    }
    var body: some View { AnswerPage(model: model, id: nil) }
}

private struct EntryPresentation: Identifiable {
    let kind: ReminderKind
    let existing: Reminder?
    var id: String { existing?.id.uuidString ?? kind.rawValue }
}

/// Every create action captures the displayed response, never an unrelated global selection.
struct ConversationControls: View {
    let origin: ConversationOrigin
    @Environment(ConversationArchive.self) private var archive
    @Environment(ReminderStore.self) private var entries
    @State private var editor: EntryPresentation?
    @State private var showingDetails = false
    @State private var armedEntryID: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Button {
                    _ = archive.togglePin(origin)
                } label: {
                    Label(archive.isPinned(origin) ? "Unpin" : "Pin", systemImage: archive.isPinned(origin) ? "pin.fill" : "pin")
                }
                .accessibilityIdentifier("pinConversation")
                Button { showingDetails = true } label: {
                    Label("Details", systemImage: "slider.horizontal.3")
                }
                .accessibilityIdentifier("conversationDetails")
                Spacer()
                Menu {
                    ForEach(ReminderKind.allCases.filter { $0 != .post }) { kind in
                        Button(kind.label, systemImage: symbol(kind)) { editor = EntryPresentation(kind: kind, existing: nil) }
                    }
                } label: { Label("Create", systemImage: "plus") }
                .accessibilityIdentifier("createFromConversation")
            }
            .font(.system(size: 16, weight: .semibold))

            SavyCardFlow(spacing: 10) {
                ForEach(Array(entries.items(from: origin).filter { $0.status == .active }.enumerated()), id: \.element.id) { index, entry in
                    let colors = SavyReminderCardAppearance.colors(for: index)
                    SavyUpNextCardRow(
                        reminderId: entry.id.uuidString, armedId: $armedEntryID,
                        actions: [
                            SavySwipeAction(title: "Done", icon: "checkmark", bg: SavyTheme.crimson) { entries.complete(entry) },
                            SavySwipeAction(title: entry.pinned ? "Unpin" : "Pin", icon: "pin", bg: Brand.tileBlue) { entries.togglePin(entry) },
                            SavySwipeAction(title: "Delete", icon: "trash", bg: CowboyTheme.red) { entries.delete(entry) },
                        ],
                        onTap: { editor = EntryPresentation(kind: entry.kind, existing: entry) },
                        onMoveUp: { entries.moveUpNext(entry, direction: .up) },
                        onMoveDown: { entries.moveUpNext(entry, direction: .down) }
                    ) {
                        SavyReminderBandCard(
                            reminder: entry, bg: colors.bg, fg: colors.fg, accent: colors.accent,
                            detail: entry.pinned ? .full : .minimal, showsCompleteMetadata: true
                        )
                        .accessibilityIdentifier("linkedEntry-\(entry.id.uuidString)")
                    }
                }
                ForEach(entries.items(from: origin).filter { $0.status == .completed }) { entry in
                    SavyCompletedReminderRow(
                        reminder: entry,
                        onToggle: { entries.uncomplete(entry) },
                        onTap: { editor = EntryPresentation(kind: entry.kind, existing: entry) },
                        onDelete: { entries.delete(entry) }
                    )
                }
            }
            if let message = archive.errorMessage ?? entries.errorMessage {
                Text(message).font(.footnote).accessibilityIdentifier("localSaveError")
            }
        }
        .foregroundStyle(.white)
        .padding(20)
        .sheet(isPresented: $showingDetails) { ConversationDetailsEditor(origin: origin) }
        .sheet(item: $editor) { presentation in
            ReminderFormView(initialKind: presentation.kind, origin: origin, existing: presentation.existing,
                             existingTags: entries.recentTags, onSaveAttempt: { entries.save($0) }) { _ in }
        }
    }

    private func symbol(_ kind: ReminderKind) -> String {
        switch kind { case .reminder: "bell"; case .action: "bolt"; case .event: "calendar"; case .post: "text.bubble" }
    }
}

/// Uses SAVY's form controls. This edits the pair's local metadata only;
/// scheduling remains on the actual Reminder / Action / Calendar entry.
struct ConversationDetailsEditor: View {
    let origin: ConversationOrigin
    @Environment(ConversationArchive.self) private var archive
    @Environment(ReminderStore.self) private var entries

    var body: some View {
        ReminderFormView(
            origin: origin,
            existing: archive.metadata(for: origin),
            existingTags: entries.recentTags,
            conversationID: origin.conversationID,
            onSaveAttempt: { archive.saveMetadata($0, for: origin) },
            onSave: { _ in }
        )
    }
}
