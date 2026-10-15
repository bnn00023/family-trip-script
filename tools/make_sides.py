import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_blocking

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
SIDES = ROOT / "sides"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

ROLES = [
    ("阿嬤", "amah", "阿嬤 金花", "凱莉"),
    ("阿明", "aming", "爸爸 阿明", "冠豪"),
    ("淑芬", "shufen", "媽媽 淑芬", "雅典娜"),
    ("小瑜", "xiaoyu", "孫女 小瑜", "鈺庭"),
]

LINE = re.compile(r'<p><span class="who">(?P<who>[^<]+)</span>(?P<body>.*?)</p>', re.S)
STAGE_SPAN = re.compile(r'(<span class="(?:who|act)">[^<]*</span>)')
HEADING = re.compile(r'<h3>[^<]*<small>[^<]*</small></h3>')
MOOD = re.compile(r'<div class="block mood"><b>情緒</b><ul>(?P<items>.*?)</ul></div>', re.S)
ACTING = re.compile(r'<div class="block"><b>演法</b>.*?</div>\s*', re.S)
PARAGRAPH = re.compile(r'<p(?: class="[^"]*")?>(?P<body>.*?)</p>', re.S)
WHO = re.compile(r'^<span class="who">(?P<who>[^<]+)</span>')
CUE_TAIL = re.compile(r'[^。！？]+[。！？]*\s*$')
CUE_MAX = 16

CSS = """
@page {
  size: A4;
  margin: 13mm 15mm 15mm;
  @bottom-center { content: "%(title)s · 第 " counter(page) " / " counter(pages) " 頁"; font-size: 9pt; color: #777; }
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0; color: #111; background: #fff;
  font-family: "PingFang TC", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
  font-size: 11pt; line-height: 1.5;
}
.cover { border: 1.5pt solid #111; border-radius: 6pt; padding: 10pt 14pt; margin-bottom: 14pt; }
.cover h1 { font-size: 18pt; margin: 0 0 2pt; }
.cover .role { font-size: 14pt; font-weight: 700; margin: 0 0 4pt; }
.cover .meta { font-size: 10pt; color: #444; margin: 0; }
.legend { margin-top: 6pt; font-size: 10pt; }
.legend .say { text-decoration: underline; text-decoration-thickness: 1.5pt; text-underline-offset: 3pt; }
h3 { font-size: 13pt; margin: 12pt 0 5pt; padding-bottom: 2pt; border-bottom: 1pt solid #111; break-after: avoid; clear: both; }
h3 small { font-weight: normal; font-size: 10pt; color: #555; margin-left: 6pt; }
.script p { margin: 0 0 4pt; break-inside: avoid; }
.script .who { font-weight: 700; margin-right: 6pt; }
.script .act { color: #555; }
.script .dir { color: #555; }
.block { border-left: 2.5pt solid #999; padding: 2pt 8pt; margin: 5pt 0; font-size: 9.5pt; color: #333; break-inside: avoid; }
.block b { margin-right: 6pt; color: #111; }
p.mine .who { font-size: 12pt; }
p.mine .say { font-weight: 600; text-decoration: underline; text-decoration-thickness: 1.5pt; text-underline-offset: 3pt; }
.cue { font-weight: 700; font-style: italic; }
figure.stage { float: right; width: 52%%; margin: 0 0 4pt 10pt; break-inside: avoid; }
figure.stage svg { display: block; width: 100%%; height: auto; }
figure.stage figcaption { font-size: 8pt; line-height: 1.3; color: #666; margin-top: 2pt; }
"""


def underline_spoken(body):
    parts = STAGE_SPAN.split(body)
    return "".join(
        part if STAGE_SPAN.fullmatch(part) or not part.strip() else '<span class="say">' + part + "</span>"
        for part in parts
    )


def mark_lines(text, role):
    def replace(match):
        if match.group("who") != role:
            return match.group(0)
        return '<p class="mine"><span class="who">' + role + "</span>" + underline_spoken(match.group("body")) + "</p>"

    return LINE.sub(replace, text)


