import SwiftUI

/// The SAVY app's shell, copied from /Users/adamblair/Developer/GitHub/SAVY-iOS/SAVY (RootView.swift,
/// SavyShellComponents.swift, ConnectionView.swift). Adam, 2026-09-14: "refer to the savy app repo so you can see the
/// type of navigation expect. Adopt the homepage layout of SAVY."
enum SavyLayout {
    static let horizontalPadding: CGFloat = 24
    static let heroHeight: CGFloat = 204
    static let heroContentTopPadding: CGFloat = 34
    static let heroDividerHeight: CGFloat = 3
    static let heroWordmarkFontSize: CGFloat = 64
    static let carouselHorizontalPadding: CGFloat = 2
    static let carouselCardWidth: CGFloat = 282
    static let carouselCardHeight: CGFloat = 182
    static let carouselCardTitleFontSize: CGFloat = 24
    static let pinnedEntryTrailingInset: CGFloat = 17
    static let bottomNavigationHeight: CGFloat = 128
    static let bottomNavNavyRiserHeight: CGFloat = 44
    static let bottomNavigationTopPadding: CGFloat = 8
    static let bottomNavigationBottomPadding: CGFloat = 28
    static let bottomNavigationIconSize: CGFloat = 25
    static let bottomNavigationLabelSize: CGFloat = 15
    static let bottomNavigationIconLabelSpacing: CGFloat = 7
    static let floatingCaptureSize: CGFloat = 64
    static let floatingCaptureSymbolOuterSize: CGFloat = 30
    static let floatingCaptureSymbolInnerSize: CGFloat = 25
    static let accountMenuSymbolName = "line.3.horizontal"
    static let accountMenuButtonSize: CGFloat = 42

    /// Nudges the menu down to the optical center of the wordmark cap height.
    static var accountMenuHeroWordmarkOffset: CGFloat {
        ((heroWordmarkFontSize - accountMenuButtonSize) * 0.42) + 5
    }

    /// SAVY's editorial serif, bold by default (SavyTypography.displaySerif).
    static func displaySerif(_ size: CGFloat, weight: Font.Weight = .bold) -> Font {
        Font.custom(CowboyTheme.editorialSerifName, size: size).weight(weight)
    }
}

/// His three lines. Each is a page of past answers. Adam, 2026-09-14: "past answers under aligned and why, past
/// answers under are responses under not sure, some correlation, past answers under I don't know."
enum Category: String, CaseIterable, Identifiable, Hashable {
    case aligned
    case notSure = "not_sure"
    case dontKnow = "dont_know"

    var id: String { rawValue }

    var eyebrow: String {
        switch self {
        case .aligned: "ALIGNED"
        case .notSure: "NOT SURE"
        case .dontKnow: "I DON'T KNOW"
        }
    }

    /// The first line of the answer, in his words (gate.FIRST_LINE).
    var title: String {
        switch self {
        case .aligned: "aligned and why"
        case .notSure: "There is some relationship, but not enough to justify causation."
        case .dontKnow: "I don't know. There is nothing in your records that points to a conclusion."
        }
    }
}

enum SavyMenuAppearance {
    case onDarkHero
    case onWhiteHeader
}

/// SAVY's round menu button at the top right (SavyAccountMenuButton).
struct SavyMenuButton: View {
    let openConnection: () -> Void
    var appearance: SavyMenuAppearance = .onDarkHero
    var openRoute: (() -> Void)? = nil
    var openAppearance: (() -> Void)? = nil

