import SwiftUI

/// One of his three lines as its own page: SAVY's section page (ConnectionView), listing the past answers under it.
struct CategoryPage: View {
    var model: AskModel
    let category: Category
    let openAnswer: (String) -> Void

    private var items: [RecentItem] { model.recent(in: category) }

    var body: some View {
        GeometryReader { proxy in
            ScrollView {
                VStack(spacing: 0) {
                    header(topInset: proxy.safeAreaInsets.top)
                    list
                }
            }
            .ignoresSafeArea(edges: .top)
        }
        .background(CowboyTheme.navy.ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
        .toolbar(.hidden, for: .navigationBar)
        .accessibilityIdentifier("categoryPage-\(category.rawValue)")
    }

    private func header(topInset: CGFloat) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            SavyBackButton()

            Text(category.title)
                .font(SavyLayout.displaySerif(40, weight: .regular))
                .foregroundStyle(CowboyTheme.ink)
                .lineLimit(3)
                .minimumScaleFactor(0.72)
                .padding(.top, 24)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, SavyLayout.horizontalPadding)
        .padding(.top, topInset + 18)
        .padding(.bottom, 30)
        .background(CowboyTheme.bottomNavigationTan)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(CowboyTheme.red)
                .frame(height: 2)
        }
    }

    private var list: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("PAST RESULTS")
                    .font(.system(size: 13, weight: .heavy))
                    .tracking(2.6)
                    .foregroundStyle(CowboyTheme.bottomNavigationTan)
                Spacer()
                Text("\(items.count)")
                    .font(.system(size: 13, weight: .heavy))
                    .foregroundStyle(CowboyTheme.bottomNavigationTan.opacity(0.72))
            }
            .padding(.horizontal, 2)
            .padding(.bottom, 12)

            if items.isEmpty {
                Text("Your past results will appear here.")
                    .font(CowboyTheme.carouselSerif(22))
                    .foregroundStyle(CowboyTheme.bottomNavigationTan)
            } else {
                VStack(spacing: 11) {
                    ForEach(items) { item in
                        Button {
                            openAnswer(item.id)
                        } label: {
                            BandCard(item: item)
                        }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("categoryCard-\(item.id)")
                    }
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 22)
        .padding(.bottom, 48)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CowboyTheme.navy)
    }
}

/// SAVY's band card (ConnectionBandCard, the minimal one).
private struct BandCard: View {
    let item: RecentItem

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(item.question)
                .font(SavyLayout.displaySerif(25, weight: .regular))
                .foregroundStyle(CowboyTheme.navy)
                .lineLimit(2)
                .minimumScaleFactor(0.82)
                .multilineTextAlignment(.leading)

            Rectangle()
                .fill(CowboyTheme.red)
                .frame(width: 36, height: 2)

            Text(item.dateLabel)
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(CowboyTheme.navy.opacity(0.72))

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .frame(height: 124)
        .background(CowboyTheme.bottomNavigationTan)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        }
    }
}
