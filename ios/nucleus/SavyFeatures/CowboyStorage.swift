import Foundation

enum CowboyRuntime {
    static var isTesting: Bool {
        #if DEBUG
        ProcessInfo.processInfo.arguments.contains("COWBOYAI_UI_TEST") || ProcessInfo.processInfo.environment["COWBOYAI_UI_TEST"] == "1"
        #else
        false
        #endif
    }
}

/// App-container files only. These never resolve SAVY containers, shared groups, or iCloud.
enum CowboyStorage {
    static var directory: URL {
        let root = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return root.appendingPathComponent(CowboyRuntime.isTesting ? "CowboyAI-UI-Tests" : "CowboyAI", isDirectory: true)
    }
    static func file(_ name: String) -> URL { directory.appendingPathComponent(name) }
    static func preferenceKey(_ key: String) -> String { CowboyRuntime.isTesting ? "cowboyai.ui-test." + key : key }

    static func prepareForTesting() {
        #if DEBUG
        guard CowboyRuntime.isTesting, ProcessInfo.processInfo.arguments.contains("COWBOYAI_UI_TEST_RESET"),
              directory.lastPathComponent == "CowboyAI-UI-Tests" else { return }
        try? FileManager.default.removeItem(at: directory)
        for key in UserDefaults.standard.dictionaryRepresentation().keys where key.hasPrefix("cowboyai.ui-test.") {
            UserDefaults.standard.removeObject(forKey: key)
        }
        #endif
    }
}
