import SwiftUI

/// The CowboyAI app's shell: the hat header, the tan bottom bar with the red bolt, the hat button. Copied from
/// Cowboyai/authority-hub/ios/CowboyAI/RootView.swift; the screens under it are nucleus's.
enum AppTab: String, CaseIterable, Identifiable {
    case decide
    case route

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .decide: "text.bubble"
        case .route: "arrow.triangle.branch"
        }
    }

    var title: String {
        switch self {
        case .decide: "Decide"
        case .route: "Route"
        }
    }
}

struct RootView: View {
    var model: AskModel
    @Environment(\.scenePhase) private var scenePhase
    @State private var selectedTab: AppTab = .decide
    @State private var showingSettings = false
    @State private var showingComposer = false

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            NavigationStack {
                Group {
                    switch selectedTab {
                    case .decide:
                        DecideView(model: model)
                    case .route:
                        RouteView(model: model)
                    }
                }
                .safeAreaInset(edge: .top, spacing: 0) {
                    CowboyHeader {
                        showingSettings = true
                    }
                }
                .safeAreaInset(edge: .bottom, spacing: 0) {
                    BottomNavigation(
                        selection: $selectedTab,
                        openComposer: { showingComposer = true }
                    )
                }
                .toolbar(.hidden, for: .navigationBar)
                .sheet(isPresented: $showingSettings) {
                    SettingsView()
                }
                .sheet(isPresented: $showingComposer) {
                    ComposerView(model: model) {
                        // The form closes at once; his words appear on Decide while the answer is still being written.
                        showingComposer = false
                        selectedTab = .decide
                        Task { await model.ask() }
                    }
                }
            }

            Button {
                selectedTab = .decide
            } label: {
                Image("CowboyHat")
                    .renderingMode(.template)
                    .resizable()
                    .scaledToFit()
                    .foregroundStyle(CowboyTheme.cream)
                    .frame(width: 42, height: 32)
                    .frame(width: 58, height: 58)
                    .background(CowboyTheme.navy, in: Circle())
                    .overlay {
                        Circle().stroke(CowboyTheme.red, lineWidth: 2)
                    }
                    .shadow(color: .black.opacity(0.24), radius: 8, y: 4)
            }
            .buttonStyle(.plain)
            .padding(.trailing, 14)
            .padding(.bottom, 106)
            .accessibilityLabel("Open nucleus")
            .accessibilityIdentifier("assistant-hat")
        }
        .task {
            print("nucleus: view task started")
            await NucleusAPI.hello()
            await model.loadRecent()
            // a question handed in at launch (`-ask "..."`) is asked at once; used by the Mac to test the app
            if let i = CommandLine.arguments.firstIndex(of: "-ask"), i + 1 < CommandLine.arguments.count {
                model.question = CommandLine.arguments[i + 1]
                await model.ask()
            }
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active, !model.working else { return }
            Task { await model.loadRecent() }
        }
        .cowboyBackground()
    }
}

private struct CowboyHeader: View {
    let openSettings: () -> Void

    var body: some View {
        ZStack {
            Image("CowboyHat")
                .renderingMode(.template)
                .resizable()
                .scaledToFill()
                .frame(width: 188, height: 106)
                .clipped()
                .foregroundStyle(CowboyTheme.tan)
                .accessibilityLabel("nucleus")

            HStack {
                Spacer()
                Button(action: openSettings) {
                    Image(systemName: "slider.horizontal.3")
                        .font(.system(size: 22, weight: .regular))
                        .foregroundStyle(CowboyTheme.cream)
                        .frame(width: 44, height: 44)
                }
                .accessibilityLabel("Connection settings")
            }
        }
        .padding(.horizontal, 16)
        .frame(maxWidth: .infinity)
        .frame(height: 110)
        .background(CowboyTheme.navy)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(CowboyTheme.red)
                .frame(height: 3)
        }
    }
}

private struct BottomNavigation: View {
    @Binding var selection: AppTab
    let openComposer: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            CowboyTheme.navy
                .frame(height: 24)

            ZStack(alignment: .top) {
                CowboyTheme.bottomNavigationTan

                HStack(alignment: .center, spacing: 0) {
                    navigationButton(for: .decide)

                    Spacer()
                        .frame(maxWidth: .infinity)

                    navigationButton(for: .route)
                }
                .padding(.horizontal, 12)
                .padding(.top, 14)

                Button(action: openComposer) {
                    borderedBolt
                        .frame(width: 64, height: 64)
                        .background(CowboyTheme.red, in: Circle())
                        .shadow(color: .black.opacity(0.3), radius: 12, y: 6)
                }
                .buttonStyle(.plain)
                .offset(y: -22)
                .accessibilityLabel("Add a question")
                .accessibilityIdentifier("chargeFab")
            }
            .frame(height: 72)
        }
        .frame(height: 96)
        .background(CowboyTheme.bottomNavigationTan.ignoresSafeArea(edges: .bottom))
    }

    private func navigationButton(for tab: AppTab) -> some View {
        let isSelected = selection == tab

        return Button {
            selection = tab
        } label: {
            VStack(spacing: 4) {
                Image(systemName: tab.icon)
                    .font(.system(size: 22, weight: isSelected ? .semibold : .regular))
                Text(tab.title)
                    .font(.system(size: 11, weight: isSelected ? .bold : .semibold))
            }
            .frame(maxWidth: .infinity)
            .frame(height: 58)
            .foregroundStyle(isSelected ? CowboyTheme.red : CowboyTheme.navigationInactive)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(tab.title)
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }

    private var borderedBolt: some View {
        ZStack {
            Image(systemName: "bolt.fill")
                .font(.system(size: 30, weight: .bold))
                .foregroundStyle(.black)
            Image(systemName: "bolt.fill")
                .font(.system(size: 25, weight: .bold))
                .foregroundStyle(.white)
        }
    }
}
