import SwiftUI

@main
struct NucleusApp: App {
    @State private var model = AskModel()

    var body: some Scene {
        WindowGroup {
            RootView(model: model)
                .preferredColorScheme(.dark)
        }
    }
}
