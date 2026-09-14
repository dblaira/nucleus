import SwiftUI

/// The CowboyAI app's Connection sheet (Cowboyai/authority-hub/ios/CowboyAI/SettingsView.swift), holding the
/// nucleus address and the build stamp.
struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var baseURLText = UserDefaults.standard.string(forKey: "nucleus.base") ?? "http://100.111.154.126:8766"

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("nucleus URL", text: $baseURLText)
                        .font(.system(size: 16, weight: .regular, design: .monospaced))
                        .foregroundStyle(CowboyTheme.navy)
                        .tint(CowboyTheme.red)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()
                        .textFieldStyle(.plain)
                        .padding(.horizontal, 14)
                        .frame(minHeight: 58)
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                } header: {
                    Text("the Mac")
                        .font(CowboyTheme.editorialSerif(16, relativeTo: .body))
                        .foregroundStyle(CowboyTheme.navy)
                }
                .listRowBackground(Color.white)

                Section {
                    Button {
                        UserDefaults.standard.set(baseURLText.trimmingCharacters(in: .whitespacesAndNewlines), forKey: "nucleus.base")
                        dismiss()
                    } label: {
                        HStack {
                            Text("Save and reconnect")
                            Spacer()
                            Image(systemName: "arrow.right")
                        }
                        .font(CowboyTheme.editorialSerif(16, relativeTo: .body))
                        .padding(.horizontal, 16)
                        .frame(maxWidth: .infinity, minHeight: 58)
                        .background(CowboyTheme.red)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
                .listRowBackground(Color.white)

                Section {
                    Text("build \(BuildStamp.text)")
                        .font(CowboyTheme.readingSerif(15, relativeTo: .body))
                        .foregroundStyle(CowboyTheme.navy)
                }
                .listRowBackground(Color.white)
            }
            .scrollContentBackground(.hidden)
            .background(Color.white)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("Connection")
                        .font(CowboyTheme.editorialSerif(21, relativeTo: .title3))
                        .foregroundStyle(CowboyTheme.cream)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        dismiss()
                    } label: {
                        Text("Done")
                            .font(CowboyTheme.editorialSerif(15, relativeTo: .body))
                            .foregroundStyle(CowboyTheme.cream)
                    }
                }
            }
            .toolbarBackground(CowboyTheme.navy, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .tint(CowboyTheme.red)
        }
    }
}
