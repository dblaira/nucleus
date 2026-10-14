import SwiftUI

@main
struct NucleusApp: App {
    @State private var model: AskModel

    init() {
        CowboyStorage.prepareForTesting()
        _model = State(initialValue: AskModel())
    }

    var body: some Scene {
        WindowGroup {
            RootView(model: model)
                .preferredColorScheme(.dark)
        }
    }
}
