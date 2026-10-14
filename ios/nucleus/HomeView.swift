import SwiftUI

private struct HomeConversation: Identifiable {
    let id: String
    let answer: String
    let origin: ConversationOrigin?
    let metadata: Reminder
    var pinned: Bool { metadata.pinned }
}

struct HomeView: View {
    var model: AskModel
    @Environment(HomeAppearance.self) private var appearance
    let openAnswer: (String) -> Void
    let openCategory: (Category) -> Void
    let openConnection: () -> Void
    let openOrigin: (ConversationOrigin) -> Void
    let openRoute: () -> Void
    let openAppearance: () -> Void

    private var cards: [HomeConversation] {
        let records = model.archive.recentRecords(for: NucleusAPI.base, recent: model.recent)
        var values = records.map { record in
            HomeConversation(id: record.latest.questionID, answer: record.displayed.answerPreview,
                             origin: record.displayed, metadata: model.archive.metadata(for: record.displayed))
        }
        let savedIDs = Set(values.map(\.id))
        for item in model.recent where !savedIDs.contains(item.id) {
            var metadata = Reminder()
            metadata.title = item.question
            metadata.createdAt = Date(timeIntervalSince1970: item.finished)
            // No fabricated response or metadata while the saved response is loading.
            values.append(HomeConversation(id: item.id, answer: "", origin: nil, metadata: metadata))
        }
        let dates = Dictionary(model.recent.map { ($0.id, $0.finished) }, uniquingKeysWith: max)
        return values.sorted {
            let left = dates[$0.id] ?? $0.metadata.createdAt.timeIntervalSince1970
            let right = dates[$1.id] ?? $1.metadata.createdAt.timeIntervalSince1970
            return left == right ? $0.id < $1.id : left > right
        }
    }

