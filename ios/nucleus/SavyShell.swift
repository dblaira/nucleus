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

    var body: some View {
        Menu {
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
        .accessibilityLabel("nucleus menu")
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

    var body: some View {
        Button {
            dismiss()
        } label: {
            Image(systemName: "chevron.left")
                .font(.system(size: 21, weight: .bold))
                .foregroundStyle(CowboyTheme.red)
                .frame(width: 48, height: 48)
                .overlay {
                    Circle().stroke(CowboyTheme.red.opacity(0.85), lineWidth: 1)
                }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Back")
    }
}

/// SAVY's bottom bar (SavyBottomNavigationBar) with the bolt; the bolt opens the question form.
struct SavyBottomNavigationBar: View {
    @Binding var selection: AppTab
    let openComposer: () -> Void

    private let barBackground = CowboyTheme.bottomNavigationTan
    private let inactiveColor = CowboyTheme.navigationInactive
    private let navyTopBandHeight: CGFloat = 24

    var body: some View {
        VStack(spacing: 0) {
            CowboyTheme.navy
                .frame(height: navyTopBandHeight)

            ZStack(alignment: .top) {
                barBackground

                HStack(alignment: .center, spacing: 0) {
                    navigationButton(for: .now)

                    Spacer()
                        .frame(maxWidth: .infinity)

                    navigationButton(for: .route)
                }
                .frame(maxHeight: .infinity, alignment: .top)

                Button(action: openComposer) {
                    borderedSymbol("bolt.fill")
                        .frame(width: SavyLayout.floatingCaptureSize, height: SavyLayout.floatingCaptureSize)
                        .background(CowboyTheme.red, in: Circle())
                        .shadow(color: .black.opacity(0.3), radius: 12, y: 6)
                }
                .buttonStyle(.plain)
                .offset(y: -22)
                .accessibilityLabel("Add a question")
                .accessibilityIdentifier("chargeFab")
            }
            .frame(height: SavyLayout.bottomNavigationHeight - navyTopBandHeight)
        }
        .frame(height: SavyLayout.bottomNavigationHeight)
        .background(alignment: .top) {
            CowboyTheme.navy
                .frame(height: SavyLayout.bottomNavNavyRiserHeight + SavyLayout.bottomNavigationTopPadding)
                .offset(y: -(SavyLayout.bottomNavNavyRiserHeight + SavyLayout.bottomNavigationTopPadding))
        }
        .background(barBackground.ignoresSafeArea(edges: .bottom))
    }

    private func borderedSymbol(_ name: String) -> some View {
        ZStack {
            Image(systemName: name)
                .font(.system(size: SavyLayout.floatingCaptureSymbolOuterSize, weight: .bold))
                .foregroundStyle(.black)
            Image(systemName: name)
                .font(.system(size: SavyLayout.floatingCaptureSymbolInnerSize, weight: .bold))
                .foregroundStyle(.white)
        }
    }

    private func navigationButton(for tab: AppTab) -> some View {
        let isActive = selection == tab

        return Button {
            selection = tab
        } label: {
            VStack(spacing: SavyLayout.bottomNavigationIconLabelSpacing) {
                Image(systemName: tab.symbolName)
                    .font(.system(size: SavyLayout.bottomNavigationIconSize, weight: .regular))

                Text(tab.title)
                    .font(.system(size: SavyLayout.bottomNavigationLabelSize, weight: isActive ? .bold : .semibold))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
            }
            .padding(.top, SavyLayout.bottomNavigationTopPadding)
            .padding(.bottom, SavyLayout.bottomNavigationBottomPadding)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            .foregroundStyle(isActive ? CowboyTheme.red : inactiveColor)
            .contentShape(Rectangle())
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .buttonStyle(.plain)
        .accessibilityLabel(tab.title)
    }
}

extension RecentItem {
    var dateLabel: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d · h:mm a"
        return formatter.string(from: Date(timeIntervalSince1970: finished)).uppercased()
    }
}
