import UIKit
import SwiftUI
import ImageIO

/// Picked photos remain local immediately; CloudKit transports referenced files as assets.
enum LocalImageStore {
    static var cache: SavyImageCache {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("reminder-images", isDirectory: true)
        return SavyImageCache(directory: base)
    }

    static func save(_ image: UIImage) -> String? {
        guard let data = image.jpegData(compressionQuality: 0.8) else { return nil }
        let name = UUID().uuidString + ".jpg"
        do { try cache.store(data, name: name); return name }
        catch { return nil }
    }

    static func load(_ name: String?) -> UIImage? {
        guard let name, let file = try? cache.existingFileURL(for: name) else { return nil }
        return UIImage(contentsOfFile: file.path)
    }

    /// Original JPEG bytes, without re-encoding the image.
    static func data(_ name: String?) -> Data? {
        guard let name, let file = try? cache.existingFileURL(for: name) else { return nil }
        return try? Data(contentsOf: file)
    }

    /// Write downloaded bytes under an explicit name (deterministic cache for cloud images).
    @discardableResult
    static func write(_ data: Data, name: String) -> String? {
        do { try cache.store(data, name: name); return name }
        catch { return nil }
    }

    static func exists(_ name: String) -> Bool {
        (try? cache.existingFileURL(for: name)) != nil
    }
}

/// Each main page keeps its own photo inside the CowboyAI Trial app container.
/// Saving a replacement is atomic, so a failed import leaves the previous image intact.
@MainActor
final class PageBackgroundStore: ObservableObject {
    enum ImportError: Error { case invalidImage, encodingFailed }

    @Published private(set) var images: [SavyNavigationSection: UIImage] = [:]
    private let directory: URL

    init(directory: URL? = nil) {
        self.directory = directory ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("page-backgrounds", isDirectory: true)
        for section in SavyNavigationSection.allCases {
            if let image = UIImage(contentsOfFile: fileURL(for: section).path) {
                images[section] = image
            }
        }
    }

    func image(for section: SavyNavigationSection) -> UIImage? { images[section] }

    func save(_ data: Data, for section: SavyNavigationSection) throws {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil),
              let thumbnail = CGImageSourceCreateThumbnailAtIndex(source, 0, [
                kCGImageSourceCreateThumbnailFromImageAlways: true,
                kCGImageSourceCreateThumbnailWithTransform: true,
                kCGImageSourceThumbnailMaxPixelSize: 2000
              ] as CFDictionary) else { throw ImportError.invalidImage }
        let image = UIImage(cgImage: thumbnail)
        guard let jpeg = image.jpegData(compressionQuality: 0.86) else { throw ImportError.encodingFailed }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try jpeg.write(to: fileURL(for: section), options: .atomic)
        images[section] = image
    }

    func useNavy(for section: SavyNavigationSection) throws {
        let file = fileURL(for: section)
        if FileManager.default.fileExists(atPath: file.path) {
            try FileManager.default.removeItem(at: file)
        }
        images.removeValue(forKey: section)
    }

    private func fileURL(for section: SavyNavigationSection) -> URL {
        directory.appendingPathComponent(section.rawValue + ".jpg")
    }
}
