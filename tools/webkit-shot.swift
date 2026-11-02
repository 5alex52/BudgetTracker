// Снимок страницы в настоящем WebKit (движок Safari) без Playwright.
// Использование: swift -module-cache-path ./tools/.mcache tools/webkit-shot.swift <url> <out.png> [w] [h] [scale]
import AppKit
import WebKit

let args = CommandLine.arguments
guard args.count >= 3 else {
    print("usage: webkit-shot <url> <out.png> [width] [height] [scale]")
    exit(2)
}
let url = URL(string: args[1])!
let outPath = args[2]
let width = args.count > 3 ? Double(args[3])! : 1440
let height = args.count > 4 ? Double(args[4])! : 900
let scale = args.count > 5 ? Double(args[5])! : 1.0

final class Shotter: NSObject, WKNavigationDelegate {
    let webView: WKWebView
    let outPath: String
    let size: CGSize

    init(size: CGSize, outPath: String) {
        self.size = size
        self.outPath = outPath
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        self.webView = WKWebView(frame: CGRect(origin: .zero, size: size), configuration: config)
        super.init()
        webView.navigationDelegate = self
    }

    func start(_ url: URL) {
        webView.load(URLRequest(url: url))
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        // Даём время шрифтам и анимациям устояться
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            self.webView.evaluateJavaScript("document.fonts.ready.then(() => document.documentElement.scrollHeight)") { result, _ in
                let pageHeight = (result as? NSNumber)?.doubleValue ?? Double(self.size.height)
                // Снимаем полную страницу: временно растягиваем вью
                let full = CGSize(width: self.size.width, height: min(max(pageHeight, self.size.height), 6000))
                self.webView.frame = CGRect(origin: .zero, size: full)
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                    let snapshotConfig = WKSnapshotConfiguration()
                    snapshotConfig.rect = CGRect(origin: .zero, size: full)
                    snapshotConfig.afterScreenUpdates = true
                    self.webView.takeSnapshot(with: snapshotConfig) { image, error in
                        guard let image = image,
                              let tiff = image.tiffRepresentation,
                              let rep = NSBitmapImageRep(data: tiff),
                              let png = rep.representation(using: .png, properties: [:]) else {
                            print("ошибка снимка: \(error?.localizedDescription ?? "нет изображения")")
                            exit(1)
                        }
                        try? png.write(to: URL(fileURLWithPath: self.outPath))
                        print("OK \(self.outPath) \(rep.pixelsWide)x\(rep.pixelsHigh) webkit")
                        exit(0)
                    }
                }
            }
        }
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        print("навигация не удалась: \(error.localizedDescription)")
        exit(1)
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

let shotter = Shotter(size: CGSize(width: width, height: height), outPath: outPath)
shotter.start(url)

DispatchQueue.main.asyncAfter(deadline: .now() + 25) {
    print("таймаут WebKit")
    exit(1)
}

app.run()
