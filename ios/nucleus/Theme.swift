import SwiftUI

enum CowboyTheme {
    static let editorialSerifName = "Bodoni 72 Oldstyle"
    static let carouselSerifName = "TimesNewRomanPSMT"
    static let navy = Color(red: 8 / 255, green: 23 / 255, blue: 45 / 255)
    static let navyRaised = Color(red: 10 / 255, green: 31 / 255, blue: 54 / 255)
    static let cream = Color(red: 243 / 255, green: 234 / 255, blue: 213 / 255)
    static let tan = Color(red: 213 / 255, green: 193 / 255, blue: 148 / 255)
    static let red = Color(red: 230 / 255, green: 14 / 255, blue: 68 / 255)
    static let cardRed = Color(red: 176 / 255, green: 1 / 255, blue: 36 / 255)
    static let bottomNavigationTan = Color(red: 0.80, green: 0.70, blue: 0.58)
    static let navigationInactive = Color(red: 0.34, green: 0.27, blue: 0.21).opacity(0.68)
    static let green = Color(red: 54 / 255, green: 205 / 255, blue: 125 / 255)
    static let orange = Color(red: 241 / 255, green: 117 / 255, blue: 32 / 255)
    static let muted = Color.white.opacity(0.86)

    /// The same regular-weight editorial face used by Notorious Recall and SAVY.
    static func editorialSerif(
        _ size: CGFloat,
        relativeTo textStyle: Font.TextStyle
    ) -> Font {
        .custom(editorialSerifName, size: size, relativeTo: textStyle)
    }

    /// The same regular-weight reading face at a calmer body size.
    static func readingSerif(
        _ size: CGFloat,
        relativeTo textStyle: Font.TextStyle
    ) -> Font {
        .custom(editorialSerifName, size: size, relativeTo: textStyle)
    }

    /// SAVY's regular Times New Roman carousel title face.
    static func carouselSerif(_ size: CGFloat) -> Font {
        .custom(carouselSerifName, size: size)
    }
}

/// A quiet Ben-Day field borrowed from the Harness pop-art surface.
/// It is decorative texture, never status or data.
struct BenDayDotBackground: View {
    var body: some View {
        Canvas { context, size in
            context.fill(Path(CGRect(origin: .zero, size: size)), with: .color(.white))

            let spacing: CGFloat = 18
            let diameters: [CGFloat] = [2.4, 3.2, 4.6, 6.4, 8.2, 6.4, 4.6, 3.2]
            var row = 0
            var y: CGFloat = 8

            while y < size.height {
                let offset = row.isMultiple(of: 2) ? CGFloat.zero : spacing / 2
                var column = 0
                var x = 8 + offset
                while x < size.width {
                    let diameter = diameters[(column + row * 2) % diameters.count]
                    let dot = CGRect(
                        x: x - diameter / 2,
                        y: y - diameter / 2,
                        width: diameter,
                        height: diameter
                    )
                    context.fill(Path(ellipseIn: dot), with: .color(CowboyTheme.navy.opacity(0.10)))
                    x += spacing
                    column += 1
                }
                y += spacing
                row += 1
            }
        }
        .accessibilityHidden(true)
    }
}

struct Panel<Content: View>: View {
    let accent: Color
    @ViewBuilder let content: Content

    init(accent: Color = CowboyTheme.red, @ViewBuilder content: () -> Content) {
        self.accent = accent
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            content
        }
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.white)
            .overlay(alignment: .leading) {
                Rectangle().fill(accent).frame(width: 3)
            }
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(accent.opacity(0.35), lineWidth: 1)
            }
    }
}

struct Kicker: View {
    let text: String

    var body: some View {
        Text(text)
            .font(CowboyTheme.editorialSerif(16, relativeTo: .body))
            .foregroundStyle(CowboyTheme.navy)
    }
}

extension View {
    func cowboyBackground() -> some View {
        background(CowboyTheme.navy.ignoresSafeArea())
    }
}
