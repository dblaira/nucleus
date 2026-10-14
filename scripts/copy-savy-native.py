"""One-time source import. No SAVY files, data, or services are changed."""
from pathlib import Path
import hashlib
import json
import shutil

src = Path('/Users/adamblair/Developer/GitHub/SAVY-iOS/SAVY')
dst = Path(__file__).resolve().parents[1] / 'ios/nucleus/SavyFeatures'
dst.mkdir(parents=True, exist_ok=True)
files = ['ReminderModels.swift', 'ReminderFormView.swift', 'ReminderScheduleView.swift',
         'ReminderCalendarIntegration.swift', 'ReminderNotificationScheduler.swift',
         'SavyReminderScreens.swift', 'CalendarView.swift', 'SavyTypography.swift',
         'ReminderBrandTheme.swift', 'SavyWideLayout.swift', 'SavyCarouselDetails.swift',
         'LocalImageStore.swift', 'SavyImageCache.swift']
manifest = []
for name in files:
    raw = (src / name).read_bytes()
    text = '// Adapted from SAVY-iOS 87f2b8c; runs only inside CowboyAI. No SAVY service or data access.\n' + raw.decode()
    manifest.append({'source': name, 'source_sha256': hashlib.sha256(raw).hexdigest()})
    if name == 'ReminderModels.swift':
        text = text.replace('struct Reminder: Identifiable, Codable, Equatable {',
                            'struct Reminder: Identifiable, Codable, Equatable {\n    var origin: ConversationOrigin? = nil')
        assert 'var origin: ConversationOrigin?' in text
    if name == 'ReminderBrandTheme.swift':
        text = text.replace('Color(red: 0xDC / 255, green: 0x14 / 255, blue: 0x3C / 255)', 'CowboyTheme.red')
        text = text.replace('Color(hex: 0xB00124)', 'CowboyTheme.red')
    if name == 'LocalImageStore.swift':
        start = text.index('        let base = FileManager.default.urls')
        end = text.index('        return SavyImageCache', start)
        text = text[:start] + '        let base = CowboyStorage.directory.appendingPathComponent("entry-images", isDirectory: true)\n' + text[end:]
    if name == 'SavyWideLayout.swift':
        text = text[:text.index('/// Gives the Mac window')] + '#endif\n'
    if name in ['ReminderCalendarIntegration.swift', 'ReminderNotificationScheduler.swift', 'ReminderModels.swift']:
        text = text.replace('savy.schedule.', 'cowboyai.schedule.').replace('recall.reminder.', 'cowboyai.reminder.')
        text = text.replace('SAVY_UI_TEST_UNLOCKED', 'COWBOYAI_UI_TEST')
        text = text.replace('SAVY only', 'CowboyAI only').replace('Allow SAVY', 'Allow CowboyAI').replace('Your SAVY entry', 'Your CowboyAI entry')
        text = text.replace('-//SAVY//Schedule//EN', '-//CowboyAI//Schedule//EN').replace('@savy', '@cowboyai')
    if name == 'ReminderFormView.swift':
        text = text.replace('let connectionMode: Bool', 'private let connectionMode = false\n    let origin: ConversationOrigin?\n    @Environment(ConversationArchive.self) private var archive\n    @State private var showingOrigin: ConversationOrigin?')
        text = text.replace('connectionMode: Bool = false, existing:', 'origin: ConversationOrigin? = nil, existing:')
        text = text.replace('self.connectionMode = connectionMode', 'self.origin = origin')
        text = text.replace('kind: initialKind, connectionMode: connectionMode)', 'kind: initialKind, origin: origin)')
        text = text.replace('base.kind = initialKind', 'base.kind = initialKind\n            base.origin = origin')
        text = text.replace('fixedTheme: connectionMode ? ConnectionEntry.theme : nil', 'fixedTheme: nil')
        text = text.replace('ForEach(ReminderKind.allCases)', 'ForEach(ReminderKind.allCases.filter { $0 != .post })')
        text = text.replace('                unifiedEntrySections', '''                if let source = r.origin {
                    Section("From this conversation") {
                        Button { showingOrigin = source } label: {
                            Label(source.question, systemImage: "arrow.uturn.backward")
                                .lineLimit(3).foregroundStyle(CowboyTheme.red)
                        }.accessibilityIdentifier("entryOrigin")
                    }.listRowBackground(CowboyTheme.tan)
                }
                unifiedEntrySections''')
        text = text.replace('        .sheet(isPresented: $showsSchedule)', '''        .sheet(item: $showingOrigin) { source in
            NavigationStack { ArchivedAnswerPage(origin: source, archive: archive) }
        }
        .sheet(isPresented: $showsSchedule)''')
        text = text.replace('Text(connectionMode ? "Saved" : "Harnessed!")', 'Text("Saved")')
        start = text.index("        // Adam's list #7:")
        end = text.index('        UINotificationFeedbackGenerator()', start)
        text = text[:start] + '        // Local CowboyAI save only; no Harness or candidate submission.\n' + text[end:]
        text = text.replace('connectionMode: connectionMode))', 'connectionMode: false))')
    if name == 'SavyReminderScreens.swift':
        text = text.replace('@EnvironmentObject private var store: ReminderStore', '@Environment(ReminderStore.self) private var store')
        text = text.replace('Color(hex: 0xB00124)', 'CowboyTheme.red')
    if name == 'CalendarView.swift':
        text = text.replace('@EnvironmentObject var store: ReminderStore', '@Environment(ReminderStore.self) private var store')
        text = text.replace('Color(hex: 0xB00124)', 'CowboyTheme.red')
    (dst / name).write_text(text)

