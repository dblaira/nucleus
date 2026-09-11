import Foundation
import FoundationModels
@main struct Tiny {
    static func main() async {
        let pcc = PrivateCloudComputeLanguageModel()
        do { let s = LanguageModelSession(model: pcc); let r = try await s.respond(to: "Reply with exactly the word ok."); print("PCC ok:", r.content) } catch { print("PCC error:", error) }
        do { let s = LanguageModelSession(model: SystemLanguageModel.default); let r = try await s.respond(to: "Reply with exactly the word ok."); print("on-device ok:", r.content) } catch { print("on-device error:", error) }
    }
}
