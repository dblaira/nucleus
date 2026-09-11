// nucleus through Apple's free server model, from this Mac. No key, no account.
// Usage: fmtest <prompt file> [light|moderate|deep]
import Foundation
import FoundationModels

@main
struct FMTest {
    static func main() async {
        let args = CommandLine.arguments
        guard args.count >= 2, let prompt = try? String(contentsOfFile: args[1], encoding: .utf8) else {
            print("usage: fmtest <prompt file> [light|moderate|deep]"); exit(2)
        }
        let level: ContextOptions.ReasoningLevel = args.count >= 3 ? (args[2] == "deep" ? .deep : args[2] == "moderate" ? .moderate : .light) : .light
        let pcc = PrivateCloudComputeLanguageModel()
        print("server model availability:", pcc.availability)
        print("server model quota:", pcc.quotaUsage)
        let onDevice = SystemLanguageModel.default
        print("on-device availability:", onDevice.availability)
        guard pcc.isAvailable else { print("server model not available"); exit(1) }
        do {
            let session = LanguageModelSession(model: pcc, instructions: "You return exactly one JSON object and nothing else, as the contract in the prompt describes.")
            let t0 = Date()
            let tokens = try await onDevice.tokenCount(for: prompt)
            let serverContext = try await pcc.contextSize
            let deviceContext = try await onDevice.contextSize
            print("prompt tokens (on-device tokenizer):", tokens, "| server context size:", serverContext, "| on-device context size:", deviceContext, "| counted in", String(format: "%.1f", Date().timeIntervalSince(t0)), "s")
            let t1 = Date()
            let response = try await session.respond(to: prompt, options: GenerationOptions(maximumResponseTokens: 2500), contextOptions: ContextOptions(reasoningLevel: level))
            print("answered in", String(format: "%.1f", Date().timeIntervalSince(t1)), "s")
            print("=== reply ===")
            print(response.content)
            print("=== end ===")
        } catch {
            print("error:", error)
            exit(1)
        }
    }
}
