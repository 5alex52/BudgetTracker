// imginspect.swift — offline reference-image inspector for the design task.
// Extracts (1) OCR text with normalized boxes, (2) a colour grid (avg per cell),
// (3) a quantised palette, (4) a "content density" ASCII map.
// Usage: swift tools/imginspect.swift <image> [gridW] [gridH]

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

func hex(_ r: Int, _ g: Int, _ b: Int) -> String {
    String(format: "#%02X%02X%02X", r, g, b)
}

// Downscale to wxh using high-quality interpolation => each output pixel is an area average.
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

func lum(_ r: Int, _ g: Int, _ b: Int) -> Double {
    0.2126 * Double(r) + 0.7152 * Double(g) + 0.0722 * Double(b)
}

let args = CommandLine.arguments
guard args.count >= 2 else { print("usage: imginspect <image> [gw] [gh]"); exit(2) }
let path = args[1]
let gw = args.count > 2 ? Int(args[2])! : 60
let gh = args.count > 3 ? Int(args[3])! : 34

guard let img = loadCGImage(path) else { print("cannot load \(path)"); exit(1) }
print("FILE: \((path as NSString).lastPathComponent)")
print("SIZE: \(img.width)x\(img.height)  aspect=\(String(format: "%.3f", Double(img.width)/Double(img.height)))")

// ---------- OCR ----------
let handler = VNImageRequestHandler(cgImage: img, options: [:])
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = true
req.recognitionLanguages = ["ru-RU", "en-US"]
var lines: [(String, CGRect, Float)] = []
do {
    try handler.perform([req])
    for obs in (req.results ?? []) {
        guard let cand = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox // origin bottom-left, normalized
        lines.append((cand.string, b, cand.confidence))
    }
} catch { print("OCR ERROR: \(error)") }

// sort top->bottom then left->right (group rows within 1.5% height)
lines.sort { a, b in
    let ay = 1 - a.1.midY, by = 1 - b.1.midY
    if abs(ay - by) > 0.018 { return ay < by }
    return a.1.minX < b.1.minX
}
print("\n--- OCR (\(lines.count) items) [x,y,w,h normalized, y from top] ---")
for (txt, b, conf) in lines {
    let x = b.minX, y = 1 - b.maxY, w = b.width, h = b.height
    print(String(format: "%.3f,%.3f,%.3f,%.3f\tc=%.2f\t%@",
                 x, y, w, h, conf, txt))
}

// ---------- colour grid ----------
let grid = downscale(img, gw, gh)
func px(_ gx: Int, _ gy: Int) -> (Int, Int, Int) {
    // CGContext draws with origin bottom-left; flip y for "top-down" reading
    let yy = gh - 1 - gy
    let i = (yy * gw + gx) * 4
    return (Int(grid[i]), Int(grid[i+1]), Int(grid[i+2]))
}

print("\n--- COLOUR GRID \(gw)x\(gh) (top-down rows) ---")
for gy in 0..<gh {
    var row = ""
    for gx in 0..<gw {
        let (r, g, b) = px(gx, gy)
        row += hex(r, g, b) + " "
    }
    print(String(format: "%02d ", gy) + row)
}

// ---------- ASCII luminance/density map ----------
let chars = Array(" .:-=+*#%@")
print("\n--- DENSITY MAP (top-down; @ = darkest/most ink) ---")
for gy in 0..<gh {
    var row = ""
    for gx in 0..<gw {
        let (r, g, b) = px(gx, gy)
        let l = lum(r, g, b)
        let idx = max(0, min(9, Int((255 - l) / 255 * 9.99)))
        row += String(chars[idx])
    }
    print(String(format: "%02d ", gy) + row)
}

// ---------- palette ----------
let sw = 180, sh = 100
let small = downscale(img, sw, sh)
var counts: [Int: Int] = [:]
for i in stride(from: 0, to: sw * sh * 4, by: 4) {
    let r = Int(small[i]) / 12 * 12, g = Int(small[i+1]) / 12 * 12, b = Int(small[i+2]) / 12 * 12
    counts[(r << 16) | (g << 8) | b, default: 0] += 1
}
let total = sw * sh
print("\n--- PALETTE (top 14, quantised) ---")
for (k, v) in counts.sorted(by: { $0.value > $1.value }).prefix(14) {
    let r = (k >> 16) & 0xFF, g = (k >> 8) & 0xFF, b = k & 0xFF
    print(String(format: "%@  %5.2f%%", hex(r, g, b), Double(v) / Double(total) * 100))
}

// ---------- saturated accent colours (chips, charts, icons) ----------
print("\n--- ACCENT COLOURS (saturated, quantified) ---")
var acc: [Int: Int] = [:]
for i in stride(from: 0, to: sw * sh * 4, by: 4) {
    let r = Int(small[i]), g = Int(small[i+1]), b = Int(small[i+2])
    let mx = max(r, max(g, b)), mn = min(r, min(g, b))
    if mx == 0 { continue }
    let sat = Double(mx - mn) / Double(mx)
    if sat < 0.35 || mx < 60 { continue }
    let key = (r / 20 * 20 << 16) | (g / 20 * 20 << 8) | (b / 20 * 20)
    acc[key, default: 0] += 1
}
for (k, v) in acc.sorted(by: { $0.value > $1.value }).prefix(12) {
    let r = (k >> 16) & 0xFF, g = (k >> 8) & 0xFF, b = k & 0xFF
    print(String(format: "%@  %d px", hex(r, g, b), v))
}