def keep_own_mood(text, role):
    def replace(match):
        own = re.search(r"<li><b>" + role + r"</b>(.*?)</li>", match.group("items"))
        return '<div class="block mood"><b>情緒</b>' + own.group(1) + "</div>"

    return MOOD.sub(replace, text)


def drop_acting_notes(text):
    return ACTING.sub("", text)


def with_cue(body):
    parts = STAGE_SPAN.split(body)
    for index in range(len(parts) - 1, -1, -1):
        part = parts[index]
        if STAGE_SPAN.fullmatch(part) or not part.strip():
            continue
        cue = CUE_TAIL.search(part).group(0)
        if len(cue) > CUE_MAX and "，" in cue:
            cue = cue[cue.rindex("，") + 1:]
        parts[index] = part[:-len(cue)] + '<span class="cue">' + cue + "</span>"
        break
    return "".join(parts)


def mark_cues(text, role):
    paragraphs = list(PARAGRAPH.finditer(text))
    speakers = [WHO.match(match.group("body")) for match in paragraphs]
    cued = set()
    for index, speaker in enumerate(speakers):
        if speaker is None or speaker.group("who") != role:
            continue
        previous = index - 1
        while previous >= 0 and speakers[previous] is None:
            previous -= 1
        if previous >= 0 and speakers[previous].group("who") != role:
            cued.add(previous)
    pieces, position = [], 0
    for index in sorted(cued):
        match = paragraphs[index]
        pieces.append(text[position:match.start("body")])
        pieces.append(with_cue(match.group("body")))
        position = match.end("body")
    pieces.append(text[position:])
    return "".join(pieces)


def with_stage_figures(text, role, scenes):
    figures = iter(
        '<figure class="stage">' + make_blocking.focus_svg(pot, paths, role) +
        "<figcaption>實心圈＝這段結束位置，虛線圈＝出發點，數字＝移動順序。</figcaption></figure>"
        for _, _, pot, _, paths in scenes
    )
    marked, count = HEADING.subn(lambda match: match.group(0) + next(figures), text)
    if count != len(scenes):
        raise ValueError("expected %d scene headings, found %d" % (len(scenes), count))
    return marked


def render(script, version, role, label, actor, scenes):
    marked = mark_cues(drop_acting_notes(keep_own_mood(mark_lines(script, role), role)), role)
    marked = with_stage_figures(marked, role, scenes)
    count = marked.count('<p class="mine">')
    title = "早知道就出門了 · " + label + "台詞本"
    page = (
        '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>' + title + "</title>"
        "<style>" + CSS % {"title": label + "（" + actor + "）"} + "</style></head><body>"
        '<div class="cover"><h1>早知道就出門了</h1>'
        '<p class="role">' + label + "（" + actor + " 飾）台詞本</p>"
        '<p class="meta">共 ' + str(count) + " 句台詞 · 單一場景：飯店房間 · 約 8 分 · 劇本 " + version.group(1) + "（" + version.group(2) + "）</p>"
        '<p class="legend">加粗＋<span class="say">底線</span>＝你的台詞。<span class="cue">粗體＋斜體</span>＝你開口前對方的最後一句，聽到它就接。（　）裡是動作，不用唸出來。每段標題右邊的圖是這段走位：深色是你，淡色是其他人。</p></div>'
        + marked + "</body></html>"
    )
    return page, count


def main():
    html = PAGE.read_text(encoding="utf-8")
    version = re.search(r'版本 (v[\d.]+) · 更新時間 ([\d\- :]+)', html)
    script = html[html.index('<h2 id="script">'):html.index('<h2 id="notes">')]
    script = re.sub(r'<h2 id="script">[^<]*</h2>\s*<p>.*?</p>', '', script, count=1, flags=re.S)
    scenes = make_blocking.walk()
    SIDES.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        for role, slug, label, actor in ROLES:
            page, count = render(script, version, role, label, actor, scenes)
            source = Path(work) / (slug + ".html")
            source.write_text(page, encoding="utf-8")
            subprocess.run(
                [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                 "--print-to-pdf=" + str(SIDES / (slug + ".pdf")), source.as_uri()],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            print(role, count, "sides/" + slug + ".pdf")


if __name__ == "__main__":
    main()
