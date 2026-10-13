import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
SCRIPT_MD = ROOT / "劇本.md"
START = '<h2 id="script">'
END = '<h2 id="notes">'

ACTORS = {"阿嬤": "凱莉", "阿明": "冠豪", "淑芬": "雅典娜", "小瑜": "鈺庭"}

HEADING_HTML = re.compile(r'^<h3>(?P<title>.+) <small>(?P<time>[^<]+)</small></h3>$')
BLOCK_HTML = re.compile(r'^<div class="block"><b>(?P<kind>[^<]+)</b>(?P<text>.*)</div>$')
DIR_HTML = re.compile(r'^<p class="dir">(?P<text>.*)</p>$')
LINE_HTML = re.compile(r'^<p><span class="who">(?P<who>[^<]+)</span>(?P<body>.*)</p>$')
ACT_HTML = re.compile(r'<span class="act">([^<]*)</span>')
INTRO_HTML = re.compile(r'^<p>(?P<text>.*)</p>$')
TITLE_HTML = re.compile(r'^<h2 id="script">(?P<text>[^<]+)</h2>$')

TITLE_MD = re.compile(r'^# (?P<text>.+)$')
HEADING_MD = re.compile(r'^## (?P<title>.+) (?P<time>\d+:\d\d–\d+:\d\d)$')
BLOCK_MD = re.compile(r'^> (?P<kind>走位|演法)：(?P<text>.*)$')
DIR_MD = re.compile(r'^（.*）$')
LINE_MD = re.compile(r'^(?P<who>' + "|".join(ACTORS) + r')：(?P<body>.+)$')
ACT_MD = re.compile(r'（[^（）]*）')


def export_markdown(page):
    section = page[page.index(START):page.index(END)]
    out = []
    for raw in section.split("\n"):
        line = raw.strip()
        if not line or line in ('<div class="script">', "</div>"):
            continue
        if match := TITLE_HTML.match(line):
            out.append("# " + match["text"])
        elif match := HEADING_HTML.match(line):
            out.append("## " + match["title"] + " " + match["time"])
        elif match := BLOCK_HTML.match(line):
            out.append("> " + match["kind"] + "：" + match["text"])
        elif match := DIR_HTML.match(line):
            out.append(match["text"])
        elif match := LINE_HTML.match(line):
            out.append(match["who"] + "：" + ACT_HTML.sub(r"\1", match["body"]))
        elif match := INTRO_HTML.match(line):
            out.append(match["text"])
        else:
            raise ValueError("unrecognized line: " + line)
    return "\n\n".join(out) + "\n"


def build_section(markdown):
    out = []
    in_scene = False
    for number, raw in enumerate(markdown.split("\n"), 1):
        line = raw.strip()
        if not line:
            continue
        if match := HEADING_MD.match(line):
            if in_scene:
                out.append("</div>\n")
            out.append("<h3>" + match["title"] + " <small>" + match["time"] + "</small></h3>")
            out.append('<div class="script">')
            in_scene = True
        elif match := TITLE_MD.match(line):
            out.append(START + match["text"] + "</h2>")
        elif match := BLOCK_MD.match(line):
            out.append('<div class="block"><b>' + match["kind"] + "</b>" + match["text"] + "</div>")
        elif DIR_MD.match(line):
            out.append('<p class="dir">' + line + "</p>")
        elif match := LINE_MD.match(line):
            body = ACT_MD.sub(lambda act: '<span class="act">' + act.group(0) + "</span>", match["body"])
            out.append('<p><span class="who">' + match["who"] + "</span>" + body + "</p>")
        elif not in_scene:
            out.append("<p>" + line + "</p>\n")
        else:
            raise ValueError("劇本.md 第 %d 行看不懂：%s" % (number, line))
    if in_scene:
        out.append("</div>\n")
    return "\n".join(out) + "\n"


def count_lines(section):
    return {who: len(re.findall(r'<p><span class="who">' + who + "</span>", section)) for who in ACTORS}


def build_page(page, markdown):
    section = build_section(markdown)
    page = page[:page.index(START)] + section + page[page.index(END):]
    for who, total in count_lines(section).items():
        page, hits = re.subn(ACTORS[who] + r" 飾 · \d+ 句台詞", ACTORS[who] + " 飾 · %d 句台詞" % total, page)
        if hits != 1:
            raise ValueError("download card for " + who + " matched %d times" % hits)
    return page


def main():
    command = sys.argv[1]
    page = PAGE.read_text(encoding="utf-8")
    if command == "export":
        SCRIPT_MD.write_text(export_markdown(page), encoding="utf-8")
    elif command == "build":
        PAGE.write_text(build_page(page, SCRIPT_MD.read_text(encoding="utf-8")), encoding="utf-8")
    elif command == "check":
        rebuilt = build_page(page, export_markdown(page))
        print("round trip identical" if rebuilt == page else "round trip DIFFERS")
    else:
        raise SystemExit("usage: script_md.py export|build|check")


if __name__ == "__main__":
    main()
