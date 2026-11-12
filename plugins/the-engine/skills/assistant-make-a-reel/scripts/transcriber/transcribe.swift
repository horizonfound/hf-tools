// transcribe: the Mac's own Speech Recognition on one sound file, on this Mac only, with the time of every word.
// The Assistant, by Horizon Found (transcribe.py's MacSpeech builds this into a small app and starts it through
// the Mac's own `open`; the Speech Recognition permission needs an app of its own to belong to).
//
// KEEP THIS FILE SHORT AND FROZEN. To macOS a rebuilt app is a new app, and it asks for the permission again.
// Everything that may change lives in Python.
//
// Arguments: <sound file> <language> <answer file> <state file> <alive file> <deadline, seconds since 1970>
// The answer file (written whole under another name, then given its name):
//     {"ok": true, "words": [{"w", "start", "end", "conf"}], "ondevice": true}
//  or {"error": "<code>", "detail": "<the Mac's own words, for the log only>"}
// Codes, never sentences: denied, restricted, not_asked, unavailable, servers, language, no_words, failed,
// deadline, stopped, args.
// The state file: {"state": "asking" | "working", "pid": this program's number}.
// It stops by itself when nothing has touched the alive file for 12 seconds (the job that started it is gone),
// or when the deadline passes. It never uses Apple's servers: a Mac that can't do it by itself answers "servers".
import Foundation
import Speech

struct Word { let w: String; let start: Double; let end: Double; let conf: Double }

let args = CommandLine.arguments
func put(_ d: [String: Any], _ path: String) {
    guard let j = try? JSONSerialization.data(withJSONObject: d) else { return }
    let part = path + ".part"
    if FileManager.default.createFile(atPath: part, contents: j) { _ = rename(part, path) }
}
guard args.count >= 7, let deadline = Double(args[6]) else {
    if args.count >= 4 { put(["error": "args", "detail": ""], args[3]) }
    exit(2)
}
let sound = args[1], lang = args[2], answerPath = args[3], statePath = args[4], alivePath = args[5]

var all: [Word] = []                    // every word so far; a newer piece replaces the words it covers
var recognizer: SFSpeechRecognizer?
var task: SFSpeechRecognitionTask?

func fail(_ code: String, _ detail: String = "") -> Never {
    put(["error": code, "detail": detail], answerPath)
    exit(1)
}
func state(_ s: String) {
    put(["state": s, "pid": Int(ProcessInfo.processInfo.processIdentifier)], statePath)
}
func r3(_ x: Double) -> Double { return (x * 1000).rounded() / 1000 }
func finish() -> Never {
    if all.isEmpty { fail("no_words") }
    let words: [[String: Any]] = all.map {
        ["w": $0.w, "start": r3($0.start), "end": r3($0.end), "conf": ($0.conf * 100).rounded() / 100]
    }
    put(["ok": true, "words": words, "ondevice": true], answerPath)
    exit(0)
}

func go() {
    guard let rec = SFSpeechRecognizer(locale: Locale(identifier: lang)) else { fail("language", lang) }
    guard rec.supportsOnDeviceRecognition else { fail("servers") }      // never Apple's servers; asked first: a Mac
    guard rec.isAvailable else { fail("unavailable") }                  // that needs them, offline, is "servers" too
    recognizer = rec
    let req = SFSpeechURLRecognitionRequest(url: URL(fileURLWithPath: sound))
    req.shouldReportPartialResults = true      // a long recording comes back in pieces: keep every piece
    req.requiresOnDeviceRecognition = true
    req.addsPunctuation = true                 // the sentences are found by . ? !
    state("working")
    task = rec.recognitionTask(with: req) { result, error in
        if let r = result {
            let segs = r.bestTranscription.segments.filter { !$0.substring.isEmpty }
            // a piece in progress has no times yet: it counts once every word has a length
            let timed = !segs.isEmpty && segs.allSatisfy { $0.duration > 0 }
            if timed, let first = segs.first {
                all.removeAll { $0.start >= first.timestamp - 0.01 }
                all += segs.map {
                    Word(w: $0.substring, start: $0.timestamp, end: $0.timestamp + $0.duration, conf: Double($0.confidence))
                }
            }
            if r.isFinal { finish() }
        }
        if let e = error {
            let ns = e as NSError
            if all.isEmpty { fail("failed", "\(ns.domain) \(ns.code): \(ns.localizedDescription)") } else { finish() }
        }
    }
}

// The job that started this touches the alive file every second. When it stops, or the deadline passes, so do we.
let watch = DispatchSource.makeTimerSource(queue: DispatchQueue.main)
watch.schedule(deadline: .now() + 2, repeating: 2)
watch.setEventHandler {
    let now = Date()
    if now.timeIntervalSince1970 > deadline { task?.cancel(); fail("deadline") }
    let touched = (try? FileManager.default.attributesOfItem(atPath: alivePath))?[.modificationDate] as? Date
    if touched == nil || now.timeIntervalSince(touched!) > 12 { task?.cancel(); fail("stopped") }
}
watch.resume()

func answered(_ st: SFSpeechRecognizerAuthorizationStatus) {
    switch st {
    case .authorized: go()
    case .denied: fail("denied")
    case .restricted: fail("restricted")
    default: fail("not_asked")
    }
}
if SFSpeechRecognizer.authorizationStatus() == .notDetermined {
    state("asking")                            // macOS is about to ask its question
    SFSpeechRecognizer.requestAuthorization { st in DispatchQueue.main.async { answered(st) } }
} else {
    answered(SFSpeechRecognizer.authorizationStatus())
}
dispatchMain()
