// imginspect2.swift — offline reference-image inspector (crops, scan lines, segments).
// Usage:
//   swift tools/imginspect2.swift <image> [--gw N] [--gh N] [--crop x,y,w,h] [--grid]
//                                    [--hline y] [--vline x] [--segments h|v,coord]
//   All coords normalized 0..1 in original image space; y measured from the top.
import Foundation
import Vision
import CoreGraphics
import ImageIO
import AppKit

func loadCGImage(_ path: String) -> CGImage? {
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { return nil }
    return img
}
func hex(_ r: Int, _ g: Int, _ b: Int) -> String { String(format: "#%02X%02X%02X", r, g, b) }

func downscale(_ img: CGImage, _ w: Int, _ h: Int) -> [UInt8] {
    let cs = CGColorSpaceCreateDeviceRGB()
    var buf = [UInt8](repeating: 0, count: w * h * 4)
    guard let ctx = CGContext(data: &buf, width: w, height: h, bitsPerComponent: 8,
                              bytesPerRow: w * 4, space: cs,
                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return buf }
    ctx.interpolationQuality = .high
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
    return buf
}
func lum(_ r: Int, _ g: Int, _ b: Int) -> Double { 0.2126 * Double(r) + 0.7152 * Double(g) + 0.0722 * Double(b) }

// Full-resolution RGB accessor
struct Pix {
    let w: Int, h: Int, buf: [UInt8]
    init(_ img: CGImage) {
        w = img.width; h = img.height
        let cs = CGColorSpaceCreateDeviceRGB()
        var b = [UInt8](repeating: 0, count: w * h * 4)
        let ctx = CGContext(data: &b, width: w, height: h, bitsPerComponent: 8,
                            bytesPerRow: w * 4, space: cs,
                            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        ctx.interpolationQuality = .none
        ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
        buf = b
    }
    // top-down coords
    func at(_ x: Int, _ y: Int) -> (Int, Int, Int) {
        let cx = min(max(x, 0), w - 1), cy = min(max(y, 0), h - 1)
        let i = (cy * w + cx) * 4
        return (Int(buf[i]), Int(buf[i + 1]), Int(buf[i + 2]))
    }
}

var path: String?
var gw = 60, gh = 34
var crop: (Double, Double, Double, Double)?
var doGrid = false, doOCR = false
var hline: Double?, vline: Double?
var segSpec: String?
var saveCrop: String?
var outScale = 1.0

var it = CommandLine.arguments.dropFirst().makeIterator()
while let a = it.next() {
    switch a {
    case "--gw": gw = Int(it.next() ?? "60") ?? 60
    case "--gh": gh = Int(it.next() ?? "34") ?? 34
    case "--crop":
        let p = (it.next() ?? "").split(separator: ",").compactMap { Double($0) }
        if p.count == 4 { crop = (p[0], p[1], p[2], p[3]) }
    case "--grid": doGrid = true
    case "--ocr": doOCR = true
    case "--hline": hline = Double(it.next() ?? "0")
    case "--vline": vline = Double(it.next() ?? "0")
    case "--segments": segSpec = it.next()
    case "--save-crop": saveCrop = it.next()
    case "--scale": outScale = Double(it.next() ?? "1") ?? 1
    default: if path == nil { path = a }
    }
}
guard let p = path, let img = loadCGImage(p) else { print("cannot load"); exit(1) }
let P = Pix(img)
print("FILE: \((p as NSString).lastPathComponent)  \(img.width)x\(img.height)")

if doOCR {
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    req.recognitionLanguages = ["ru-RU", "en-US"]
    var lines: [(String, CGRect, Float)] = []
    try? handler.perform([req])
    for obs in (req.results ?? []) {
        guard let c = obs.topCandidates(1).first else { continue }
        lines.append((c.string, obs.boundingBox, c.confidence))
    }
    lines.sort { a, b in
        let ay = 1 - a.1.midY, by = 1 - b.1.midY
        if abs(ay - by) > 0.015 { return ay < by }
        return a.1.minX < b.1.minX
    }
    print("\n--- OCR \(lines.count) [x,y,w,h norm from top] ---")
    for (t, b, c) in lines {
        print(String(format: "%.3f,%.3f,%.3f,%.3f c=%.2f\t%@", b.minX, 1 - b.maxY, b.width, b.height, c, t))
    }
}

// crop rect in device px
let cr = crop.map { (x: $0.0, y: $0.1, w: $0.2, h: $0.3) } ?? (x: 0.0, y: 0.0, w: 1.0, h: 1.0)
let x0 = Int(cr.x * Double(img.width)), y0 = Int(cr.y * Double(img.height))
let cw = max(1, Int(cr.w * Double(img.width))), ch = max(1, Int(cr.h * Double(img.height)))
print("CROP px: x=\(x0) y=\(y0) w=\(cw) h=\(ch)")

if doGrid {
    // sample the crop region on a gw x gh grid (average of each cell)
    print("\n--- GRID \(gw)x\(gh) within crop ---")
    for gy in 0..<gh {
        var row = ""
        for gx in 0..<gw {
            let sx0 = x0 + cw * gx / gw, sx1 = x0 + cw * (gx + 1) / gw
            let sy0 = y0 + ch * gy / gh, sy1 = y0 + ch * (gy + 1) / gh
            var r = 0, g = 0, b = 0, n = 0
            var yy = sy0
            while yy < max(sy1, sy0 + 1) {
                var xx = sx0
                while xx < max(sx1, sx0 + 1) {
                    let (pr, pg, pb) = P.at(xx, yy)
                    r += pr; g += pg; b += pb; n += 1; xx += 2
                }
                yy += 2
            }
            n = max(n, 1)
            row += hex(r / n, g / n, b / n) + " "
        }
        print(String(format: "%02d ", gy) + row)
    }
    print("\n--- DENSITY \(gw)x\(gh) (@ = darkest) ---")
    let chars = Array(" .:-=+*#%@")
    for gy in 0..<gh {
        var row = ""
        for gx in 0..<gw {
            let cx = x0 + cw * (2 * gx + 1) / (2 * gw), cy = y0 + ch * (2 * gy + 1) / (2 * gh)
            let (r, g, b) = P.at(cx, cy)
            row.append(chars[max(0, min(9, Int((255 - lum(r, g, b)) / 255 * 9.99)))])
        }
        print(String(format: "%02d ", gy) + row)
    }
}

if let outPath = saveCrop {
    let scale = outScale
    let ow = max(1, Int(Double(cw) * scale)), oh = max(1, Int(Double(ch) * scale))
    let cs = CGColorSpaceCreateDeviceRGB()
    let ctx = CGContext(data: nil, width: ow, height: oh, bitsPerComponent: 8, bytesPerRow: 0,
                        space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.interpolationQuality = .high
    // flip: crop from top-down coords into bottom-left origin space
    // CGImage.cropping(to:) uses a top-left origin — take y0 directly
    let cropRect = CGRect(x: x0, y: y0, width: cw, height: ch)
    if let sub = img.cropping(to: cropRect) {
        ctx.draw(sub, in: CGRect(x: 0, y: 0, width: ow, height: oh))
    }
    if let out = ctx.makeImage() {
        let url = URL(fileURLWithPath: outPath)
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(),
                                                withIntermediateDirectories: true)
        if let dest = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) {
            CGImageDestinationAddImage(dest, out, nil)
            CGImageDestinationFinalize(dest)
            print("SAVED CROP: \(outPath) \(ow)x\(oh)")
        }
    }
}

