import Observation
import PhotosUI
import SwiftUI

/// Each screen's photo belongs only to this CowboyAI installation.
@Observable @MainActor
final class HomeAppearance {
    private(set) var images: [AppTab: UIImage] = [:]
    var errorMessage: String?

    init() {
        for screen in AppTab.allCases {
            if let image = UIImage(contentsOfFile: fileURL(for: screen).path) {
                images[screen] = image
            }
        }
    }

    var background: Image {
        customBackground(for: .now) ?? Image("HomeMountainLandscape")
    }

    func customBackground(for screen: AppTab) -> Image? {
        images[screen].map { Image(uiImage: $0) }
    }

    func previewBackground(for screen: AppTab) -> Image? {
        if let custom = customBackground(for: screen) { return custom }
        switch screen {
        case .now: return Image("HomeMountainLandscape")
        case .reminders: return Image("RemindersBeachLandscape")
        case .actions: return Image("ActionsCarLandscape")
        case .calendar: return nil
        }
    }

    private func fileURL(for screen: AppTab) -> URL {
        // Preserve the photo already selected on Now.
        CowboyStorage.file(screen == .now ? "home-background.image" : "\(screen.rawValue)-background.image")
    }

    func save(_ data: Data, for screen: AppTab) {
        guard let decoded = UIImage(data: data) else {
            errorMessage = "This photo could not be opened. Your previous photo is still saved."
            return
        }
        do {
            let fileURL = fileURL(for: screen)
            try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            try data.write(to: fileURL, options: .atomic)
            images[screen] = decoded
            errorMessage = nil
        } catch {
            errorMessage = "The photo could not be saved. Your previous photo is still saved."
        }
    }
}

struct HomeBackgroundSettings: View {
    let screen: AppTab
    @Environment(HomeAppearance.self) private var appearance
    @Environment(\.dismiss) private var dismiss
    @State private var selection: PhotosPickerItem?
    @State private var isLoading = false

    var body: some View {
        let pickerTitle = isLoading ? "Opening photo…" : "Choose photo"
        NavigationStack {
            VStack(spacing: 24) {
                Text(screen.title).font(.headline).foregroundStyle(.white)
                Group {
                    if let background = appearance.previewBackground(for: screen) {
                        background.resizable().scaledToFill()
                    } else {
                        Image(systemName: "photo")
                            .font(.system(size: 56))
                            .foregroundStyle(.white.opacity(0.6))
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    }
                }
                .frame(height: 280).frame(maxWidth: .infinity).clipped()
                .clipShape(RoundedRectangle(cornerRadius: 12))
                PhotosPicker(selection: $selection, matching: .images) {
                    Label(pickerTitle, systemImage: "photo")
                        .frame(maxWidth: .infinity).padding(16)
                        .background(CowboyTheme.red, in: RoundedRectangle(cornerRadius: 12))
                        .foregroundStyle(.white)
                }
                .disabled(isLoading)
                .accessibilityIdentifier(screen == .now ? "chooseHomePhoto" : "choose\(screen.title)Photo")
                if let message = appearance.errorMessage { Text(message).foregroundStyle(.white) }
                Spacer()
            }
            .padding(24)
            .background(CowboyTheme.navy.ignoresSafeArea())
            .navigationTitle("Background photo")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { dismiss() }.tint(.white) } }
            .task(id: selection) {
                guard let selection else { return }
                isLoading = true
                defer { isLoading = false }
                do {
                    if let data = try await selection.loadTransferable(type: Data.self) {
                        appearance.save(data, for: screen)
                    }
                } catch { appearance.errorMessage = "This photo could not be opened. Your previous photo is still saved." }
            }
        }
    }
}
