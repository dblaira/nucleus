import SwiftUI

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

