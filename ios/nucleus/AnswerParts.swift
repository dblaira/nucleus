import Foundation

/// The answer text the Mac sends (gate.compose: first line, then his word's meanings, then the records his links
/// reach, then possibilities), split the way the page splits it and sorted into the pieces the screens show.
struct AnswerParts {
    struct Words: Identifiable {
        let id: Int
        let word: String
        let meanings: [String]
        let why: String
    }

    struct Record: Identifiable {
        let id: Int
        let row: AskResponse.Row
        let stamp: String       // "0.90 · 2026-07-10"
        let why: String
        var quote: String { row.quote.replacingOccurrences(of: "\\\"", with: "\"") }
        var label: String { [row.word, row.kind ?? ""].filter { !$0.isEmpty }.joined(separator: " ") }
    }

    var firstLine = ""
    var words: [Words] = []
    var records: [Record] = []
    var possibility: [String] = []
    var other: [String] = []

    init(text: String?, rows: [AskResponse.Row]) {
        guard let text, !text.isEmpty else { return }
        var lines = text.components(separatedBy: "\n")
        firstLine = lines.removeFirst()
        var blocks: [[String]] = []
        var current: [String] = []
        for line in lines {
            if line.isEmpty {
                if !current.isEmpty { blocks.append(current) }
                current = []
            } else {
                current.append(line)
            }
        }
        if !current.isEmpty { blocks.append(current) }

        var inPossibility = false
        for (index, block) in blocks.enumerated() {
            let joined = block.joined(separator: "\n")
            if inPossibility { possibility.append(joined); continue }
            if block == ["possibility"] { inPossibility = true; continue }
            if let row = rows.first(where: { row in
                let key = String(row.quote.replacingOccurrences(of: "\\\"", with: "\"").prefix(40))
                return !key.isEmpty && joined.contains(key)
            }) {
                let head = block[0]
                var stamp = ""
                if let dash = head.range(of: " — "), head[..<dash.lowerBound].first?.isNumber == true {
                    stamp = String(head[..<dash.lowerBound])
                }
                records.append(Record(id: index, row: row, stamp: stamp, why: block.dropFirst().joined(separator: "\n")))
            } else if let dash = block[0].range(of: " — “") {
                let word = String(block[0][..<dash.lowerBound])
                let prefix = word + " — “"
                var meanings: [String] = []
                var why: [String] = []
                for line in block {
                    if line.hasPrefix(prefix), line.hasSuffix("”") {
                        meanings.append(String(line.dropFirst(prefix.count).dropLast()))
                    } else {
                        why.append(line)
                    }
                }
                words.append(Words(id: index, word: word, meanings: meanings, why: why.joined(separator: "\n")))
            } else {
                other.append(joined)
            }
        }
    }
}
