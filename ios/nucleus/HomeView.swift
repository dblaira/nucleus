import SwiftUI

/// SAVY's home (EditorialHomeView): the wordmark hero, the carousel, then the sections under it. Here the carousel
/// is the latest answers and the sections are his three lines. Adam, 2026-09-14: "don't use greatest leverage above
/// the carousel ... just don't give them as much room as Savy gives ... all three options should be available to
/// press on".
struct HomeView: View {
    var model: AskModel
    let openAnswer: (String) -> Void
    let openCategory: (Category) -> Void
    let openConnection: () -> Void

    var body: some View {
        GeometryReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    header(topInset: proxy.safeAreaInsets.top)

                    carousel

                    ForEach(Category.allCases) { category in
                        Button {
                            openCategory(category)
                        } label: {
                            CategoryRow(category: category, count: model.recent(in: category).count)
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("homeCategory-\(category.rawValue)")
                    }
                }
                .padding(.bottom, 40)
            }
            .accessibilityIdentifier("editorialHomeScroll")
            .ignoresSafeArea(edges: .top)
            .refreshable { await model.loadRecent() }
        }
        .background(Color.white.ignoresSafeArea())
        .environment(\.colorScheme, .light)
    }

    private func header(topInset: CGFloat) -> some View {
        HStack(alignment: .top, spacing: 0) {
            // The name is Cowboy AI. It always was. Adam, 2026-09-14: "It's the name that we've always had."
            Text("Cowboy AI")
                .font(SavyLayout.displaySerif(SavyLayout.heroWordmarkFontSize, weight: .bold))
                .foregroundStyle(.white)
                .lineLimit(1)
                .minimumScaleFactor(0.85)

            Spacer(minLength: 0)

            SavyMenuButton(openConnection: openConnection)
                .padding(.top, SavyLayout.accountMenuHeroWordmarkOffset)
        }
        .padding(.horizontal, SavyLayout.horizontalPadding)
        .padding(.top, topInset + SavyLayout.heroContentTopPadding)
        .frame(maxWidth: .infinity, minHeight: SavyLayout.heroHeight, maxHeight: SavyLayout.heroHeight, alignment: .topLeading)
        .background(CowboyTheme.navy)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(CowboyTheme.red)
                .frame(height: SavyLayout.heroDividerHeight)
        }
    }

    /// The latest answers, in SAVY's home carousel (greatestLeverageSection without its title band).
    private var carousel: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 16) {
                ForEach(Array(model.recent.prefix(10).enumerated()), id: \.element.id) { index, item in
                    Button {
                        openAnswer(item.id)
                    } label: {
                        HomeFeedCard(item: item, alignment: index.isMultiple(of: 2) ? .leading : .center)
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("latest-\(item.id)")
                }
            }
            .padding(.horizontal, SavyLayout.carouselHorizontalPadding)
            .padding(.vertical, 16)
        }
        .accessibilityIdentifier("latestCarousel")
        .background(Color.white)
    }
}

/// SAVY's home carousel card (HomeFeedRowView).
private struct HomeFeedCard: View {
    let item: RecentItem
    let alignment: Alignment

    var body: some View {
        VStack(alignment: horizontalAlignment, spacing: 8) {
            Text(item.question)
                .font(CowboyTheme.carouselSerif(SavyLayout.carouselCardTitleFontSize))
                .lineLimit(3)
                .minimumScaleFactor(0.85)
                .foregroundStyle(CowboyTheme.ink)
                .frame(maxWidth: .infinity, alignment: alignment)

            Text(item.dateLabel)
                .font(.system(size: 12, weight: .heavy))
                .tracking(1.4)
                .foregroundStyle(CowboyTheme.red)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.horizontal, SavyLayout.pinnedEntryTrailingInset)
        .padding(.vertical, 16)
        .frame(width: SavyLayout.carouselCardWidth, height: SavyLayout.carouselCardHeight, alignment: .topLeading)
        .background(CowboyTheme.cream, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(Color.black.opacity(0.08), lineWidth: 1)
        }
    }

    private var horizontalAlignment: HorizontalAlignment {
        alignment == .center ? .center : .leading
    }
}

/// SAVY's home section row (HomeContentSectionView), with less room so all three fit on the first screen.
private struct CategoryRow: View {
    let category: Category
    let count: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(category.eyebrow)
                .font(.system(size: 12, weight: .heavy))
                .tracking(1.8)
                .foregroundStyle(CowboyTheme.red)

            Text(category.title)
                .font(CowboyTheme.carouselSerif(22))
                .lineSpacing(1)
                .foregroundStyle(CowboyTheme.ink)
                .lineLimit(2)
                .minimumScaleFactor(0.78)
                .fixedSize(horizontal: false, vertical: true)

            Text("\(count) ITEMS")
                .font(.system(size: 12, weight: .heavy))
                .tracking(1.4)
                .foregroundStyle(Color.black.opacity(0.45))
        }
        .padding(.horizontal, SavyLayout.horizontalPadding)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .background(Color.white)
        .contentShape(Rectangle())
    }
}