if let y = hline {
    let yy = Int(y * Double(img.height))
    print("\n--- HLINE y=\(yy)px (=\(String(format: "%.4f", y))) step 1px ---")
    var x = x0
    var out: [String] = []
    while x < x0 + cw {
        let (r, g, b) = P.at(x, yy)
        out.append("\(x):\(hex(r, g, b))")
        x += 1
    }
    // print in chunks of 10
    for i in stride(from: 0, to: out.count, by: 10) {
        print(out[i..<min(i + 10, out.count)].joined(separator: "  "))
    }
}

if let x = vline {
    let xx = Int(x * Double(img.width))
    print("\n--- VLINE x=\(xx)px (=\(String(format: "%.4f", x))) step 1px ---")
    var y = y0
    var out: [String] = []
    while y < y0 + ch {
        let (r, g, b) = P.at(xx, y)
        out.append("\(y):\(hex(r, g, b))")
        y += 1
    }
    for i in stride(from: 0, to: out.count, by: 10) {
        print(out[i..<min(i + 10, out.count)].joined(separator: "  "))
    }
}

if let spec = segSpec {
    let parts = spec.split(separator: ",")
    let axis = String(parts[0])
    let coord = Double(parts.count > 1 ? String(parts[1]) : "0.5") ?? 0.5
    let tol = parts.count > 2 ? (Int(parts[2]) ?? 6) : 6
    print("\n--- SEGMENTS along \(axis) at \(coord) tol=\(tol) ---")
    var runs: [(Int, Int, (Int, Int, Int))] = []
    var curColor: (Int, Int, Int) = (0, 0, 0)
    var start = 0
    func flush(_ end: Int) {
        if end > start { runs.append((start, end - 1, curColor)) }
    }
    if axis == "h" {
        let yy = Int(coord * Double(img.height))
        var x = x0
        curColor = P.at(x, yy); start = x
        while x < x0 + cw {
            let c = P.at(x, yy)
            if abs(c.0 - curColor.0) > tol || abs(c.1 - curColor.1) > tol || abs(c.2 - curColor.2) > tol {
                flush(x); curColor = c; start = x
            }
            x += 1
        }
        flush(x0 + cw)
    } else {
        let xx = Int(coord * Double(img.width))
        var y = y0
        curColor = P.at(xx, y); start = y
        while y < y0 + ch {
            let c = P.at(xx, y)
            if abs(c.0 - curColor.0) > tol || abs(c.1 - curColor.1) > tol || abs(c.2 - curColor.2) > tol {
                flush(y); curColor = c; start = y
            }
            y += 1
        }
        flush(y0 + ch)
    }
    let minLen = 1
    for (s, e, c) in runs where (e - s + 1) >= minLen {
        print("\(s)..\(e)  len=\(e - s + 1)  \(hex(c.0, c.1, c.2))")
    }
}
