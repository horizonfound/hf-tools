#!/usr/bin/env python3
"""The carousel designer's WORDS, checked: text boxes, fonts, the font list, brand colors.
Run through tests/design_check.py (which calls the two functions here):

    python3 tests/design_check.py --only page                       the scripts by themselves (no server, seconds)
    python3 tests/design_check.py --only text --port 8950 --work /private/tmp/<new folder>
                                                                    the real page in a hidden Chrome (this part only)

check_type_page: what the text and brand-color parts are made of, and the rules in DESIGN_TYPE_JS run by
themselves under the Mac's own JavaScript engine with a pretend ruler (every letter 10 wide): where lines break,
where each sits, how tall the box is, what a font's name may be, the address asked of Google, tidying.

check_type_browser: the real page, served by the real page server from a pretend kit, in a hidden Chrome
(tests/chrome_drive.py; SKIP when there is no Chrome). After every change it compares the screen with the
design's file on the drive. The parts that need Google Fonts (a font loaded by name, a misspelled name) are
SKIPPED when the internet cannot be reached; the parts about having no internet block every outside address
themselves. It never opens a window, never touches the real ~/.studio, and never asks for Finder.
"""
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "the-engine" / "skills" / "studio-manager" / "scripts"
W, H = 1080, 1350
MINE = ("design_js_type.py", "design_js_text.py", "design_js_brand.py")

TYPE_TESTS_JS = r"""
(new Function(TYPE_SRC)).call(this);
var T = this.DesignType, out = [];
function t(name, ok, detail){ out.push([name, !!ok, detail === undefined ? '' : JSON.stringify(detail)]); }
function eq(a, b){ return JSON.stringify(a) === JSON.stringify(b); }
// the pretend ruler: every letter is 10 wide (a two-part letter such as an emoji counts once)
var calls = 0;
function m(s){ calls += 1; return Array.from(s).length * 10; }
function texts(ls){ return ls.map(function(l){ return l.t; }); }
function TX(more){ var b = {id: 1, type: 'text', text: 'one two three', font: 'Inter', size: 100, weight: 400, italic: false, upper: false, al: 'center', ls: 0, lh: 1.2, color: '#2a2622', x: 0, y: 0, w: 70, h: 1}; for (var k in (more || {})) b[k] = more[k]; return b; }

// ---- where lines break ----
var L = T.wrapLines('one two three', 70, m);
t('wrap: words go to the next line when they do not fit ("one two" is 70 wide, the box 70)', eq(texts(L), ['one two', 'three']) && L[0].w === 70 && L[1].w === 50, L);
t('wrap: one pixel narrower and "two" goes down as well', eq(texts(T.wrapLines('one two three', 69, m)), ['one', 'two', 'three']));
t('wrap: runs of spaces count as one, and spaces at the ends are dropped', eq(T.wrapLines('  one   two  ', 500, m), [{t: 'one two', w: 70}]));
t('wrap: a line break they typed is kept, an empty line too', eq(texts(T.wrapLines('a\n\nb', 500, m)), ['a', '', 'b']) && eq(T.wrapLines('a\n\nb', 500, m)[1], {t: '', w: 0}));
t('wrap: no words at all is one empty line; a lone line break is two', eq(T.wrapLines('', 500, m), [{t: '', w: 0}]) && T.wrapLines('\n', 500, m).length === 2 && T.wrapLines('   ', 500, m).length === 1);
t('wrap: a single word wider than the box is cut where it stops fitting', eq(texts(T.wrapLines('abcdefghij', 40, m)), ['abcd', 'efgh', 'ij']));
t('wrap: ...and the words around it carry on from what is left of it', eq(texts(T.wrapLines('hi abcdefghij yo ok', 50, m)), ['hi', 'abcde', 'fghij', 'yo ok']), texts(T.wrapLines('hi abcdefghij yo ok', 50, m)));
t('wrap: a box narrower than one letter still gets a letter a line (it never loops or loses a letter)', eq(texts(T.wrapLines('abc de', 5, m)), ['a', 'b', 'c', 'd', 'e']));
t('wrap: an emoji is never cut in half', eq(texts(T.wrapLines('a🌊b', 10, m)), ['a', '🌊', 'b']) && T.letters('🌊a').length === 2);
t('wrap: every letter that went in comes out, in order (spaces aside)', (function(){
  var src = 'The quick brown fox, jumping over a supercalifragilistic dog! été 🌊 ok';
  return [15, 40, 90, 170, 400, 2000].every(function(w){ return texts(T.wrapLines(src, w, m)).join('').replace(/ /g, '') === src.replace(/ /g, ''); });
})());
t('wrap: no line is wider than the box unless it is a single letter', [15, 40, 90, 170].every(function(w){
  return T.wrapLines('The quick brown fox jumping over a supercalifragilistic dog', w, m).every(function(l){ return l.w <= w || Array.from(l.t).length === 1; });
}));
t('wrap: the same words and width always break the same way', eq(T.wrapLines('one two three four five', 90, m), T.wrapLines('one two three four five', 90, m)));
t('wrap: a hard space keeps two words together', eq(texts(T.wrapLines('one two three', 100, m)), ['one', 'two three']));

// ---- the box ----
var Y = T.layout(TX(), m);
t('layout: two lines of size 100 at 1.2 are 240 tall; each line is 120', Y.h === 240 && Y.lh === 120 && Y.lines.length === 2, Y);
t('layout: centered lines start half the spare room in (0 and 10)', Y.lines[0].x === 0 && Y.lines[1].x === 10, Y.lines);
Y = T.layout(TX({al: 'left', w: 100}), m);
t('layout: left lines start at the box\'s left edge', Y.lines.every(function(l){ return l.x === 0; }), Y.lines);
Y = T.layout(TX({al: 'right', w: 100}), m);
t('layout: right lines end at the box\'s right edge', Y.lines.every(function(l){ return l.x + l.w === 100; }), Y.lines);
Y = T.layout(TX({upper: true, text: 'straße café'}), m);
t('layout: all capitals are measured and drawn as capitals', eq(texts(Y.lines), ['STRASSE', 'CAFÉ']), texts(Y.lines));
t('layout: no words is still one line tall', T.layout(TX({text: ''}), m).h === 120);
t('layout: the height is kept to two decimal places', T.layout(TX({size: 33.33, lh: 1.115, text: 'a'}), m).h === 37.16, T.layout(TX({size: 33.33, lh: 1.115, text: 'a'}), m).h);
t('layout: a box is never written down taller than the Assistant takes (13,500)', T.layout(TX({size: 600, lh: 3, w: 10, text: 'a b c d e f g h i j'}), m).h === 13500);
t('baseline: the font\'s own height sits in the middle of the line (line 110.4, font 80 up and 20 down: 85.2)', Math.abs(T.baseline(110.4, 80, 20) - 85.2) < 1e-9);
t('sig: anything that could move a line changes it; the color and the place do not', (function(){
  var a = T.sig(TX());
  return ['font', 'size', 'weight', 'italic', 'upper', 'al', 'ls', 'lh', 'w', 'text'].every(function(k){
    var o = {}; o[k] = {font: 'Lora', size: 101, weight: 700, italic: true, upper: true, al: 'left', ls: 3, lh: 1.3, w: 71, text: 'x'}[k];
    return T.sig(TX(o)) !== a;
  }) && T.sig(TX({color: '#ffffff', x: 50, y: 60, h: 9, id: 7})) === a;
})());

// ---- a font's name ----
t('font name: letters, digits and single spaces', ['Playfair Display', 'Old Standard TT', 'Inter', 'Source Sans 3', 'A'].every(T.fontOk));
t('font name: nothing else', ['', ' Inter', 'Inter ', 'Inter  Tight', 'Inter;', 'a"b', "a'b", 'a,b', 'a/b', 'a\\b', 'a:b', 'a(b)', 'x\ny', 'café', 'a+b', 'a&b', 'a<b', '../x', 'url(x)'].every(function(n){ return !T.fontOk(n); }));
t('font name: at most 50 letters, and only text', T.fontOk(new Array(51).join('a')) && !T.fontOk(new Array(52).join('a')) && !T.fontOk(null) && !T.fontOk(7) && !T.fontOk(['Inter']) && !T.fontOk({}));
t('font string: weight, size, the name in quotes, then Georgia', T.fontString({font: 'Playfair Display', weight: 400}, 96) === '400 96px "Playfair Display", Georgia, serif', T.fontString({font: 'Playfair Display', weight: 400}, 96));
t('font string: italic and bold', T.fontString({font: 'Lora', weight: 700, italic: true}, 40) === 'italic 700 40px "Lora", Georgia, serif');
t('font string: a name that is not a font\'s name never gets into it', T.fontString({font: 'x", serif; background: url(http://e.vil)', weight: 400}, 40) === '400 40px Georgia, serif' && T.fontString({font: null, weight: 'bold', italic: 'yes'}, 'big') === '400 96px Georgia, serif', T.fontString({font: null, weight: 'bold', italic: 'yes'}, 'big'));
t('family string: the name in quotes, then Georgia', T.familyString('DM Sans') === '"DM Sans", Georgia, serif' && T.familyString('a"b') === 'Georgia, serif');
var G = 'https://fonts.googleapis.com/css2';
t('Google address: spaces become +, the weights the list gives are asked for', T.googleHref(G, 'Playfair Display', '400;700') === G + '?family=Playfair+Display:wght@400;700&display=swap', T.googleHref(G, 'Playfair Display', '400;700'));
t('Google address: a family with one weight is asked for with no weights', T.googleHref(G, 'Great Vibes', '') === G + '?family=Great+Vibes&display=swap');
t('Google address: a wrong name, wrong weights or no address gives nothing at all', T.googleHref(G, 'a&b', '') === '' && T.googleHref(G, 'Lora', '400,700') === '' && T.googleHref(G, 'Lora', '4000') === '' && T.googleHref(G, 'Lora', '400;700&x=1') === '' && T.googleHref('', 'Lora', '') === '' && T.googleHref(null, 'Lora', '') === '');
t('tidy: what they typed in the search, as a font\'s name is written', T.tidyName('  great   vibes ') === 'Great Vibes' && T.tidyName('EB garamond') === 'EB Garamond' && T.tidyName('lobster') === 'Lobster' && T.tidyName('') === '' && T.tidyName(null) === '');

// ---- typed words ----
t('clean: line breaks made plain, a tab made a space, other control characters dropped', T.cleanText('a\r\nb\rc\td\u0007e\u007ff\u0000') === 'a\nb\nc def', JSON.stringify(T.cleanText('a\r\nb\rc\td\u0007e\u007ff\u0000')));
t('clean: accents and emoji are left alone', T.cleanText('Héllo 🌊') === 'Héllo 🌊');
t('clean: cut at 2,000 letters, never through the middle of an emoji', T.cleanText(new Array(2500).join('x')).length === 2000 && T.cleanText(new Array(2000).join('x') + '🌊').length === 1999);
t('shown: capitals only when the box says so', T.shown({text: 'abc', upper: true}) === 'ABC' && T.shown({text: 'abc'}) === 'abc' && T.shown({}) === '');

// ---- a new text box, and changes to one ----
var N = T.newText(9, 2, '#ffffff', {text: 'Your words here', font: 'Playfair Display'});
t('new text: in the middle of the slide in view, a little above half way, 820 wide, one line tall', eq(N, {id: 9, type: 'text', text: 'Your words here', font: 'Playfair Display', size: 96, weight: 400, italic: false, upper: false, al: 'center', ls: 0, lh: 1.15, color: '#2a2622', x: 2290, y: 567, w: 820, h: 110.4}), N);
t('new text: white words on a dark background, dark words on a light one', T.newText(1, 0, '#111111', {}).color === '#ffffff' && T.newText(1, 0, '#f4efe6', {}).color === '#2a2622' && T.isDark('#707070') && !T.isDark('#909090') && !T.isDark('nonsense'));
t('new text: a default that is not a font\'s name becomes Georgia', T.newText(1, 0, '#ffffff', {font: 'a"b', text: 7}).font === 'Georgia' && T.newText(1, 0, '#ffffff', {font: 'a"b', text: 7}).text === '');
var b0 = TX();
t('style: size is held between 8 and 600, to two places', eq(T.style(b0, 'size', 1000), {size: 600}) && eq(T.style(b0, 'size', 1), {size: 8}) && eq(T.style(b0, 'size', '132.456'), {size: 132.46}) && T.style(b0, 'size', 'x') === null);
t('style: spacing between -20 and 200; lines between 0.5 and 3, to three places', eq(T.style(b0, 'ls', -99), {ls: -20}) && eq(T.style(b0, 'ls', 12), {ls: 12}) && eq(T.style(b0, 'lh', 1.40004), {lh: 1.4}) && eq(T.style(b0, 'lh', 9), {lh: 3}) && eq(T.style(b0, 'lh', 0), {lh: 0.5}));
t('style: bold is 700 or 400, never anything between', eq(T.style(b0, 'weight', 700), {weight: 700}) && eq(T.style(b0, 'weight', 500), {weight: 400}));
t('style: italic and capitals are yes or no', eq(T.style(b0, 'italic', true), {italic: true}) && eq(T.style(b0, 'italic', 'yes'), {italic: false}) && eq(T.style(b0, 'upper', true), {upper: true}));
t('style: left, center or right only', eq(T.style(b0, 'al', 'right'), {al: 'right'}) && T.style(b0, 'al', 'justify') === null);
t('style: a color is #rrggbb in small letters, or it is not a change', eq(T.style(b0, 'color', '#C4683F'), {color: '#c4683f'}) && T.style(b0, 'color', 'red') === null && T.style(b0, 'color', '#fff') === null);
t('style: a font must be a font\'s name', eq(T.style(b0, 'font', 'Lora'), {font: 'Lora'}) && T.style(b0, 'font', 'a;b') === null);
t('style: words are cleaned on their way in', eq(T.style(b0, 'text', 'a\tb\r\nc'), {text: 'a b\nc'}));
t('style: nothing else can be changed this way', T.style(b0, 'x', 5) === null && T.style(b0, 'id', 5) === null && T.style(b0, 'type', 'photo') === null);
T.useLimits({size: [10, 300], ls: [-5, 50], lh: [1, 2], text: 100, texts: 3, text_w_min: 120, text_h_max: 5000});
t('the Assistant\'s own limits are used once they arrive', eq(T.style(b0, 'size', 1000), {size: 300}) && eq(T.style(b0, 'ls', 99), {ls: 50}) && T.cleanText(new Array(500).join('x')).length === 100 && T.RULES.texts === 3 && T.RULES.wMin === 120 && T.layout(TX({size: 300, lh: 2, w: 10, text: 'a b c d e f g h i j k'}), m).h === 5000);
JSON.stringify(out);
"""