text = (src / 'PostTheme.swift').read_text()
(dst / 'PostEntryDraft.swift').write_text('import Foundation\n\n' + text[text.index('struct PostEntryDraft:'):text.index('/// The seed catalog')])
text = (src / 'SavyShellComponents.swift').read_text()
helpers = 'import SwiftUI\nimport UIKit\n\n' + text[text.index('enum SavyHapticFeedback'):text.index('enum SavyFabMenuMotion')]
helpers += '''
extension View {
    func savyHeaderPageContent(minHeight: CGFloat) -> some View {
        frame(maxWidth: .infinity, minHeight: minHeight, alignment: .top)
            .background(SavyTheme.contentBackground)
    }
    func savyHeaderOverscrollCapture(_ screen: String) -> some View { self }
}

enum RootHomeLayout {
    static let heroDividerHeight: CGFloat = 1
    static let bottomNavNavyRiserHeight: CGFloat = 44
    static let carouselCardTitleFontSize: CGFloat = 24
}

enum SavyTheme {
    static let deepNavy = CowboyTheme.navy
    static let pageBackground = CowboyTheme.navy
    static let contentBackground = Color.white
    static let headerDivider = Color.white
    static let crimson = CowboyTheme.red
    static let bottomNavTan = CowboyTheme.bottomNavigationTan
    static let secondaryText = Color.black.opacity(0.62)
    static let tertiaryText = Color.black.opacity(0.45)
}
'''
(dst / 'SavyFeatureSupport.swift').write_text(helpers)
root = dst.parents[2]
for name in ['RemindersBeachLandscape', 'ActionsCarLandscape', 'HomeMountainLandscape']:
    path = src / 'Assets.xcassets' / f'{name}.imageset'
    if path.exists():
        shutil.copytree(path, dst.parent / 'Assets.xcassets' / path.name, dirs_exist_ok=True)
(dst / 'Fonts').mkdir(exist_ok=True)
for name in ['BodoniModa-Regular.ttf', 'Roboto-Medium.ttf']:
    shutil.copy2(src / 'Fonts' / name, dst / 'Fonts' / name)
output = dst.parents[2] / 'docs/savy-source-manifest.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps({'source_commit': '87f2b8c535fd7069d9748159a78d3770247f1a2c', 'copied': manifest,
                             'boundary': 'Local CowboyAI code only. No SAVY data, services, cloud, or Harness writes.'}, indent=2) + '\n')
print('Imported', len(files), 'native sources; SAVY unchanged')
