import SwiftUI

enum AppTab: String, CaseIterable, Identifiable {
    case now, reminders, actions, calendar
    var id: String { rawValue }
    var title: String {
        switch self { case .now: "Now"; case .reminders: "Reminders"; case .actions: "Actions"; case .calendar: "Calendar" }
    }
    var symbolName: String {
        switch self { case .now: "house"; case .reminders: "bell"; case .actions: "bolt"; case .calendar: "calendar" }
    }
}

enum Page: Hashable {
    case answer(String?)
    case category(Category)
    case origin(ConversationOrigin)
    case route
}

private enum RootSheet: String, Identifiable {
    case question, reminder, action, event, settings, appearance
    var id: String { rawValue }
    var kind: ReminderKind {
        switch self { case .action: .action; case .event: .event; default: .reminder }
    }
}

struct RootView: View {
    var model: AskModel
    @Environment(\.scenePhase) private var scenePhase
    @State private var selectedTab: AppTab = .now
    @State private var path = NavigationPath()
    @State private var sheet: RootSheet?
    @State private var showingCreate = false
    @State private var entries = ReminderStore()
    @State private var appearance = HomeAppearance()
    @State private var recovery: EntryRecoveryDraft?
    @State private var notificationEntry: Reminder?
    @ObservedObject private var notificationStatus = NotificationScheduler.status

    var body: some View {
        NavigationStack(path: $path) {
            ZStack(alignment: .bottom) {
                CowboyTheme.navy.ignoresSafeArea()
                Group {
                    switch selectedTab {
                    case .now:
                        HomeView(model: model, openAnswer: { path.append(Page.answer($0)) },
                                 openCategory: { path.append(Page.category($0)) },
                                 openConnection: { sheet = .settings },
                                 openOrigin: { path.append(Page.origin($0)) },
                                 openRoute: { path.append(Page.route) },
                                 openAppearance: { sheet = .appearance })
                    case .reminders: SavyReminderKindTabScreen(kind: .reminder)
                    case .actions: SavyReminderKindTabScreen(kind: .action)
                    case .calendar: SavyCalendarTabScreen()
                    }
                }
                if showingCreate {
                    Color.black.opacity(0.45).ignoresSafeArea()
                        .onTapGesture {
                            SavyHapticFeedback.menuClose()
                            withAnimation(SavyFabMenuMotion.close) { showingCreate = false }
                        }
                        .transition(.opacity)
                }
                if selectedTab != .now {
                    VStack {
                        HStack {
                            Spacer()
                            SavyMenuButton(openConnection: { sheet = .settings }, openRoute: { path.append(Page.route) },
                                           openAppearance: { sheet = .appearance })
                        }.padding(.horizontal, 18).padding(.top, 10)
                        Spacer()
                    }.safeAreaPadding(.top, 8)
                }
            }
            .safeAreaInset(edge: .bottom, spacing: 0) {
                SavyBottomNavigationBar(selection: $selectedTab, isRadialMenuPresented: $showingCreate) { kind in
                    showingCreate = false
                    switch kind { case .question: sheet = .question; case .reminder: sheet = .reminder; case .action: sheet = .action; case .calendar: sheet = .event }
                }
            }
            .animation(SavyFabMenuMotion.open, value: showingCreate)
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: Page.self) { page in
                switch page {
                case .answer(let id): AnswerPage(model: model, id: id)
                case .category(let category): CategoryPage(model: model, category: category, openAnswer: { path.append(Page.answer($0)) })
                case .origin(let origin): ArchivedAnswerPage(origin: origin, archive: model.archive)
                case .route: RouteView(model: model)
                }
            }
            .sheet(item: $sheet) { presentation in
                switch presentation {
                case .question:
                    ComposerView(model: model) {
                        sheet = nil; selectedTab = .now; path = NavigationPath([Page.answer(nil)])
                        Task { await model.ask() }
                    }
                case .settings: SettingsView()
                case .appearance: HomeBackgroundSettings(screen: selectedTab)
                default:
                    ReminderFormView(initialKind: presentation.kind, existing: nil,
                                     existingTags: entries.recentTags, onSaveAttempt: { entries.save($0) }) { _ in }
                }
            }
            .sheet(item: $notificationEntry) { entry in
                ReminderFormView(existing: entry, existingTags: entries.recentTags, onSaveAttempt: { entries.save($0) }) { _ in }
            }
            .sheet(item: $recovery) { draft in
                ReminderFormView(existing: nil, existingTags: entries.recentTags, recoveryDraft: draft,
                                 onSaveAttempt: { entries.save($0) }) { _ in }
            }
            .alert("Couldn't finish the schedule", isPresented: Binding(
                get: { notificationStatus.errorMessage != nil }, set: { if !$0 { notificationStatus.errorMessage = nil } }
            )) {
                Button("OK", role: .cancel) { notificationStatus.errorMessage = nil }
            } message: { Text(notificationStatus.errorMessage ?? "") }
        }
        .environment(entries)
        .environment(appearance)
        .environment(model.archive)
        .task {
            NotificationScheduler.configurePresentation()
            if CowboyRuntime.isTesting {
                CowboyUITestFixtures.prepare(model: model, entries: entries)
            } else {
                await entries.bootstrap()
                recovery = EntryDraftStore.shared.latest
                await NucleusAPI.hello()
                await model.loadRecent()
                #if DEBUG
                if let index = CommandLine.arguments.firstIndex(of: "-ask"), index + 1 < CommandLine.arguments.count {
                    model.question = CommandLine.arguments[index + 1]
                    path = NavigationPath([Page.answer(nil)])
                    await model.ask()
                } else if let index = CommandLine.arguments.firstIndex(of: "-open"), index + 1 < CommandLine.arguments.count {
                    path = NavigationPath([Page.answer(CommandLine.arguments[index + 1])])
                }
                #endif
            }
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active, !model.working, !CowboyRuntime.isTesting else { return }
            Task { await model.loadRecent() }
        }
        .onReceive(notificationStatus.$pendingEntryID.compactMap { $0 }) { id in
            guard let entry = entries.item(id) else { notificationStatus.pendingEntryID = nil; return }
            if entry.status == .deleted {
                if let origin = entry.origin { path = NavigationPath([Page.origin(origin)]) }
            } else { notificationEntry = entry }
            notificationStatus.pendingEntryID = nil
        }
    }
}
