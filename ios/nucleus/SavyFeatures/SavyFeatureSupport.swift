import SwiftUI
import UIKit

enum SavyHapticFeedback {
    static let primaryImpactIntensity: CGFloat = 1.0

    @MainActor
    static func primaryImpact() {
        let generator = UIImpactFeedbackGenerator(style: .heavy)
        generator.prepare()
        generator.impactOccurred(intensity: primaryImpactIntensity)
    }

    @MainActor
    static func menuOpen() {
        let generator = UIImpactFeedbackGenerator(style: .medium)
        generator.prepare()
        generator.impactOccurred(intensity: 0.92)
    }

    @MainActor
    static func menuClose() {
        let generator = UIImpactFeedbackGenerator(style: .light)
        generator.prepare()
        generator.impactOccurred(intensity: 0.78)
    }

    @MainActor
    static func selection() {
        let generator = UISelectionFeedbackGenerator()
        generator.prepare()
        generator.selectionChanged()
    }
}


extension View {
    func savyHeaderPageContent(minHeight: CGFloat) -> some View {
        frame(maxWidth: .infinity, minHeight: minHeight, alignment: .top)
            .background(SavyTheme.contentBackground)
    }
    func savyHeaderOverscrollCapture(_ screen: String) -> some View { self }
}

enum RootHomeLayout {
    static let leverageGridColumnCount = 2
    static let leverageGridColumns = Array(
        repeating: GridItem(.flexible(), spacing: 17),
        count: leverageGridColumnCount
    )
    static let horizontalPadding: CGFloat = 24
    static let heroTopPadding: CGFloat = 0
    static let heroHeight: CGFloat = 204
    static let heroContentTopPadding: CGFloat = 34
    static let heroDividerHeight: CGFloat = 1
    static let heroWordmarkFontSize: CGFloat = 64
    static let carouselHorizontalPadding: CGFloat = 2
    static let carouselTopPadding: CGFloat = 24
    static let carouselBottomPadding: CGFloat = 24
    static let carouselCardWidth: CGFloat = 282
    /// Fits a two-line title and up to three rows of readable 24-point detail pills.
    static let carouselCardHeight: CGFloat = 182
    static let carouselCardTitleFontSize: CGFloat = 24
    static let latestSectionBandHeight: CGFloat = 80
    static let pinnedEntryRowHeight: CGFloat = 96
    static let pinnedEntryTrailingInset: CGFloat = 17
    static let pinnedEntryFontSize: CGFloat = 24
    static let homeBandCardSpacing: CGFloat = 10
    static let homeBandTopPadding: CGFloat = 14
    /// Leave the summit visible between the carousel and the destination cards.
    static let homeLandscapeRevealHeight: CGFloat = 80
    static let homeBandBottomPadding: CGFloat = 16
    static let homeBandHorizontalPadding: CGFloat = 16
    static let homeBandCardCornerRadius: CGFloat = 8
    static let bottomNavigationHeight: CGFloat = 128
    /// Navy band painted above the tan bar (FAB overflow zone); does not add layout height.
    static let bottomNavNavyRiserHeight: CGFloat = 44
    static let bottomNavigationTopPadding: CGFloat = 8
    static let bottomNavigationBottomPadding: CGFloat = 28
    static let bottomNavigationIconSize: CGFloat = 25
    static let bottomNavigationIconWeight: Font.Weight = .regular
    static let bottomNavigationLabelSize: CGFloat = 15
    static let bottomNavigationIconLabelSpacing: CGFloat = 7
    static let bottomNavigationHorizontalPadding: CGFloat = 0
    static let floatingCaptureSize: CGFloat = 64
    static let floatingCaptureSymbolOuterSize: CGFloat = 30
    static let floatingCaptureSymbolInnerSize: CGFloat = 25
    static var floatingCaptureBackground: Color { SavyTheme.crimson }
    /// FAB center sits on the top edge of the bottom navigation bar.
    static var floatingCaptureCenterAboveBottom: CGFloat {
        bottomNavigationHeight
    }
    static var radialMenuBottomPadding: CGFloat {
        floatingCaptureCenterAboveBottom + (floatingCaptureSize / 2) + 10
    }
    static let radialMenuButtonSize: CGFloat = 56
    static let radialMenuIconSize: CGFloat = 20
    static let radialMenuLabelSize: CGFloat = 12
    static let accountMenuSymbolName = "line.3.horizontal"
    static let accountMenuButtonSize: CGFloat = 42
    static let accountMenuTopPadding: CGFloat = 88

    /// Nudges the menu down to the optical center of the SAVY wordmark cap height.
    static var accountMenuHeroWordmarkOffset: CGFloat {
        ((heroWordmarkFontSize - accountMenuButtonSize) * 0.42) + 5
    }
}

enum SavyTheme {
    static let deepNavy = CowboyTheme.navy
    static let pageBackground = CowboyTheme.navy
    static let contentBackground = Color.white
    static let headerDivider = Color.white
    static let crimson = CowboyTheme.red
    static let bottomNavTan = CowboyTheme.bottomNavigationTan
    static let secondaryText = Color.black.opacity(0.62)
    static let tertiaryText = Color.black.opacity(0.45)
}