    private var carouselCards: [HomeConversation] {
        let values = cards
        let pins = model.archive.records(for: NucleusAPI.base).filter { $0.pinned != nil }.map { $0.latest.questionID }
        let byID = Dictionary(values.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        let pinnedIDs = Set(pins)
        // Keep all history available here, with saved pins at the front.
        return pins.compactMap { byID[$0] } + values.filter { !pinnedIDs.contains($0.id) }
    }

    var body: some View {
        GeometryReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    header(topInset: proxy.safeAreaInsets.top)
                    VStack(alignment: .leading, spacing: 0) {
                        carousel
                        Color.clear.frame(height: 28).accessibilityHidden(true)
                        recentResponses
                        categories
                    }
                    .padding(.bottom, 40)
                    .frame(maxWidth: .infinity,
                           minHeight: max(0, proxy.size.height + proxy.safeAreaInsets.top - SavyLayout.heroHeight),
                           alignment: .top)
                    .background {
                        GeometryReader { landscape in
                            appearance.background
                                .resizable()
                                .scaledToFill()
                                .frame(width: landscape.size.width,
                                       height: proxy.size.height + proxy.safeAreaInsets.top)
                                .clipped()
                                .offset(y: max(0, -landscape.frame(in: .named("homeLandscapeScroll")).minY))
                        }
                        .clipped()
                        .allowsHitTesting(false)
                        .accessibilityHidden(true)
                    }
                }.padding(.bottom, 24)
            }
            .coordinateSpace(name: "homeLandscapeScroll")
            .ignoresSafeArea(edges: .top)
            .refreshable { await model.loadRecent() }
            .accessibilityIdentifier("editorialHomeScroll")
        }
        .background(CowboyTheme.navy.ignoresSafeArea())
    }

    private func header(topInset: CGFloat) -> some View {
        HStack(alignment: .top) {
            Text("CowboyAI")
                .font(CowboyTheme.editorialSerif(56, relativeTo: .largeTitle))
                .foregroundStyle(.white)
                .accessibilityLabel("Cowboy AI")
            Spacer()
            SavyMenuButton(openConnection: openConnection, openRoute: openRoute, openAppearance: openAppearance)
                .padding(.top, 8)
        }
        .padding(.horizontal, SavyLayout.horizontalPadding)
        .padding(.top, topInset + SavyLayout.heroContentTopPadding)
        .frame(height: SavyLayout.heroHeight, alignment: .topLeading)
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .background(alignment: .topLeading) {
            ZStack(alignment: .topLeading) {
                CowboyTheme.navy
                Image("CowboyHat")
                    .renderingMode(.template)
                    .resizable()
                    .scaledToFit()
                    .foregroundStyle(.white.opacity(0.18))
                    .frame(width: 220, height: 220)
                    .offset(x: 30, y: topInset - 18)
                    .allowsHitTesting(false)
                    .accessibilityHidden(true)
            }
        }
        .clipped()
        .overlay(alignment: .bottom) { Rectangle().fill(CowboyTheme.red).frame(height: 2) }
    }

    private var carousel: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(alignment: .top, spacing: 16) {
                if carouselCards.isEmpty {
                    Text(model.loadingRecent ? "Opening conversations…" : "Use the lightning button to ask CowboyAI a question.")
                        .font(.system(size: 14)).foregroundStyle(SavyTheme.deepNavy)
                        .padding(20).frame(width: RootHomeLayout.carouselCardWidth, alignment: .leading)
                        .background(Brand.card, in: RoundedRectangle(cornerRadius: 8))
                        .accessibilityIdentifier("emptyConversationCarousel")
                }
                ForEach(carouselCards) { item in
                    Button { open(item) } label: {
                        SavyReminderBandCard(
                            reminder: item.metadata,
                            bg: Brand.card,
                            fg: SavyTheme.deepNavy,
                            accent: Brand.crimson,
                            detail: .full,
                            showsSchedule: false,
                            showsCompleteMetadata: false,
                            previewHeight: RootHomeLayout.carouselCardHeight,
                            carouselDetails: SavyCarouselDetail.values(for: item.metadata)
                        )
                        .frame(width: RootHomeLayout.carouselCardWidth, alignment: .topLeading)
                    }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("latest-\(item.id)")
                        .conversationActions(for: item.origin)
                }
            }
            .padding(.horizontal, RootHomeLayout.carouselHorizontalPadding)
            .padding(.top, RootHomeLayout.carouselTopPadding)
            .padding(.bottom, RootHomeLayout.carouselBottomPadding)
        }.accessibilityIdentifier("latestCarousel")
    }

    private var recentResponses: some View {
        LazyVStack(alignment: .leading, spacing: 12) {
            Text("Recent responses")
                .font(CowboyTheme.carouselSerif(25)).foregroundStyle(.white)
                .padding(12).frame(maxWidth: .infinity, alignment: .leading)
                .background(CowboyTheme.navy.opacity(0.9), in: RoundedRectangle(cornerRadius: 8))
            if cards.isEmpty {
                Text(model.loadingRecent ? "Opening conversations…" : "Use the lightning button to ask CowboyAI a question.")
                    .foregroundStyle(CowboyTheme.ink).padding(20)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.white, in: RoundedRectangle(cornerRadius: 8))
            }
            if let problem = model.recentProblem {
                Text(problem).font(.callout).foregroundStyle(CowboyTheme.ink).padding(16)
                    .background(CowboyTheme.tan, in: RoundedRectangle(cornerRadius: 8))
            }
            ForEach(cards) { item in
                Button { open(item) } label: {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(item.metadata.title).font(.system(size: 14, weight: .semibold))
                            .lineLimit(2).foregroundStyle(.white.opacity(0.85))
                        Text(item.answer.isEmpty ? "Open the conversation" : item.answer)
                            .font(CowboyTheme.carouselSerif(22)).lineLimit(4).foregroundStyle(.white)
                            .accessibilityIdentifier("recentResponse-\(item.id)")
                        HStack {
                            if item.pinned { Label("Pinned", systemImage: "pin.fill") }
                            Spacer()
                            Image(systemName: "chevron.right")
                        }.font(.system(size: 11, weight: .semibold)).foregroundStyle(.white.opacity(0.8))
                    }
                    .multilineTextAlignment(.leading).padding(18)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(CowboyTheme.red, in: RoundedRectangle(cornerRadius: 8))
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("recent-\(item.id)")
                .conversationActions(for: item.origin)
            }
        }.padding(.horizontal, 16).padding(.bottom, 20)
    }

    private var categories: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(Category.allCases) { category in
                Button { openCategory(category) } label: {
                    HStack {
                        Text(category.eyebrow).font(.system(size: 12, weight: .heavy))
                        Spacer()
                        Text("\(model.recent(in: category).count)")
                        Image(systemName: "chevron.right")
                    }.foregroundStyle(CowboyTheme.ink).padding(15).background(.white, in: RoundedRectangle(cornerRadius: 8))
                }.buttonStyle(.plain).accessibilityIdentifier("homeCategory-\(category.rawValue)")
            }
        }.padding(.horizontal, 16)
    }

    private func open(_ item: HomeConversation) {
        if item.pinned, let origin = item.origin { openOrigin(origin) }
        else { openAnswer(item.id) }
    }

}