def osascript(js_file):
    import subprocess
    return subprocess.run(["/usr/bin/osascript", "-l", "JavaScript", str(js_file)], capture_output=True, text=True, timeout=120)


def check_type_page(case, work):
    """What the text and brand-color parts are made of, and the rules for words run by themselves."""
    sys.path.insert(0, str(SCRIPTS))
    import design_page as dp
    import design_js_brand
    import design_js_text
    page = dp.page_html("A kit")
    names = [n for n, _ in dp.SCRIPTS]
    src = {n: s for n, s in dp.SCRIPTS}

    case("text part: its three scripts go on the page after the strip's, the rules first, and before the page starts",
         all(n in names for n in ("DESIGN_TYPE_JS", "DESIGN_TEXT_JS", "DESIGN_BRAND_JS"))
         and page.index(src["DESIGN_EDIT_JS"]) < page.index(src["DESIGN_TYPE_JS"]) < page.index(src["DESIGN_TEXT_JS"]) < page.index(src["DESIGN_BRAND_JS"]) < page.index(dp.DESIGN_START_JS), names)
    case("text part: the page still names no address on the internet (Google's arrives with the state, from the Assistant's one constant)",
         not re.findall(r"https?://", page) and "googleapis" not in page and "gstatic" not in page)
    case("text part: no script comes from anywhere but the page itself", not re.search(r"<script[^>]*\ssrc=", page) and "createElement('script')" not in page and 'createElement("script")' not in page and "importScripts" not in page)
    case("text part: the only thing ever added to the page from outside is a stylesheet link", set(re.findall(r"createElement\('(link|script|iframe|object|embed)'\)", page)) <= {"link"} and "l.rel = 'stylesheet'" in src["DESIGN_TEXT_JS"])
    bare = re.sub(r"//[^\n]*", "", src["DESIGN_TYPE_JS"])
    case("the rules for words have no page in them (no document, no window but the one they hang themselves on)", "document" not in bare and bare.count("window") == 2 and "fetch(" not in bare, bare.count("window"))
    for n in ("DESIGN_TYPE_JS", "DESIGN_TEXT_JS", "DESIGN_BRAND_JS"):
        s = src[n]
        case(f"{n}: words only ever go on the page as text (no innerHTML, outerHTML, insertAdjacentHTML, document.write)",
             not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|DOMParser|createContextualFragment|srcdoc", s))
        case(f"{n}: nothing kept in the browser, no browser drag-and-drop, no clipboard, no navigator.onLine",
             not re.search(r"localStorage|sessionStorage|indexedDB|document\.cookie|draggable|dataTransfer|navigator\.clipboard|navigator\.onLine", s))
        case(f"{n}: no requestAnimationFrame and no setInterval; at most one timer, the safety net that gives up on a font",
             "requestAnimationFrame" not in s and "setInterval" not in s and s.count("setTimeout(") == (1 if n == "DESIGN_TEXT_JS" else 0), s.count("setTimeout("))
    t = src["DESIGN_TEXT_JS"]
    case("text part: every font string and font address is built by the checked helpers (fontString, familyString, googleHref)",
         len(re.findall(r"\.style\.font\s*=", t)) == 1 and "e.style.font = font" in t and "var font = T.fontString(b, b.size)" in t
         and all("T.familyString(" in ln for ln in t.splitlines() if "style.fontFamily" in ln)
         and re.findall(r"\.href\s*=\s*([^;]+);", t) == ["href", "href + '&text=' + Date.now().toString(36)"]
         and len(re.findall(r"var href = T\.googleHref\(fontsOf\(\)\.google, ", t)) == 2 and len(re.findall(r"\bhref\b\s*=", t)) == 4)
    case("text part: the one place a name is put between quotes by hand is after the family has passed the check (the 'is it here' question)",
         t.count("'400 40px \"' + name + '\"'") == 1 and t.index("if (!T.fontOk(name)) return 'failed';") < t.index("function settled("))
    case("text part: a font file's key is checked before it goes into an address", "/^[A-Za-z0-9-]{1,60}$/.test(f.file" in t)
    for css_name, css in (("text styles", design_js_text.DESIGN_TEXT_CSS), ("brand-color styles", design_js_brand.DESIGN_BRAND_CSS)):
        case(f"{css_name}: no backslash, fetch nothing (no url(...), no @font-face, no @import), name no font, light only",
             "\\" not in css and "url(" not in css and "@font-face" not in css and "@import" not in css and "prefers-color-scheme" not in css
             and not re.search(r"font-family|Georgia|Fraunces|googleapis|gstatic", css))
        used = set(re.findall(r"\.([a-zA-Z][\w-]*)", css))
        import arrange_page
        theirs = set(re.findall(r"\.([a-zA-Z][\w-]*)", arrange_page.CSS)) - {"on"}
        mine = {c for c in used if c.startswith(("tx-", "fp-", "bc-")) or c in ("words", "blank", "small")}
        case(f"{css_name}: no class of its own is one the pickers already use for something else", not (mine & theirs), sorted(mine & theirs))
    case("text part: its styles are on the page, after the strip's", page.index(dp.DESIGN_CSS) < page.index(design_js_text.DESIGN_TEXT_CSS) < page.index(design_js_brand.DESIGN_BRAND_CSS))
    for f in MINE:
        text = (SCRIPTS / f).read_text(encoding="utf-8")
        code_only = "\n".join(ln.split("#")[0] for ln in re.sub(r'"""(?:.|\n)*?"""', '""', text).splitlines())
        case(f"{f}: runs no Mac-only program and uses no Mac-only call", not re.search(r"\b(sips|osascript|chflags|caffeinate|fcntl|subprocess)\b|/Volumes|%-d", code_only))
        case(f"{f}: Python never formats over the JavaScript (raw strings, joined as they are)",
             not re.search(r'JS\s*(%|\.format\()', text) and not re.search(r'\bf(r|R)?"""', text) and 'JS = r"""' in text)

    f = work / "design-type-tests.js"
    f.write_text("var TYPE_SRC = " + json.dumps(dp.SCRIPTS[names.index("DESIGN_TYPE_JS")][1]) + ";\n" + TYPE_TESTS_JS, encoding="utf-8")
    r = osascript(f)
    try:
        got = json.loads(r.stdout) if r.returncode == 0 else None
    except ValueError:
        got = None
    if not case("the rules for words ran to the end under osascript", got is not None and len(got) >= 45, (r.stderr or r.stdout)[-400:]):
        return
    for name, ok, detail in got:
        case("words: " + name, ok, detail)


# ---------------------------------------------------------------------------------------------------------
# the real page in a hidden Chrome
# ---------------------------------------------------------------------------------------------------------

# Run in the page: everything about a text box as the SCREEN has it, beside what the shared function says.
PROBE_JS = r"""
window.__probe = function(id){
  var D = Designer, T = D.type.T, b = D.M.find(D.st, id), s = D.scale;
  var node = document.querySelector("#strip .blk[data-id='" + id + "']");
  if (!b || !node) return null;
  var L = D.type.layout(b), nr = node.getBoundingClientRect(), sr = document.getElementById('strip').getBoundingClientRect();
  var dom = Array.prototype.map.call(node.querySelectorAll('.tx-ln'), function(e){
    var cs = getComputedStyle(e), rg = document.createRange(), r = e.getBoundingClientRect();
    rg.selectNodeContents(e);
    var rr = rg.getBoundingClientRect();
    var mark = document.createElement('span');
    mark.style.cssText = 'display:inline-block;width:0;height:0';
    e.appendChild(mark);
    var base = mark.getBoundingClientRect().bottom;
    mark.remove();
    return {t: e.textContent, left: e.textContent ? (rr.left - nr.left) / s : null, w: e.textContent ? rr.width / s : 0, top: (r.top - nr.top) / s, base: (base - nr.top) / s,
            family: cs.fontFamily, weight: cs.fontWeight, slant: cs.fontStyle, ls: cs.letterSpacing, color: cs.color, size: cs.fontSize, lh: cs.lineHeight, ws: cs.whiteSpace};
  });
  // an independent ruler: the browser's own layout of a piece of text (not the canvas the page measures with)
  var sp = document.createElement('span');
  sp.style.cssText = 'position:absolute;left:-99999px;top:0;white-space:pre;visibility:hidden';
  sp.style.font = T.fontString(b, b.size); sp.style.letterSpacing = (b.ls || 0) + 'px';       // kerning left as the browser has it
  document.body.appendChild(sp);
  var ruler = function(t){ sp.textContent = t; return sp.getBoundingClientRect().width; };
  var byDom = T.wrapLines(T.shown(b), b.w, ruler).map(function(l){ return l.t; });
  sp.remove();
  // what a saved slide would be told to draw (a stand-in canvas that writes down each call)
  var calls = [], k = Math.floor((b.x + b.w / 2) / 1080);
  var ctx = {save: function(){}, restore: function(){}, fillText: function(t, x, y){ calls.push({t: t, x: x, y: y, font: this.font, ls: this.letterSpacing, kern: this.fontKerning, fill: this.fillStyle, baseline: this.textBaseline}); }};
  D.type.drawText(ctx, b, k * 1080, 0);
  return {b: b, lines: L.lines, lh: L.lh, h: L.h, base: L.base, dom: dom, byDom: byDom, calls: calls, slideLeft: k * 1080,
          node: {x: (nr.left - sr.left) / s, y: (nr.top - sr.top) / s, w: nr.width / s, h: nr.height / s},
          status: D.type.status(b), hidden: getComputedStyle(node.firstChild).visibility === 'hidden'};
};
// how wide a line of letters is in a family (with Georgia behind it), and in Georgia alone
window.__wide = function(name){
  var c = document.createElement('canvas').getContext('2d'), s = 'Handgloves & Quartz 0123';
  c.font = '400 80px "' + name + '", Georgia, serif'; var a = c.measureText(s).width;
  c.font = '400 80px Georgia, serif'; var g = c.measureText(s).width;
  return {own: a, georgia: g};
};
// a real canvas: draw one text box as a saved slide would, and say where the ink is
window.__ink = function(id){
  var D = Designer, b = D.M.find(D.st, id), k = Math.floor((b.x + b.w / 2) / 1080);
  var cv = document.createElement('canvas'); cv.width = 1080; cv.height = 1350;
  var ctx = cv.getContext('2d'); ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, 1080, 1350);
  D.type.drawText(ctx, D.M.merge(b, {color: '#000000'}), k * 1080, 0);
  var d = ctx.getImageData(0, 0, 1080, 1350).data, x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1, n = 0;
  for (var y = 0; y < 1350; y++) for (var x = 0; x < 1080; x++) { if (d[(y * 1080 + x) * 4] < 128) { n++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } }
  return {n: n, x0: x0, y0: y0, x1: x1, y1: y1, bx: b.x - k * 1080, by: b.y, bw: b.w, bh: b.h};
};
"""


def check_type_browser(case, work, port, make_kit, Server, post, get_json):
    sys.path.insert(0, str(ROOT / "tests"))
    import chrome_drive as cd
    if not cd.find_chrome():
        print("SKIP  the real-browser checks of text, fonts and brand colors: no Chrome on this computer", flush=True)
        return
    target = work / "text"
    ok, out = make_kit(target, "Fake dunes", 9)
    if not case("text browser: the pretend kit was made (tests/fake_kit.py)", ok, out):
        return
    studio = target / "studio"
    env = dict(os.environ, STUDIO_HOME=str(studio))
    for k in ("DESIGN_TEST_STOP", "DESIGN_TEST_STOP_ONCE", "ARRANGE_TEST_STOP", "ARRANGE_TEST_STOP_ONCE"):
        env.pop(k, None)
    kit_name = "2026-11-01 Fake dunes"
    kit = target / "The Assistant" / "Your Content" / kit_name
    KQ = quote(kit_name)
    designs = kit / ".kit" / "designs"
    rec_before = (kit / ".kit" / "kit.json").read_bytes()
    photos_before = sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in (kit / "Photos").iterdir())
    brand_file, fonts_file = studio / "brand.json", studio / "design-fonts.json"

    srv = Server(env, port)
    P = srv.start()
    scratch = work / "chrome-text"
    scratch.mkdir(parents=True, exist_ok=True)
    tokens = [0]
    FRAME = {"id": 1, "n": 2, "x": 0, "y": 0, "w": W, "h": H, "ox": 0.5, "oy": 0.5, "zoom": 1}

    def TB(i, **more):
        b = {"id": i, "type": "text", "text": "Your words here", "font": "Inter", "size": 96, "weight": 400, "italic": False, "upper": False,
             "al": "center", "ls": 0, "lh": 1.15, "color": "#2a2622", "x": 1210, "y": 300, "w": 820, "h": 110}
        b.update(more)
        return b

    try:
        with cd.Chrome(work=scratch, size=(1280, 900)) as c:
            base = f"http://127.0.0.1:{P}"

            def J(expr):
                return json.loads(c.js("JSON.stringify(" + expr + ")"))

            def st():
                return J("Designer.st")

            def sel():
                return J("Designer.selected()")

            def ready(seconds=15):
                c.wait_for("window.Designer && Designer.type && Designer.st && Designer.S && document.querySelectorAll('#thumbs .th').length === Designer.S.total", seconds,
                           tell="document.body.innerText.slice(0, 300)")
                c.js(PROBE_JS + "; true")

            def did():
                return c.js("Designer.design.id")

            def disk(i=None):
                return json.loads((designs / f"{i or did()}.json").read_text(encoding="utf-8"))

            def settled(seconds=10):
                try:
                    c.wait_for("Designer.save.idle() && document.getElementById('d-status').textContent === 'Saved'", seconds)
                except cd.Timeout:
                    return False
                return disk()["state"] == st()

            def fonts_in(seconds=12):
                """Every text box's font has arrived or been given up on, and the heights follow the lines."""
                try:
                    c.wait_for("Designer.st.blocks.every(function(b){ return b.type !== 'text' || Designer.type.status(b) !== 'wait'; }) && Designer.type.fit(Designer.st) === Designer.st", seconds)
                    return True
                except cd.Timeout:
                    return False

            def blk(state, i):
                return next((b for b in state["blocks"] if b["id"] == i), None)

            def probe(i):
                return J(f"__probe({i})")

            def centre(i, fx=0.5, fy=0.5):
                r = c.rect(f"#strip .blk[data-id='{i}']")
                return (r["x"] + r["w"] * fx, r["y"] + r["h"] * fy)

            def handle(which):
                r = c.rect(f"#over .selbox .h.{which}")
                return (r["cx"], r["cy"])

            def new_design(label, state=None, name=None):
                tokens[0] += 1
                body = {"kit": kit_name, "token": f"textcheck{tokens[0]:04d}"}
                if state is not None:
                    body.update(stamp=get_json(P, f"/design-state?kit={KQ}")[1]["stamp"], state=state)
                if name:
                    body["name"] = name
                code, out = post(P, "/design-new", body)
                if code != 200 or not out or not out.get("ok"):
                    case(f"text browser [{label}]: a new design was made for this part", False, (code, out))
                    raise RuntimeError("no design")
                return out["design"]["id"]

            def open_design(i):
                c.open(f"{base}/design.html?kit={KQ}&design={i}")
                ready()

            def pick_font(name):
                c.click("#font-btn")
                c.wait_for("!document.getElementById('font-panel').hidden", 3)
                c.js("(function(){ var b = document.querySelector(\"#font-list .fp-it[data-font='%s']\"); b.scrollIntoView({block: 'center'}); })()" % name)
                c.click(f"#font-list .fp-it[data-font='{name}']")

            def google_requests():
                return [u for u in c.outside_requests() if "fonts.googleapis.com" in u or "fonts.gstatic.com" in u]

            # ================= is there internet? =================
            open_design(new_design("start"))
            online = bool(c.js("Designer.type.fonts.reach()"))
            if not online:
                print("SKIP  Google Fonts cannot be reached from this computer: the checks that load a font from Google are skipped", flush=True)
            case("start: a design with no words asks nothing of any address but the Assistant's (the question above aside)",
                 all("&text=" in u and "fonts.googleapis.com" in u for u in c.outside_requests()), c.outside_requests()[:3])
            case("start: the plugin's own fonts are declared from the Assistant's own files, and none has been fetched yet (nothing uses one)",
                 c.js("(function(){ var n = 0, loaded = 0; document.fonts.forEach(function(f){ n++; if (f.status === 'loaded') loaded++; }); return n >= 12 && loaded === 0; })()")
                 and not any("/design-font-file" in r["url"] for r in c.requests))
            case("start: + Add text and the Brand colors group are in the row of tools, Brand colors beside Background",
                 c.count("#tools-main #add-text") == 1 and c.js("document.getElementById('g-bg').nextElementSibling.id") == "g-brand" and c.text("#brand-label") == "Brand colors")
            case("start: with nothing selected the text controls are not shown", c.js("document.getElementById('sel-text').hidden && document.getElementById('sel-style').hidden && document.getElementById('sel-color').hidden") is True)

            # ================= add text, type, style every way =================
            # (the Assistant's own families only, so this part is the same with or without the internet)
            c.set_offline(True)
            D1 = new_design("type")
            open_design(D1)
            n0 = len(st()["blocks"])
            c.js("document.getElementById('stage').scrollLeft = 0")
            c.click("#add-text")
            b = sel()
            case("add text: a text box is added in the middle of the slide in view, selected, on top, with the Assistant's starting words",
                 b is not None and b["type"] == "text" and b["text"] == "Your words here" and len(st()["blocks"]) == n0 + 1 and st()["blocks"][-1]["id"] == b["id"]
                 and b["w"] == 820 and b["y"] == 567 and (b["x"] - 130) % W == 0 and b["x"] // W == c.js("Designer.viewSlide()"), b)
            tid = b["id"]
            case("add text: the cursor is in the words box, with the starting words selected so typing replaces them",
                 c.js("document.activeElement.id") == "t-words" and c.js("(function(){ var t = document.getElementById('t-words'); return t.selectionStart === 0 && t.selectionEnd === t.value.length && t.value === 'Your words here'; })()"))
            case("add text: the bar now shows the text controls, not the photo ones",
                 c.js("!document.getElementById('sel-text').hidden && !document.getElementById('sel-style').hidden && !document.getElementById('sel-color').hidden && document.getElementById('sel-photo').hidden && document.getElementById('sel-crop').hidden && !document.getElementById('sel-all').hidden") is True)
            pick_font("Inter")
            case("font: a family the plugin carries is picked from the list, and the list closes", sel()["font"] == "Inter" and c.js("document.getElementById('font-panel').hidden") is True, sel()["font"])
            fonts_in()
            c.click("#t-words")
            c.key("Mod+A")
            c.type_text("Héllo wörld 🌊\nsecond line")
            want_text = "Héllo wörld 🌊\nsecond line"
            case("type: two lines with accents and an emoji arrive in the design exactly as typed", sel()["text"] == want_text, sel()["text"])
            p = probe(tid)
            case("type: the strip shows them at once, as two lines, in the font picked",
                 [d["t"] for d in p["dom"]] == ["Héllo wörld 🌊", "second line"] and p["status"] == "ready" and all("Inter" in d["family"] for d in p["dom"]), p["dom"])
            case("type: the box's height follows the lines (2 lines of 96 at 1.15 = 220.8)", p["b"]["h"] == 220.8 and abs(p["node"]["h"] - 220.8) < 0.3, (p["b"]["h"], p["node"]))
            case("type: saved as typed", settled() and blk(disk()["state"], tid)["text"] == want_text)
            # every style, one after the other
            pick_font("Cormorant Garamond")
            c.set_value("#t-size", "150")
            c.set_value("#t-size-n", "132.5")
            c.click("#selbar button[data-t='weight']")
            c.click("#selbar button[data-t='italic']")
            c.click("#selbar button[data-t='upper']")
            c.click("#selbar button[data-t='al'][data-v='left']")
            left_then = sel()["al"]
            c.click("#selbar button[data-t='al'][data-v='right']")
            c.set_value("#t-ls", "12")
            c.set_value("#t-lh", "140")
            c.set_value("#t-color", "#c4683f")
            fonts_in()
            b = sel()
            p = probe(tid)
            n_lines = len(p["dom"])
            want = {"id": tid, "type": "text", "text": want_text, "font": "Cormorant Garamond", "size": 132.5, "weight": 700, "italic": True, "upper": True,
                    "al": "right", "ls": 12, "lh": 1.4, "color": "#c4683f", "x": b["x"], "y": 567, "w": 820, "h": round(n_lines * 132.5 * 1.4, 2)}
            case("style: font, size (slider then number), bold, italic, capitals, left then right, spacing, lines, color: the design holds exactly that",
                 b == want and left_then == "left" and n_lines >= 2, (b, want))
            case("style: the file on the drive holds exactly that", settled() and blk(disk()["state"], tid) == want, blk(disk()["state"], tid))
            d0 = p["dom"][0]
            case("style: the screen shows it: capitals, the family, bold, slanted, 12 px between letters, the color, the size, lines 1.4 apart",
                 d0["t"] == d0["t"].upper() and "".join(d["t"] for d in p["dom"]).replace(" ", "") == want_text.upper().replace(" ", "").replace("\n", "")
                 and "Cormorant Garamond" in d0["family"] and d0["weight"] == "700" and d0["slant"] == "italic" and d0["ls"] == "12px"
                 and d0["color"] == "rgb(196, 104, 63)" and d0["size"] == "132.5px" and abs(float(d0["lh"][:-2]) - 185.5) < 0.01 and d0["ws"] == "pre", d0)
            case("style: right-aligned lines end at the box's right edge", all(abs(d["left"] + d["w"] - 820) < 0.8 for d in p["dom"] if d["t"]), [(d["left"], d["w"]) for d in p["dom"]])
            case("style: the buttons show what is on (B, I, AA, Right) and the boxes hold the numbers",
                 J("Array.prototype.map.call(document.querySelectorAll('#selbar button[data-t].on'), function(x){ return x.dataset.t + (x.dataset.v || ''); })") == ["weight", "italic", "upper", "alright"]
                 and c.js("document.getElementById('t-size-n').value") == "132.5" and c.js("document.getElementById('t-ls').value") == "12" and c.js("document.getElementById('t-lh').value") == "140"
                 and c.js("document.getElementById('t-color').value") == "#c4683f" and c.text("#font-btn").startswith("Cormorant Garamond"))
            case("style: the family's bold and italic came from the Assistant's own files (no internet was there to ask)",
                 any("/design-font-file?f=CormorantGaramond-SemiBoldItalic" in r["url"] for r in c.requests) and any("/design-font-file?f=Inter-Regular" in r["url"] for r in c.requests)
                 and not any(("family=Cormorant" in u or "family=Inter" in u) and "&text=" not in u for u in google_requests()), [r["url"] for r in c.requests if "font" in r["url"]][:6])
            # a number outside the limits, and words no key should be able to send
            c.set_value("#t-size-n", "5")
            case("style: a size the Assistant would refuse (5) is not taken", sel()["size"] == 132.5)
            c.set_value("#t-words", "tab\there\u0007 and\r\nnew")
            case("type: a pasted tab becomes a space, a line break is made plain and a stray control character is dropped (the Assistant refuses them)",
                 sel()["text"] == "tab here and\nnew" and c.js("document.getElementById('t-words').value") == "tab here and\nnew", sel()["text"])
            case("type: ...and that saves", settled())

            # ================= HTML-looking words stay words =================
            n_req = len(c.requests)
            evil = "<img src=x onerror=window.__pwned=1><script>window.__pwned=2</script>&amp;"
            c.set_value("#t-words", evil)
            p = probe(tid)
            case("markup: words that look like HTML show as plain characters on the strip",
                 "".join(d["t"] for d in p["dom"]).replace(" ", "") == evil.upper().replace(" ", "") and c.count("#strip .blk.words img") == 0 and c.count("#strip .blk.words script") == 0
                 and c.js(f"document.querySelector(\"#strip .blk[data-id='{tid}']\").querySelectorAll('*').length") == 1 + len(p["dom"]), [d["t"] for d in p["dom"]])
            case("markup: nothing in them ran, the page has no error, and no request came of it",
                 c.js("typeof window.__pwned") == "undefined" and c.page_errors() == [] and not any(r["url"].rstrip("/").endswith("/x") for r in c.requests[n_req:]), c.page_errors())
            case("markup: saved as the same plain characters", settled() and blk(disk()["state"], tid)["text"] == evil)
            c.click("#font-btn")
            c.click("#font-search")
            c.type_text("<b>x")
            case("markup: the same in the font search: the offer to load it shows the characters, and a name like that is never asked for",
                 c.text("#font-list .fp-load") == "Load “<b>x” from Google Fonts" and c.count("#font-list b") == 0)
            n_req = len(c.requests)
            c.click("#font-list .fp-load")
            case("markup: pressing it says it couldn't be found, at once, with nothing asked of anyone",
                 c.text("#font-list .fp-load") == "Couldn’t find “<b>x” on Google Fonts. Check the spelling." and len(c.requests) == n_req, c.text("#font-list .fp-load"))
            c.key("Escape")
            case("font list: Escape closes it", c.js("document.getElementById('font-panel').hidden") is True)

            # ================= undo walks back through the text edits =================
            D2 = new_design("undo")
            open_design(D2)
            c.js("document.getElementById('stage').scrollLeft = 0")
            trail = [st()]
            c.click("#add-text"); trail.append(st())
            pick_font("Montserrat"); fonts_in(); trail.append(st())
            c.click("#t-words"); c.key("Mod+A"); c.type_text("One two"); trail.append(st())
            c.click("#selbar button[data-t='weight']"); trail.append(st())
            c.click("#selbar button[data-t='al'][data-v='left']"); trail.append(st())
            c.js("document.getElementById('t-size').focus(); true"); c.key("ArrowRight"); trail.append(st())          # a real key on the slider
            c.set_value("#t-color", "#336699"); trail.append(st())
            case("undo: (seven edits were made, each changing the design)", all(trail[i] != trail[i + 1] for i in range(7)), [len(x["blocks"]) for x in trail])
            case("undo: typing a run of letters is one step, not one a letter", blk(trail[3], trail[1]["blocks"][-1]["id"])["text"] == "One two")
            walked = []
            for i in range(7):
                c.click("#undo")
                walked.append(st() == trail[6 - i])
            case("undo: seven presses walk back through color, size, side, bold, the words, the font and the box itself, one at a time", walked == [True] * 7, walked)
            case("undo: ...and the design is as it began, saved, with Undo off again", st() == trail[0] and settled() and c.js("document.getElementById('undo').disabled") is True)

            # ================= move, resize (width only), layers, keys, snapping =================
            D3 = new_design("box", {"slides": 3, "bg": "#f4efe6", "blocks": [dict(FRAME), TB(2, text="one two three four five six seven eight nine ten", font="Inter", w=820, x=1210, y=300)]})
            open_design(D3)
            fonts_in()
            c.js("document.getElementById('stage').scrollLeft = 0")
            p = probe(2)
            lines0 = len(p["dom"])
            case("open: a text box whose height was only a stand-in (110) is given its real height from its lines, and that is saved",
                 lines0 >= 2 and p["b"]["h"] == round(lines0 * 96 * 1.15, 2) and settled() and blk(disk()["state"], 2)["h"] == p["b"]["h"], (lines0, p["b"]["h"]))
            s = c.js("Designer.scale")
            c.click(centre(2))
            hs = J("Array.prototype.map.call(document.querySelectorAll('#over .selbox .h'), function(h){ var r = h.getBoundingClientRect(), b = document.querySelector('#over .selbox').getBoundingClientRect(); return [h.dataset.h, getComputedStyle(h).display !== 'none', Math.round(r.top + r.height / 2 - (b.top + b.height / 2)), getComputedStyle(h).cursor]; })")
            case("select: a press on the words selects the box; it has a handle in the middle of each side (a text box changes in width only) and the help line says how",
                 c.js("Designer.sel") == 2 and [h[:3] for h in hs if h[1]] == [["tl", True, 0], ["br", True, 0]] and all(h[3] == "ew-resize" for h in hs if h[1])
                 and c.text("#selhint") == "Text. Type in the box next to “Text” here, or double-click the words. Drag to move it, or pull a side to make it wider or narrower.", (hs, c.text("#selhint")))
            c.js("document.activeElement && document.activeElement.blur()")
            c.double_click(centre(2))
            case("double-click on the words puts the cursor in the words box", c.js("document.activeElement.id") == "t-words")
            c.key("Escape")
            case("Escape in the words box leaves it (the box stays selected)", c.js("document.activeElement.id") != "t-words" and c.js("Designer.sel") == 2)
            before = sel()
            x, y = centre(2)
            c.drag((x, y), (x + 31, y + 17), steps=5, alt=True)
            b = sel()
            case("move: dragging the words moves the box and changes nothing else about it",
                 abs(b["x"] - (before["x"] + round(31 / s, 2))) < 0.02 and abs(b["y"] - (before["y"] + round(17 / s, 2))) < 0.02 and dict(b, x=0, y=0) == dict(before, x=0, y=0), b)
            # pull the right-hand side in: narrower, more lines, taller; the top and the left stay
            before = sel()
            hx, hy = handle("br")
            c.drag((hx, hy), (hx - 90, hy + 40), steps=6, alt=True, release=False)
            mid = probe(2)
            sb = c.rect("#over .selbox")
            nb = c.rect("#strip .blk[data-id='2']")
            case("resize: while a side is pulled the lines re-break on screen and the blue box follows them, and the design is not changed yet",
                 len(mid["dom"]) > lines0 and abs(sb["h"] - nb["h"]) < 0.8 and abs(sb["w"] - nb["w"]) < 0.8 and mid["b"] == before, (len(mid["dom"]), sb, nb))
            c.mouse_release()
            b = sel()
            p = probe(2)
            case("resize: on letting go only the WIDTH changed by the pull; the height is what the lines come to; the left and the top stayed",
                 abs(b["w"] - (before["w"] - round(90 / s, 2))) < 0.02 and b["x"] == before["x"] and b["y"] == before["y"]
                 and b["h"] == round(len(p["dom"]) * 96 * 1.15, 2) and len(p["dom"]) > lines0, (b, len(p["dom"])))
            c.click("#undo")
            case("resize: one Undo step puts the width AND the height back", sel() == before, sel())
            hx, hy = handle("tl")
            c.drag((hx, hy), (hx + 5000, hy), steps=4, alt=True)
            case("resize: a text box is never narrower than 80", sel()["w"] == 80 and sel()["h"] == round(len(probe(2)["dom"]) * 96 * 1.15, 2), sel())
            p = probe(2)
            case("resize: in a box that narrow a word too long for it is cut, and nothing sticks out of the box",
                 len(p["dom"]) > 10 and all(d["w"] <= 80.6 or len(d["t"]) == 1 for d in p["dom"]), [d["t"] for d in p["dom"]][:6])
            c.click("#undo")
            press = lambda a: c.click(f"#selbar button[data-a='{a}']")      # noqa: E731
            press("center")
            b = sel()
            case("Center on slide centres the box on its slide", abs((b["x"] % W) - (W - b["w"]) / 2) < 0.011, b["x"])
            press("back")
            order1 = [x["id"] for x in st()["blocks"]]
            press("front")
            order2 = [x["id"] for x in st()["blocks"]]
            press("dup")
            dup = sel()
            case("Send back, Bring forward, Duplicate work on a text box (stacking is the order of the list)",
                 order1 == [2, 1] and order2 == [1, 2] and dup["id"] != 2 and dup["text"] == b["text"] and dup["x"] == b["x"] + 60 and len(st()["blocks"]) == 3, (order1, order2))
            fonts_in()
            c.key("Delete")
            case("Delete removes the selected text box (the copy)", len(st()["blocks"]) == 2 and c.js("Designer.sel") is None)
            c.click(centre(2))
            b = sel()
            c.key("ArrowRight"); c.key("Shift+ArrowDown")
            case("arrow keys nudge a text box (5, and 50 with Shift)", sel()["x"] == b["x"] + 5 and sel()["y"] == b["y"] + 50, sel())
            # snapping: drop it a few pixels short of a sixth of a slide
            b = sel()
            goal = 1260                                 # slide 2's first sixth
            x, y = centre(2)
            c.drag((x, y), (x + (goal - 4 - b["x"]) * s, y), steps=6)
            case("snapping: let go a little short of a sixth of a slide, a text box snaps onto it like a photo", abs(sel()["x"] - goal) < 0.011, sel()["x"])
            case("box: all of that is saved", settled())
            # the words emptied: the box stays findable
            c.set_value("#t-words", "")
            c.click(centre(1, 0.1, 0.9))
            case("empty words: the box is one line tall and shows a dashed outline on screen so it can be found",
                 blk(st(), 2)["text"] == "" and blk(st(), 2)["h"] == 110.4 and c.count("#strip .blk.words.blank[data-id='2']") == 1)

            # ================= bold only where the family has it =================
            D4 = new_design("bold", {"slides": 2, "bg": "#ffffff", "blocks": [TB(1, font="Montserrat", weight=700, x=130, y=300)]})
            open_design(D4)
            fonts_in()
            c.click(centre(1))
            case("bold: offered for a family that has it (and on, for a bold box)", c.js("(function(){ var b = document.querySelector(\"#selbar button[data-t='weight']\"); return !b.disabled && b.classList.contains('on'); })()"))
            pick_font("Fraunces")
            fonts_in()
            case("bold: picking a family with no bold takes bold off the box, and the B button says why it is off",
                 sel()["font"] == "Fraunces" and sel()["weight"] == 400
                 and J("(function(){ var b = document.querySelector(\"#selbar button[data-t='weight']\"); return [b.disabled, b.title]; })()") == [True, "This font has no bold."], sel())
            pick_font("Inter")
            c.click("#selbar button[data-t='weight']")
            case("bold: back on a family that has it, B works again", sel()["weight"] == 700)

            # ================= the same breaks on screen as the shared function gives =================
            sample = "Golden hour at the dunes, où l'été s'achève: a very long sentence to wrap, with a supercalifragilistic word and a wave 🌊 at the end"
            wrap_fonts = ["Cormorant Garamond", "Inter", "Montserrat"]
            widths = [300, 517, 820, 1400]
            blocks, i = [], 0
            for fi, f in enumerate(wrap_fonts):
                for wi, wv in enumerate(widths):
                    i += 1
                    blocks.append(TB(i, text=sample, font=f, w=wv, size=[64, 96, 41.5][fi], ls=[0, 6, -2][fi], weight=[400, 700, 400][fi], italic=fi == 0, upper=fi == 1,
                                     al=["left", "center", "right"][fi], lh=[1.15, 1.4, 0.9][fi], x=40 + wi * 800, y=40 + fi * 100))
            D5 = new_design("wrap", {"slides": 4, "bg": "#ffffff", "blocks": blocks})
            open_design(D5)
            case("wrap: (three families, four widths each: every font arrived)", fonts_in(20) and all(J(f"Designer.type.status(Designer.st.blocks[{k}])") == "ready" for k in range(12)))
            same_break, same_ruler, fits, widths_ok, places_ok, base_ok, calls_ok, heights_ok, shown_ok = [], [], [], [], [], [], [], [], []
            for b in blocks:
                p = probe(b["id"])
                dom = [d["t"] for d in p["dom"]]
                fn = [ln["t"] for ln in p["lines"]]
                same_break.append(dom == fn)
                same_ruler.append(p["byDom"] == dom)
                fits.append(all(d["w"] <= b["w"] + 0.6 for d in p["dom"]))
                widths_ok.append(all(abs(d["w"] - ln["w"]) < 0.1 for d, ln in zip(p["dom"], p["lines"]) if d["t"]))
                places_ok.append(all(abs(d["left"] - ln["x"]) < 0.15 and abs(d["top"] - k * p["lh"]) < 0.15 for k, (d, ln) in enumerate(zip(p["dom"], p["lines"])) if d["t"]))
                base_ok.append(p["base"] is not None and all(abs(d["base"] - (k * p["lh"] + p["base"])) < 1.01 for k, d in enumerate(p["dom"])))
                want_calls = [(ln["t"], b_x, k) for k, ln in enumerate(p["lines"]) if ln["t"] for b_x in [p["b"]["x"] - p["slideLeft"] + ln["x"]]]
                calls_ok.append(len(p["calls"]) == len(want_calls) and all(
                    cl["t"] == t and abs(cl["x"] - x) < 0.001 and abs(cl["y"] - (p["b"]["y"] + k * p["lh"] + p["base"])) < 0.001 and cl["baseline"] == "alphabetic"
                    and f'"{b["font"]}"' in cl["font"] and cl["ls"] == f'{b["ls"]}px' and cl["kern"] == "normal" and cl["fill"] == "#2a2622" for cl, (t, x, k) in zip(p["calls"], want_calls)))
                heights_ok.append(p["b"]["h"] == round(len(dom) * b["size"] * b["lh"], 2) and abs(p["node"]["h"] - p["b"]["h"]) < 0.5)
                shown_ok.append("".join(dom).replace(" ", "") == (sample.upper() if b["upper"] else sample).replace(" ", ""))
            case("wrap: for three fonts at four widths the line breaks ON SCREEN are the breaks the shared function gives (both read)", all(same_break), same_break)
            case("wrap: ...and they are the breaks the browser's own layout of each piece gives (a second ruler, not the canvas)", all(same_ruler), same_ruler)
            case("wrap: no line on screen is wider than its box", all(fits), fits)
            case("wrap: each line is as wide on screen as it was measured", all(widths_ok), widths_ok)
            case("wrap: each line sits where the function put it (left, center or right; one line height apart)", all(places_ok), places_ok)
            case("wrap: the letters stand on the line the saved slide will draw them on (within a slide pixel)", all(base_ok), base_ok)
            case("wrap: what a saved slide is told to draw is the same lines at the same places, in the same font, spacing and color", all(calls_ok), calls_ok)
            case("wrap: every box is as tall as its lines, and every letter that went in is on screen", all(heights_ok) and all(shown_ok), (heights_ok, shown_ok))
            ink = J("__ink(5)")
            case("wrap: drawn on a real canvas the words land inside their box's width and from its top down (the ink is where the box is)",
                 ink["n"] > 2000 and ink["x0"] >= ink["bx"] - 12 and ink["x1"] <= ink["bx"] + ink["bw"] + 12 and ink["y0"] >= ink["by"] - 30 and ink["y0"] <= ink["by"] + 96 * 1.4
                 and ink["y1"] <= min(1349, ink["by"] + ink["bh"] + 40), ink)
            case("wrap: opening that design saved the real heights (once per font that arrived, at most) and nothing more", settled() and 1 <= disk()["rev"] <= 3, disk()["rev"])

            # ================= no internet =================
            # (still cut off: 127.0.0.1 answers, nothing else does)
            D6 = new_design("offline", {"slides": 3, "bg": "#ffffff", "blocks": [dict(FRAME), TB(2, text="Carried by the Assistant", font="Montserrat", x=1210, y=200),
                                                                                  TB(3, text="Needs the internet", font="Lora", x=1210, y=600)]})
            open_design(D6)
            case("no internet: the page opens and works", fonts_in(20) and c.count("#strip .blk") == 3 and c.page_errors() == [], c.page_errors())
            wide = J("__wide('Montserrat')")
            case("no internet: a family the plugin carries draws in its own face (a line measures differently from Georgia)",
                 J("Designer.type.status(Designer.st.blocks[1])") == "ready" and abs(wide["own"] - wide["georgia"]) > 20 and c.js("document.fonts.check('400 40px \"Montserrat\"')") is True, wide)
            wide = J("__wide('Lora')")
            p = probe(3)
            case("no internet: a Google family falls back to Georgia (it measures exactly as Georgia does), and is drawn, not left blank",
                 p["status"] == "fallback" and abs(wide["own"] - wide["georgia"]) < 0.01 and not p["hidden"] and [d["t"] for d in p["dom"]] == ["Needs the internet"], (p["status"], wide))
            try:
                c.wait_for("document.getElementById('l-fonts').textContent.indexOf('No internet') === 0", 15)
            except cd.Timeout:
                pass
            case("no internet: one plain line on the page says so",
                 c.text("#l-fonts") == "No internet right now, so “Lora” is showing as Georgia. It will come back when you’re online." and c.js("document.getElementById('l-fonts').hidden") is False, c.text("#l-fonts"))
            got = json.loads(c.js("Designer.type.fonts.ready().then(function(r){ return JSON.stringify(r); })"))
            case("no internet: asked 'are all fonts ready, and which fell back', the page answers: ready, Lora fell back (never a silent wrong font in a saved slide)",
                 got == {"ready": True, "fellBack": ["Lora"]}, got)
            c.click(centre(3))
            case("no internet: the help line for that box says it too", c.text("#selhint").startswith("This text is showing in Georgia for now, because “Lora” couldn’t be loaded."), c.text("#selhint"))
            c.click("#font-btn")
            try:
                c.wait_for("!document.getElementById('font-line').hidden", 15)
            except cd.Timeout:
                pass
            case("no internet: the font list still opens, with every family in it, the plugin's own marked",
                 c.count("#font-list .fp-it[data-font]") == 31 and c.text("#font-list .fp-it[data-font='Montserrat'] .fp-tag") == "works offline"
                 and sorted(J("Array.prototype.map.call(document.querySelectorAll('#font-list .fp-tag'), function(t){ return t.parentNode.dataset.font; })")) == ["Cormorant Garamond", "DM Sans", "Fraunces", "Inter", "Montserrat"])
            rows = J("Array.prototype.map.call(document.querySelectorAll('#font-list .fp-it[data-font]'), function(b){ return b.getBoundingClientRect().height; })")
            lr, pr = c.rect("#font-list"), c.rect("#font-line")
            case("no internet: that line sits under the list and every name's row is the same height, so nothing moves a name from under the pointer when a line or a face arrives",
                 pr["y"] >= lr["bottom"] - 0.5 and len(set(rows)) == 1, (lr, pr, sorted(set(rows))))
            case("no internet: the list says the others need the internet",
                 c.text("#font-line") == "No internet right now. The fonts marked “works offline” still work. The others need the internet.", c.text("#font-line"))
            c.click("#font-search")
            c.type_text("Lobster")
            c.click("#font-list .fp-load")
            try:
                c.wait_for("document.querySelector('#font-list .fp-load').textContent.indexOf('Loading') < 0", 15)
            except cd.Timeout:
                pass
            case("no internet: loading a font by name says Google Fonts can't be reached (not that the name is wrong), and keeps nothing",
                 c.text("#font-list .fp-load") == "Can’t reach Google Fonts right now. Check the internet and try again." and not fonts_file.exists() and sel()["font"] == "Lora", c.text("#font-list .fp-load"))
            c.key("Escape")
            pick_font("DM Sans")
            fonts_in()
            case("no internet: picking one of the plugin's own families for that box works, and the line goes away",
                 sel()["font"] == "DM Sans" and probe(3)["status"] == "ready" and c.js("document.getElementById('l-fonts').hidden") is True and settled(), c.text("#l-fonts"))
            case("no internet: in all of that no request left this computer that was not for Google Fonts, and every one of those failed",
                 all(("fonts.googleapis.com" in u or "fonts.gstatic.com" in u) for u in c.outside_requests()), [u for u in c.outside_requests() if "fonts.g" not in u][:3])
            c.set_offline(False)

            # ================= with the internet: a Google family, a misspelled name, a font loaded by name =================
            if online:
                D7 = new_design("google", {"slides": 3, "bg": "#ffffff", "blocks": [dict(FRAME), TB(2, text="A Google family", font="Lora", x=1210, y=300)]})
                open_design(D7)
                fonts_in(20)
                wide = J("__wide('Lora')")
                reqs = google_requests()
                case("online: a Google family on the list loads from Google, with the weights the list gives, and draws in its own face",
                     probe(2)["status"] == "ready" and abs(wide["own"] - wide["georgia"]) > 5 and any(u.endswith("css2?family=Lora:wght@400;700&display=swap") for u in reqs)
                     and c.js("document.getElementById('l-fonts').hidden") is True, (wide, reqs[:2]))
                case("online: Google was asked through a stylesheet link only (no script, no fetch), and nothing else outside was asked for",
                     c.count("head link[rel='stylesheet'][href^='https://fonts.googleapis.com/css2?family=Lora']") == 1 and c.count("script[src]") == 0
                     and all(("fonts.googleapis.com" in u or "fonts.gstatic.com" in u) for u in c.outside_requests()))
                c.click(centre(2))
                c.click("#font-btn")
                c.wait_for("!document.getElementById('font-panel').hidden", 3)
                asked_now = J("Array.prototype.filter.call(document.querySelectorAll('#font-list .fp-it[data-font]'), function(b){ return Designer.type.fonts.state(b.dataset.font) !== 'none'; }).map(function(b){ return b.dataset.font; })")
                case("font list: opening it asks only for the families in sight (not all thirty-one at once)", 4 <= len(asked_now) <= 16 and "Caveat" not in asked_now, asked_now)
                try:
                    c.wait_for("(function(){ var b = document.querySelector(\"#font-list .fp-it[data-font='Libre Baskerville'] .fp-name\"); return getComputedStyle(b).fontFamily.indexOf('Libre Baskerville') >= 0; })()", 15)
                except cd.Timeout:
                    pass
                case("font list: a name in sight is shown in its own face once it has loaded",
                     "Libre Baskerville" in c.js("getComputedStyle(document.querySelector(\"#font-list .fp-it[data-font='Libre Baskerville'] .fp-name\")).fontFamily")
                     and J("__wide('Libre Baskerville')")["own"] != J("__wide('Libre Baskerville')")["georgia"])
                c.js("(function(){ var l = document.getElementById('font-list'); l.scrollTop = l.scrollHeight; l.dispatchEvent(new Event('scroll')); })()")
                try:
                    c.wait_for("Designer.type.fonts.state('Caveat') === 'ok'", 15)
                except cd.Timeout:
                    pass
                case("font list: scrolled to the end, the last names are asked for then", c.js("Designer.type.fonts.state('Caveat')") == "ok", c.js("Designer.type.fonts.state('Caveat')"))
                case("font list: the groups are Serif, Sans and Script, with the open box's own font marked",
                     J("Array.prototype.map.call(document.querySelectorAll('#font-list .fp-grp'), function(g){ return g.textContent; })") == ["Serif", "Sans", "Script"]
                     and c.text("#font-list .fp-it.cur .fp-name") == "Lora")
                # a misspelled name
                n_fontposts = sum(1 for r in c.requests if r["url"].endswith("/design-font"))
                c.click("#font-search")
                c.type_text("lobsterr xyzq")
                case("misspelled: the search offers to load what was typed, written as a font's name", c.text("#font-list .fp-load") == "Load “Lobsterr Xyzq” from Google Fonts", c.text("#font-list .fp-load"))
                c.click("#font-list .fp-load")
                try:
                    c.wait_for("document.querySelector('#font-list .fp-load').textContent.indexOf('Couldn') === 0", 20)
                except cd.Timeout:
                    pass
                case("misspelled: it says “Couldn’t find ... on Google Fonts. Check the spelling.”",
                     c.text("#font-list .fp-load") == "Couldn’t find “Lobsterr Xyzq” on Google Fonts. Check the spelling.", c.text("#font-list .fp-load"))
                case("misspelled: nothing was added: the box keeps its font, nothing went to the Assistant, no 'Yours', no page error",
                     sel()["font"] == "Lora" and sum(1 for r in c.requests if r["url"].endswith("/design-font")) == n_fontposts and not fonts_file.exists()
                     and c.js("Designer.S.fonts.yours.length") == 0 and c.js("Designer.type.fonts.state('Lobsterr Xyzq')") == "none" and c.page_errors() == [], c.page_errors())
                # a real one, by name
                c.click("#font-search")
                c.key("Mod+A")
                c.type_text("lobster two")
                c.key("Enter")                 # Enter presses the first row: the offer to load it
                try:
                    c.wait_for("Designer.selected() && Designer.selected().font === 'Lobster Two'", 20)
                except cd.Timeout:
                    pass
                fonts_in(20)
                wide = J("__wide('Lobster Two')")
                case("by name: a real Google font typed in the search is loaded, used for the selected box, and the list closes",
                     sel()["font"] == "Lobster Two" and probe(2)["status"] == "ready" and abs(wide["own"] - wide["georgia"]) > 5 and c.js("document.getElementById('font-panel').hidden") is True, (sel()["font"], wide))
                try:
                    cd.wait_until(lambda: fonts_file.exists(), 5)
                except Exception:  # noqa: BLE001
                    pass
                kept = json.loads(fonts_file.read_text(encoding="utf-8")) if fonts_file.exists() else {}
                case("by name: the Assistant keeps it under 'Yours' (on the drive, not in the browser)", kept.get("fonts") == ["Lobster Two"] and c.js("localStorage.length + sessionStorage.length") == 0, kept)
                case("by name: a family loaded by name is asked for bold too, and Lobster Two has one, so B is offered",
                     any("family=Lobster+Two:wght@400;700" in u for u in google_requests()) and c.js("document.querySelector(\"#selbar button[data-t='weight']\").disabled") is False)
                case("by name: saved in the design", settled() and blk(disk()["state"], 2)["font"] == "Lobster Two")
                c.reload()
                ready()
                fonts_in(20)
                c.click(centre(2))
                c.click("#font-btn")
                c.wait_for("!document.getElementById('font-panel').hidden", 3)
                case("by name: after a reload it is in the list under 'Yours', first, and marked as the box's font",
                     J("Array.prototype.map.call(document.querySelectorAll('#font-list .fp-grp'), function(g){ return g.textContent; })") == ["Yours", "Serif", "Sans", "Script"]
                     and c.js("document.querySelector('#font-list .fp-it').dataset.font") == "Lobster Two" and c.text("#font-list .fp-it.cur .fp-name") == "Lobster Two" and probe(2)["status"] == "ready")
                c.key("Escape")
                # the internet goes away under an open page, and comes back
                c.set_offline(True)
                D8 = new_design("lost", {"slides": 3, "bg": "#ffffff", "blocks": [dict(FRAME), TB(2, text="Was online", font="Oswald", x=1210, y=300)]})
                open_design(D8)
                fonts_in(20)
                case("internet lost: (a Google family not asked for before falls back, and the line shows)", probe(2)["status"] == "fallback" and "Oswald" in c.text("#l-fonts"), c.text("#l-fonts"))
                c.set_offline(False)
                c.js("window.dispatchEvent(new Event('online')); true")
                try:
                    c.wait_for("Designer.type.status(Designer.st.blocks[1]) === 'ready'", 20)
                except cd.Timeout:
                    pass
                wide = J("__wide('Oswald')")
                case("internet back: the font is asked for again by itself, the words go into their own face and the line goes away",
                     probe(2)["status"] == "ready" and abs(wide["own"] - wide["georgia"]) > 5 and c.js("document.getElementById('l-fonts').hidden") is True, (c.text("#l-fonts"), wide))
            c.set_offline(True)

            # ================= brand colors =================
            D9 = new_design("brand", {"slides": 2, "bg": "#ffffff", "blocks": [TB(1, font="Inter", x=130, y=300)]})
            open_design(D9)
            fonts_in()
            case("brand: with none saved the group says so, beside its + button", c.text("#brand-row") == "none yet" and c.count("#brand-row .bc-sw") == 0 and not brand_file.exists())
            # (a hidden Chrome cannot open a color box, so the asking is written down instead)
            STUB = "window.__picks = []; HTMLInputElement.prototype.showPicker = function(){ window.__picks.push([this.id, this.value]); }; true"
            c.js(STUB)
            c.click("#brand-add")
            case("brand: + asks the browser to open the color box, starting from the color in use (the background)", J("window.__picks") == [["brand-pick", "#ffffff"]], J("window.__picks"))
            c.set_value("#brand-pick", "#AA3366")
            try:
                c.wait_for("document.querySelectorAll('#brand-row .bc-sw').length === 1", 5)
            except cd.Timeout:
                pass
            saved = json.loads(brand_file.read_text(encoding="utf-8")) if brand_file.exists() else {}
            case("brand: a color chosen in the + color box is saved by the Assistant and shows as a swatch, with a line beside it saying so",
                 saved.get("colors") == ["#aa3366"] and c.js("document.querySelector('#brand-row .bc-sw').dataset.c") == "#aa3366" and c.text("#brand-line") == "Saved. It’s here for every shoot.", (saved, c.text("#brand-line")))
            c.click("#brand-row .bc-sw")
            case("brand: with nothing selected, a click on it colors the background", st()["bg"] == "#aa3366" and c.js("getComputedStyle(document.getElementById('strip')).backgroundColor") == "rgb(170, 51, 102)")
            c.click(centre(1))
            case("brand: with a text box selected the group says the colors are for the text, and the same swatches sit beside the text color",
                 c.text("#brand-label") == "Brand colors (for the text)" and c.count("#t-brand .bc-sw") == 1 and c.count("#t-brand .bc-off") == 0)
            c.set_value("#brand-pick", "#00aa77")
            c.wait_for("document.querySelectorAll('#brand-row .bc-sw').length === 2", 5)
            c.click("#brand-row .bc-sw", nth=1)
            case("brand: a click on a swatch then colors the selected text, not the background", sel()["color"] == "#00aa77" and st()["bg"] == "#aa3366", sel()["color"])
            c.click("#t-brand .bc-sw")
            case("brand: the small swatches beside the text color do the same", sel()["color"] == "#aa3366")
            case("brand: both saved in the design", settled() and disk()["state"]["bg"] == "#aa3366" and blk(disk()["state"], 1)["color"] == "#aa3366")
            c.reload()
            ready()
            fonts_in()
            case("brand: after a reload the colors are still there, in the order saved (kept by the Assistant, nothing in the browser)",
                 J("Array.prototype.map.call(document.querySelectorAll('#brand-row .bc-sw'), function(s){ return s.dataset.c; })") == ["#aa3366", "#00aa77"]
                 and c.js("localStorage.length + sessionStorage.length") == 0)
            for k in range(14):
                c.set_value("#brand-pick", "#10%02x%02x" % (k * 16, 255 - k * 16))
                c.wait_for("document.querySelectorAll('#brand-row .bc-sw').length === %d" % (k + 3), 5)
            case("brand: sixteen can be saved", c.count("#brand-row .bc-sw") == 16 and len(json.loads(brand_file.read_text(encoding="utf-8"))["colors"]) == 16)
            n_posts = sum(1 for r in c.requests if r["url"].endswith("/design-brand"))
            c.js(STUB)
            c.click("#brand-add")
            full_line = c.text("#brand-line")
            case("brand: at sixteen the + button says plainly that the list is full, and opens nothing",
                 full_line == "You've saved 16 brand colors, which is as many as fit. Take one off first." and J("window.__picks") == [], (full_line, J("window.__picks")))
            c.set_value("#brand-pick", "#123456")
            time.sleep(0.3)
            case("brand: ...and a seventeenth is not saved (not by the page, not by the Assistant)",
                 c.count("#brand-row .bc-sw") == 16 and "#123456" not in json.loads(brand_file.read_text(encoding="utf-8"))["colors"]
                 and sum(1 for r in c.requests if r["url"].endswith("/design-brand")) == n_posts)
            code, out = post(P, "/design-brand", {"add": "#123456"})
            case("brand: asked directly, the Assistant refuses a seventeenth in the very same words", code == 409 and (out or {}).get("words") == full_line, (code, out))
            # taking one off: the small x that shows when the pointer is over the color
            case("brand: the small x on a color is not showing until the pointer is over it", c.js("getComputedStyle(document.querySelector('#brand-row .bc-off')).display") == "none")
            r = c.rect("#brand-row .bc-sw", 1)
            c.mouse_move(r["cx"], r["cy"])
            case("brand: with the pointer over a color its x shows, and says what it does", c.js("getComputedStyle(document.querySelectorAll('#brand-row .bc-off')[1]).display") == "block"
                 and c.js("document.querySelectorAll('#brand-row .bc-off')[1].title") == "Take #00aa77 off your brand colors")
            c.click("#brand-row .bc-off", nth=1)
            c.wait_for("document.querySelectorAll('#brand-row .bc-sw').length === 15", 5)
            now = json.loads(brand_file.read_text(encoding="utf-8"))
            case("brand: pressing it takes that color off the list (the Assistant keeps a note of it; nothing else changes), and a line says so with a way back",
                 "#00aa77" not in now["colors"] and len(now["colors"]) == 15 and any(x.get("color") == "#00aa77" for x in now.get("removed", []))
                 and c.text("#brand-line").startswith("Taken off your brand colors.") and c.text("#brand-back") == "Put it back" and len(st()["blocks"]) == 1, c.text("#brand-line"))
            c.click("#brand-back")
            c.wait_for("document.querySelectorAll('#brand-row .bc-sw').length === 16", 5)
            case("brand: Put it back puts it back", "#00aa77" in json.loads(brand_file.read_text(encoding="utf-8"))["colors"])
            case("brand: the page had no error in any of it", c.page_errors() == [], c.page_errors())

            # ================= the limit on text boxes =================
            D10 = new_design("forty", {"slides": 2, "bg": "#ffffff", "blocks": [TB(k + 1, text="t", font="Inter", x=130, y=40 + k * 20, w=200) for k in range(40)]})
            open_design(D10)
            fonts_in()
            c.click("#add-text")
            case("limit: with 40 text boxes, + Add text says so beside the button and adds nothing",
                 c.text("#text-line") == "A design holds up to 40 text boxes. Remove one first." and len(st()["blocks"]) == 40, c.text("#text-line"))

            # ================= nothing waits on a timer =================
            c.hold_timers()
            try:
                D11 = new_design("timers")
                open_design(D11)
                c.js("document.getElementById('stage').scrollLeft = 0")
                c.click("#add-text")
                pick_font("Montserrat")
                fonts_in(10)
                c.click("#t-words")
                c.key("Mod+A")
                c.type_text("No timers")
                c.click("#selbar button[data-t='weight']")
                tid = c.js("Designer.sel")
                p = probe(tid)
                case("timers held: a text box is added, its font arrives, typed words and Bold show on the strip at once (no timer or animation frame is needed)",
                     p["status"] == "ready" and [d["t"] for d in p["dom"]] == ["No timers"] and p["dom"][0]["weight"] == "700" and "Montserrat" in p["dom"][0]["family"] and p["b"]["h"] == 110.4, p["dom"])
            finally:
                c.run_timers()
                c.free_timers()

            # ================= a phone's width =================
            c.phone(390, 844)
            try:
                open_design(D3)
                fonts_in()
                c.js("(function(){ var b = Designer.st.blocks.filter(function(x){ return x.type === 'text'; })[0]; Designer.select(b.id); })()")
                c.js("document.getElementById('font-btn').scrollIntoView({block: 'center'})")
                c.click("#font-btn")
                c.wait_for("!document.getElementById('font-panel').hidden", 3)
                wide = J("({inner: innerWidth, doc: document.documentElement.scrollWidth, body: document.body.scrollWidth})")
                pr = c.rect("#font-panel")
                case("phone width (390): with a text box selected and the font list open the page does not scroll sideways, and the list is inside the window",
                     wide["inner"] == 390 and wide["doc"] <= 390 and wide["body"] <= 390 and pr["x"] >= 0 and pr["right"] <= 390, (wide, pr))
                c.key("Escape")
            finally:
                c.desktop()

            # ================= the whole run =================
            case("the page threw no error and logged none, in the whole run", c.page_errors() == [], c.page_errors()[:4])
            outside = [u for u in c.outside_requests() if "fonts.googleapis.com" not in u and "fonts.gstatic.com" not in u]
            case("the page asked nothing of any address but the Assistant's and Google Fonts, in the whole run", outside == [], outside[:4])
            case("everything asked of Google was a stylesheet or a font file, by GET", all(re.match(r"https://fonts\.googleapis\.com/css2\?family=[A-Za-z0-9+]+(:wght@[0-9;]+)?&display=swap(&text=[a-z0-9]+)?$", u) or u.startswith("https://fonts.gstatic.com/") for u in c.outside_requests()),
                 [u for u in c.outside_requests() if "gstatic" not in u][:3])
            asked = sorted(set(re.sub(r"\?.*", "", re.sub(r"^https?://[^/]+", "", r["url"])) for r in c.requests if "127.0.0.1" in r["url"]))
            case("every request to the Assistant was for the page, its state, a made copy of a photo, a font file, a save, a brand color or a kept font",
                 set(asked) <= {"/design.html", "/design-state", "/kit-photo", "/design", "/design-font-file", "/design-brand", "/design-font", "/favicon.ico"}, asked)
            case("the Finder was never asked for (/open was not requested)", not any("/open" in r["url"] for r in c.requests))
            case("nothing is kept in the browser's own storage", c.js("localStorage.length + sessionStorage.length") == 0 and c.js("document.cookie") == "")
    finally:
        srv.stop()
    case("text browser: the kit's own record was not written by any of it", (kit / ".kit" / "kit.json").read_bytes() == rec_before)
    case("text browser: no photo was changed", sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in (kit / "Photos").iterdir()) == photos_before)
    case("text browser: nothing was put in the Carousel folder", not (kit / "Carousel").exists() or not list((kit / "Carousel").iterdir()))
    log = (studio / "arrange.log").read_text(encoding="utf-8", errors="replace") if (studio / "arrange.log").is_file() else ""
    case("text browser: the server never fell over (no Python error, no failed route in its log)", "Traceback" not in log and " failed: " not in log, [ln for ln in log.splitlines() if " failed: " in ln or "Traceback" in ln][:3])
