import SwiftUI

/// The CowboyAI app's Route screen (Cowboyai/authority-hub/ios/CowboyAI/RouteView.swift) showing nucleus's seven
/// steps for the question on Decide. Adam, 2026-09-12: nothing between the question and the answer, so the steps
/// live here, under the page's own line.
struct RouteView: View {
    var model: AskModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("how long each step took")
                    .font(CowboyTheme.editorialSerif(29, relativeTo: .title))
                    .foregroundStyle(CowboyTheme.navy)

                if let current = model.current {
                    Text(current.question.question)
                        .font(CowboyTheme.readingSerif(18, relativeTo: .body))
                        .foregroundStyle(CowboyTheme.navy)
                        .lineSpacing(3)
                }

                route
            }
            .padding(20)
        }
        .background(Color.white)
    }

    private var route: some View {
        VStack(spacing: 0) {
            ForEach(Array(AskModel.stepNames.enumerated()), id: \.offset) { index, name in
                let step = model.current?.steps.first { $0.name == name }
                let running = step != nil && step?.finished == nil
                RouteNode(kicker: name.uppercased(), title: title(for: step), accent: accent(step))
                if index < AskModel.stepNames.count - 1 {
                    RouteConnector(color: step?.finished == nil ? CowboyTheme.tan : CowboyTheme.green)
                        .opacity(running ? 0.5 : 1)
                }
            }
        }
        .padding(16)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .stroke(CowboyTheme.red.opacity(0.5), lineWidth: 1)
        }
    }

    private func title(for step: AskResponse.Step?) -> String {
        guard let step else { return " " }
        let end = step.finished ?? Date().timeIntervalSince1970
        let seconds = String(format: "%.1f s", max(0, end - step.started))
        if let note = step.note, !note.isEmpty { return "\(seconds) · \(note)" }
        return seconds
    }

    private func accent(_ step: AskResponse.Step?) -> Color {
        guard let step else { return CowboyTheme.tan }
        return step.finished == nil ? CowboyTheme.red : CowboyTheme.green
    }
}

private struct RouteNode: View {
    let kicker: String
    let title: String
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(kicker)
                .font(CowboyTheme.editorialSerif(14, relativeTo: .footnote))
                .foregroundStyle(CowboyTheme.navy)
            Text(title)
                .font(CowboyTheme.editorialSerif(18, relativeTo: .body))
                .foregroundStyle(CowboyTheme.navy)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(15)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 13, style: .continuous)
                .stroke(accent.opacity(0.55), lineWidth: 1)
        }
    }
}

private struct RouteConnector: View {
    let color: Color

    var body: some View {
        VStack(spacing: 0) {
            Rectangle().fill(color).frame(width: 2, height: 20)
            Image(systemName: "arrowtriangle.down.fill")
                .font(.system(size: 11, weight: .regular))
                .foregroundStyle(color)
        }
        .accessibilityHidden(true)
    }
}
