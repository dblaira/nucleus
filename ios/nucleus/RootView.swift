import SwiftUI

/// SAVY's shell (RootView.swift in SAVY-iOS): tabs at the bottom with the bolt, pages pushed over the home.
enum AppTab: String, CaseIterable, Identifiable {
    case now
    case route

    var id: String { rawValue }

    var title: String {
        switch self {
        case .now: "Now"
        case .route: "Route"
        }
    }

    var symbolName: String {
        switch self {
        case .now: "house"
        case .route: "arrow.triangle.branch"
        }
    }
}

/// A page pushed over the home. The answer page shows one question and its answer (nil: the one being asked now).
enum Page: Hashable {
    case answer(String?)
    case category(Category)
}

struct RootView: View {
    var model: AskModel
    @Environment(\.scenePhase) private var scenePhase
    @State private var selectedTab: AppTab = .now
    @State private var path = NavigationPath()
    @State private var showingSettings = false
    @State private var showingComposer = false

    var body: some View {
        NavigationStack(path: $path) {
            ZStack {
                CowboyTheme.paper.ignoresSafeArea()

                Group {
                    switch selectedTab {
                    case .now:
                        HomeView(
                            model: model,
                            openAnswer: { path.append(Page.answer($0)) },
                            openCategory: { path.append(Page.category($0)) },
                            openConnection: { showingSettings = true }
                        )
                    case .route:
                        RouteView(model: model)
                    }
                }
                .padding(.bottom, SavyLayout.bottomNavigationHeight)

                VStack(spacing: 0) {
                    Spacer()
                    SavyBottomNavigationBar(selection: $selectedTab, openComposer: { showingComposer = true })
                }
                .ignoresSafeArea(edges: .bottom)

                if selectedTab != .now {
                    menuButton
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar(.hidden, for: .navigationBar)
            .navigationDestination(for: Page.self) { page in
                switch page {
                case .answer(let id):
                    AnswerPage(model: model, id: id)
                case .category(let category):
                    CategoryPage(model: model, category: category, openAnswer: { path.append(Page.answer($0)) })
                }
            }
            .sheet(isPresented: $showingSettings) {
                SettingsView()
            }
            .sheet(isPresented: $showingComposer) {
                ComposerView(model: model) {
                    // The form closes at once; the answer page opens while the answer is still being written.
                    showingComposer = false
                    selectedTab = .now
                    path = NavigationPath([Page.answer(nil)])
                    Task { await model.ask() }
                }
            }
        }
        .task {
            print("nucleus: view task started")
            await NucleusAPI.hello()
            await model.loadRecent()
            // a question handed in at launch (`-ask "..."`) is asked at once; used by the Mac to test the app
            if let i = CommandLine.arguments.firstIndex(of: "-theme"), i + 1 < CommandLine.arguments.count {
                model.selectTheme(CommandLine.arguments[i + 1])
                if let j = CommandLine.arguments.firstIndex(of: "-answers"), j + 1 < CommandLine.arguments.count, let theme = model.theme {
                    for (index, answer) in CommandLine.arguments[j + 1].split(separator: "|", omittingEmptySubsequences: false).enumerated()
                    where theme.questions.indices.contains(index) {
                        model.setThemeField(theme.questions[index].prompt + "\n" + answer, at: index)
                    }
                }
            }
            if let i = CommandLine.arguments.firstIndex(of: "-ask"), i + 1 < CommandLine.arguments.count {
                model.question = CommandLine.arguments[i + 1]
                path = NavigationPath([Page.answer(nil)])
                await model.ask()
            }
            // a past answer handed in at launch (`-open "<id>"`) opens at once; used by the Mac to test the app
            if let i = CommandLine.arguments.firstIndex(of: "-open"), i + 1 < CommandLine.arguments.count {
                let id = CommandLine.arguments[i + 1]
                path = NavigationPath([Page.answer(id)])
                // `-log "<text>"` then logs more information under it, the way the Log button does
                if let j = CommandLine.arguments.firstIndex(of: "-log"), j + 1 < CommandLine.arguments.count {
                    await model.open(id)
                    model.moreDrafts[id] = CommandLine.arguments[j + 1]
                    await model.logMore()
                }
            }
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active, !model.working else { return }
            Task { await model.loadRecent() }
        }
    }

    @ViewBuilder
    private var menuButton: some View {
        VStack {
            HStack {
                Spacer()
                SavyMenuButton(openConnection: { showingSettings = true }, appearance: .onWhiteHeader)
            }
            .padding(.horizontal, 16)
            Spacer()
        }
        .safeAreaPadding(.top, 10)
        .zIndex(20)
    }
}
