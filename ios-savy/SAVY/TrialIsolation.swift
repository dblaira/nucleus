import Foundation

/// This separate app may use its own records and Nucleus, never SAVY's services.
enum TrialIsolation {
    static let connectsToSavyServices = false
}
