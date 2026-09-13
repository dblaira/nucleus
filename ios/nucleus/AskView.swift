import SwiftUI

struct AskView: View {
    @State private var model = AskModel()
    @State private var showSettings = false
    @AppStorage("nucleus.base") private var base = "http://100.111.154.126:8766"
    private let fold = 4

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                masthead
                askBox
                steps
                answer
                earlier
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 40)
        }
        .background(CowboyTheme.tan.ignoresSafeArea())
        .scrollDismissesKeyboard(.interactively)
        .task {
            print("nucleus: view task started")
            await model.loadRecent()
            // a question handed in at launch (`-ask "..."`) is asked at once; used by the Mac to test the app
            if let i = CommandLine.arguments.firstIndex(of: "-ask"), i + 1 < CommandLine.arguments.count {
                model.question = CommandLine.arguments[i + 1]
                await model.ask()
            }
        }
        .sheet(isPresented: $showSettings) { settings }
    }

    private var masthead: some View {
        HStack(spacing: 16) {
            Image("CowboyHat").resizable().scaledToFit().frame(width: 64).foregroundStyle(CowboyTheme.cream)
            VStack(alignment: .leading, spacing: 4) {
                Text("nucleus").font(CowboyTheme.editorialSerif(40, relativeTo: .largeTitle)).italic().foregroundStyle(CowboyTheme.cream).shadow(color: .black.opacity(0.5), radius: 3, y: 1)
                Text("your words first, then your three answers").font(.system(size: 15)).foregroundStyle(CowboyTheme.cream.opacity(0.9))
            }
            Spacer()
            Button { showSettings = true } label: {
                Image(systemName: "gearshape").font(.system(size: 20)).foregroundStyle(CowboyTheme.cream.opacity(0.8))
            }
        }
        .padding(.vertical, 18).padding(.horizontal, 20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background {
            // the red rock photo Adam chose, under a navy wash so the words stay readable
            Image("Header").resizable().scaledToFill()
                .overlay(CowboyTheme.navy.opacity(0.62))
        }
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .shadow(color: .black.opacity(0.25), radius: 8, y: 4)
        .padding(.top, 8)
    }

    private var askBox: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("YOUR QUESTION").font(.system(size: 12, weight: .semibold)).tracking(1.4).foregroundStyle(CowboyTheme.navigationInactive)
            TextEditor(text: $model.question)
                .font(.custom(CowboyTheme.editorialSerifName, size: 22))
                .frame(minHeight: 120)
                .padding(8)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 10))
            HStack {
                Text("\(model.question.split(separator: " ").count) words").font(.system(size: 13)).foregroundStyle(CowboyTheme.navigationInactive)
                Spacer()
                Button {
                    Task { await model.ask() }
                } label: {
                    Text("Ask").font(.system(size: 19, weight: .bold)).foregroundStyle(CowboyTheme.cream)
                        .padding(.horizontal, 26).padding(.vertical, 14)
                        .background(CowboyTheme.cardRed).clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(model.working)
                .opacity(model.working ? 0.5 : 1)
            }
        }
        .padding(14)
        .background(CowboyTheme.cream)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(CowboyTheme.orange.opacity(0.7), lineWidth: 2))
    }

    private var steps: some View {
        VStack(spacing: 6) {
            ForEach(AskModel.stepNames, id: \.self) { name in
                let step = model.current?.steps.first { $0.name == name }
                let running = step != nil && step?.finished == nil
                let seconds: String = {
                    guard let step else { return "" }
                    let end = step.finished ?? Date().timeIntervalSince1970
                    return String(format: "%.1f s", max(0, end - step.started))
                }()
                HStack {
                    Text(name).font(.system(size: 16))
                    Spacer()
                    Text(seconds).font(.system(size: 16)).monospacedDigit()
                }
                .padding(.vertical, 9).padding(.horizontal, 14)
                .background(running ? CowboyTheme.navy : CowboyTheme.cream)
                .foregroundStyle(running ? CowboyTheme.cream : (step == nil ? CowboyTheme.navigationInactive : Color.black))
                .clipShape(RoundedRectangle(cornerRadius: 10))
            }
        }
    }

    @ViewBuilder private var answer: some View {
        if let problem = model.problem {
            Text(problem).font(.system(size: 18)).foregroundStyle(CowboyTheme.cardRed)
        }
        if let a = model.current?.answer {
            let parts = model.blocks
            VStack(alignment: .leading, spacing: 14) {
                if let n = model.current?.asked_before, n > 0 {
                    Text("asked before · \(n) \(n == 1 ? "time" : "times")").font(.custom(CowboyTheme.editorialSerifName, size: 18)).italic().foregroundStyle(CowboyTheme.navigationInactive)
                }
                if a.status != "answered" {
                    Text("\(a.status): \(a.text ?? a.gate_reason ?? "")").font(.system(size: 19)).foregroundStyle(CowboyTheme.cardRed)
                } else {
                    Text(parts.first).font(.custom(CowboyTheme.editorialSerifName, size: 28)).italic().foregroundStyle(CowboyTheme.cardRed)
                    let shown = model.showAll ? parts.rest : Array(parts.rest.prefix(fold))
                    ForEach(Array(shown.enumerated()), id: \.offset) { _, block in
                        blockView(block)
                    }
                    if !model.showAll && parts.rest.count > fold {
                        Button("▾ \(parts.rest.count - fold) more") { model.showAll = true }
                            .font(.system(size: 18)).foregroundStyle(CowboyTheme.navy)
                            .padding(.horizontal, 16).padding(.vertical, 10)
                            .overlay(RoundedRectangle(cornerRadius: 10).stroke(CowboyTheme.navy, lineWidth: 1.5))
                    }
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(CowboyTheme.cream)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        }
    }

    private func blockView(_ block: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(block).font(.system(size: 19)).foregroundStyle(Color.black)
            if let row = model.row(for: block) {
                HStack(spacing: 8) {
                    thumbButton("hand.thumbsup", on: model.thumbState(row) == 1, color: CowboyTheme.green) { Task { await model.thumb(row, up: true) } }
                    thumbButton("hand.thumbsdown", on: model.thumbState(row) == 0, color: CowboyTheme.cardRed) { Task { await model.thumb(row, up: false) } }
                }
            }
        }
    }

    private func thumbButton(_ symbol: String, on: Bool, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: symbol).font(.system(size: 18))
                .foregroundStyle(on ? Color.white : CowboyTheme.navigationInactive)
                .padding(.horizontal, 12).padding(.vertical, 7)
                .background(on ? color : Color.clear)
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(on ? color : CowboyTheme.tan, lineWidth: 1.5))
                .clipShape(RoundedRectangle(cornerRadius: 10))
        }
    }

    @ViewBuilder private var earlier: some View {
        if !model.recent.isEmpty {
            VStack(alignment: .leading, spacing: 0) {
                Text("earlier").font(.custom(CowboyTheme.editorialSerifName, size: 30)).italic().foregroundStyle(CowboyTheme.navy).padding(.bottom, 6)
                ForEach(model.recent) { item in
                    Button { Task { await model.open(item.id) } } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(item.answer ?? item.status).font(.system(size: 20, weight: .bold)).foregroundStyle(CowboyTheme.cardRed)
                            Text(item.question).font(.system(size: 20)).foregroundStyle(Color.black).multilineTextAlignment(.leading)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 12)
                    }
                    Divider()
                }
            }
            .padding(.top, 12)
        }
    }

    private var settings: some View {
        NavigationStack {
            Form {
                Section("the Mac") {
                    TextField("http://100.111.154.126:8766", text: $base).keyboardType(.URL).autocorrectionDisabled().textInputAutocapitalization(.never)
                }
            }
            .navigationTitle("nucleus")
            .toolbar { Button("Done") { showSettings = false } }
        }
    }
}