    var body: some View {
        Menu {
            if let openAppearance { Button("Background photo", systemImage: "photo", action: openAppearance) }
            if let openRoute { Button("Route", systemImage: "arrow.triangle.branch", action: openRoute) }
            Button {
                openConnection()
            } label: {
                Label("Connection", systemImage: "slider.horizontal.3")
            }
        } label: {
            Image(systemName: SavyLayout.accountMenuSymbolName)
                .font(.system(size: 18, weight: .bold))
                .foregroundStyle(iconColor)
                .frame(width: SavyLayout.accountMenuButtonSize, height: SavyLayout.accountMenuButtonSize)
                .background(backgroundColor, in: Circle())
                .overlay(Circle().stroke(borderColor, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("CowboyAI menu")
    }

    private var iconColor: Color {
        switch appearance {
        case .onDarkHero: .white.opacity(0.78)
        case .onWhiteHeader: CowboyTheme.bottomNavigationTan
        }
    }

    private var backgroundColor: Color {
        switch appearance {
        case .onDarkHero: .white.opacity(0.08)
        case .onWhiteHeader: CowboyTheme.navy
        }
    }

    private var borderColor: Color {
        switch appearance {
        case .onDarkHero: .white.opacity(0.12)
        case .onWhiteHeader: CowboyTheme.bottomNavigationTan.opacity(0.35)
        }
    }
}

/// SAVY's back button on a pushed page (ConnectionView.connectionHeader).
struct SavyBackButton: View {
    @Environment(\.dismiss) private var dismiss
    var onDarkBackground = false

    var body: some View {
        Button {
            dismiss()
        } label: {
            Image(systemName: "chevron.left")
                .font(.system(size: 21, weight: .bold))
                .foregroundStyle(onDarkBackground ? .white : CowboyTheme.red)
                .frame(width: 48, height: 48)
                .overlay {
                    Circle().stroke((onDarkBackground ? Color.white : CowboyTheme.red).opacity(0.85), lineWidth: 1)
                }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Back")
    }
}

enum SavyFabMenuMotion {
    static let open = Animation.spring(response: 0.34, dampingFraction: 0.72)
    static let close = Animation.spring(response: 0.3, dampingFraction: 0.8)
}

enum CowboyCaptureKind: String {
    case reminder, action, question, calendar
    var menuTitle: String {
        switch self { case .reminder: "Reminder"; case .action: "Action"; case .question: "Question"; case .calendar: "Calendar event" }
    }
    var fabMenuSymbolName: String {
        switch self { case .reminder: "bell.fill"; case .action: "bolt.fill"; case .question: "questionmark.bubble.fill"; case .calendar: "calendar" }
    }
}

struct SavyBottomNavigationBar: View {
    @Binding var selection: AppTab
    @Binding var isRadialMenuPresented: Bool
    @State private var highlightedCaptureKind: CowboyCaptureKind?
    let onSelectCaptureKind: (CowboyCaptureKind) -> Void

    @State private var draggingFab = false
    @State private var menuWasOpenAtStart = false

    private let barBackground = SavyTheme.bottomNavTan
    private let inactiveColor = Color(red: 0.34, green: 0.27, blue: 0.21).opacity(0.68)
    private let navyTopBandHeight: CGFloat = 24
    private var topBandColor: Color {
        selection == .now ? SavyTheme.deepNavy : SavyTheme.pageBackground
    }

    var body: some View {
        VStack(spacing: 0) {
            topBandColor
                .frame(height: navyTopBandHeight)

            ZStack(alignment: .top) {
                barBackground

                HStack(alignment: .center, spacing: 0) {
                    ForEach([AppTab.now, .reminders]) { section in
                        navigationButton(for: section)
                    }

                    Spacer()
                        .frame(maxWidth: .infinity)

                    ForEach([AppTab.actions, .calendar]) { section in
                        navigationButton(for: section)
                    }
                }
                .padding(.horizontal, RootHomeLayout.bottomNavigationHorizontalPadding)
                .frame(maxWidth: SavyWideLayout.navigationMaximumWidth)
                .frame(maxHeight: .infinity, alignment: .top)

                ZStack {
                    if isRadialMenuPresented {
                        // Four doors on one arc, left to right: Reminder, Action, Question, Calendar.
                        fabOption(.reminder).offset(x: -92, y: -62)
                        fabOption(.action).offset(x: -40, y: -122)
                        fabOption(.question).offset(x: 40, y: -122)
                        fabOption(.calendar).offset(x: 92, y: -62)
                    }

                    captureFab
                        .offset(y: -22)
                }
            }
            .frame(height: RootHomeLayout.bottomNavigationHeight - navyTopBandHeight)
        }
        .frame(height: RootHomeLayout.bottomNavigationHeight)
        .background(alignment: .top) {
            topBandColor
                .frame(
                    height: RootHomeLayout.bottomNavNavyRiserHeight + RootHomeLayout.bottomNavigationTopPadding
                )
                .offset(
                    y: -(RootHomeLayout.bottomNavNavyRiserHeight + RootHomeLayout.bottomNavigationTopPadding)
                )
        }
        .background(barBackground.ignoresSafeArea(edges: .bottom))
        .animation(SavyFabMenuMotion.open, value: isRadialMenuPresented)
    }

    private var captureFab: some View {
        borderedSymbol(isRadialMenuPresented ? "xmark" : "bolt.fill")
            .frame(
                width: RootHomeLayout.floatingCaptureSize,
                height: RootHomeLayout.floatingCaptureSize
            )
            .background(RootHomeLayout.floatingCaptureBackground, in: Circle())
            .shadow(color: .black.opacity(0.3), radius: 12, y: 6)
            .contentShape(Circle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { value in
                        if !draggingFab {
                            draggingFab = true
                            menuWasOpenAtStart = isRadialMenuPresented
                            if !isRadialMenuPresented {
                                SavyHapticFeedback.menuOpen()
                                withAnimation(SavyFabMenuMotion.open) {
                                    isRadialMenuPresented = true
                                }
                            }
                        }

                        let target = targetKind(for: value.translation)
                        if target != highlightedCaptureKind {
                            highlightedCaptureKind = target
                            if target != nil {
                                SavyHapticFeedback.selection()
                            }
                        }
                    }
                    .onEnded { _ in
                        if let selected = highlightedCaptureKind {
                            SavyHapticFeedback.primaryImpact()
                            withAnimation(SavyFabMenuMotion.close) {
                                onSelectCaptureKind(selected)
                            }
                        } else if menuWasOpenAtStart {
                            SavyHapticFeedback.menuClose()
                            withAnimation(SavyFabMenuMotion.close) {
                                dismissRadialMenu()
                            }
                        }

                        draggingFab = false
                        highlightedCaptureKind = nil
                    }
            )
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(
                isRadialMenuPresented
                    ? "Close quick entry menu"
                    : "Open quick entry menu"
            )
            .accessibilityIdentifier("chargeFab")
            .accessibilityAddTraits(.isButton)
            .accessibilityAction { withAnimation(SavyFabMenuMotion.open) { isRadialMenuPresented.toggle() } }
    }

    private func fabOption(_ kind: CowboyCaptureKind) -> some View {
        let isHighlighted = highlightedCaptureKind == kind

        return Button {
            SavyHapticFeedback.primaryImpact()
            withAnimation(SavyFabMenuMotion.close) {
                onSelectCaptureKind(kind)
            }
        } label: {
            VStack(spacing: 5) {
                Image(systemName: kind.fabMenuSymbolName)
                    .font(.system(size: RootHomeLayout.radialMenuIconSize, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(
                        width: RootHomeLayout.radialMenuButtonSize,
                        height: RootHomeLayout.radialMenuButtonSize
                    )
                    .background(
                        isHighlighted ? SavyTheme.crimson : Brand.nearBlack,
                        in: Circle()
                    )
                    .overlay(
                        Circle()
                            .stroke(
                                .white.opacity(isHighlighted ? 0.9 : 0.15),
                                lineWidth: 1.5
                            )
                    )
                    .scaleEffect(isHighlighted ? 1.15 : 1)

                Text(kind.menuTitle)
                    .font(.system(size: RootHomeLayout.radialMenuLabelSize, weight: .heavy))
                    .foregroundStyle(SavyTheme.crimson)
            }
            .shadow(color: .black.opacity(0.3), radius: 8, y: 4)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(kind.menuTitle)
    }

    private func borderedSymbol(_ name: String) -> some View {
        ZStack {
            Image(systemName: name)
                .font(.system(size: RootHomeLayout.floatingCaptureSymbolOuterSize, weight: .bold))
                .foregroundStyle(.black)
            Image(systemName: name)
                .font(.system(size: RootHomeLayout.floatingCaptureSymbolInnerSize, weight: .bold))
                .foregroundStyle(.white)
        }
    }

    private func dismissRadialMenu() {
        isRadialMenuPresented = false
        highlightedCaptureKind = nil
    }

    private func targetKind(for translation: CGSize) -> CowboyCaptureKind? {
        guard hypot(translation.width, translation.height) > 30 else { return nil }
        let angle = atan2(-translation.height, translation.width) * 180 / .pi
        if angle >= 90 && angle < 135 { return .action }
        if angle >= 45 && angle < 90 { return .question }
        if angle >= -45 && angle < 45 { return .calendar }
        if angle >= 135 || angle < -135 { return .reminder }
        return nil
    }

    private func navigationButton(for section: AppTab) -> some View {
        let isActive = selection == section

        return Button {
            SavyHapticFeedback.selection()
            selection = section
            withAnimation(SavyFabMenuMotion.close) {
                dismissRadialMenu()
            }
        } label: {
            VStack(spacing: RootHomeLayout.bottomNavigationIconLabelSpacing) {
                Image(systemName: section.symbolName)
                    .font(.system(size: RootHomeLayout.bottomNavigationIconSize, weight: .regular))

                Text(section.title)
                    .font(.system(size: RootHomeLayout.bottomNavigationLabelSize, weight: isActive ? .bold : .semibold))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            }
            .padding(.top, RootHomeLayout.bottomNavigationTopPadding)
            .padding(.bottom, RootHomeLayout.bottomNavigationBottomPadding)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            .foregroundStyle(isActive ? SavyTheme.crimson : inactiveColor)
            .contentShape(Rectangle())
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .buttonStyle(.plain)
        .accessibilityLabel(section.title)
        .accessibilityIdentifier("tab-\(section.rawValue)")
    }
}


extension RecentItem {
    var dateLabel: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d · h:mm a"
        return formatter.string(from: Date(timeIntervalSince1970: finished)).uppercased()
    }
}
