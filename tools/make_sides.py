import re
import subprocess
import tempfile
from pathlib import Path

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
  font-size: 11pt; line-height: 1.55;
}
.cover { border: 1.5pt solid #111; border-radius: 6pt; padding: 10pt 14pt; margin-bottom: 14pt; }
.cover h1 { font-size: 18pt; margin: 0 0 2pt; }
.cover .role { font-size: 14pt; font-weight: 700; margin: 0 0 4pt; }
.cover .meta { font-size: 10pt; color: #444; margin: 0; }
.legend { margin-top: 6pt; font-size: 10pt; }
.legend .say { text-decoration: underline; text-decoration-thickness: 1.5pt; text-underline-offset: 3pt; }
h3 { font-size: 13pt; margin: 12pt 0 5pt; padding-bottom: 2pt; border-bottom: 1pt solid #111; break-after: avoid; }
h3 small { font-weight: normal; font-size: 10pt; color: #555; margin-left: 6pt; }
.script p { margin: 0 0 4pt; break-inside: avoid; }
.script .who { font-weight: 700; margin-right: 6pt; }
.script .act { color: #555; }
.script .dir { color: #555; }
.block { border-left: 2.5pt solid #999; padding: 3pt 8pt; margin: 6pt 0; font-size: 10pt; color: #333; break-inside: avoid; }
.block b { margin-right: 6pt; color: #111; }
p.mine .who { font-size: 12pt; }
p.mine .say { font-weight: 600; text-decoration: underline; text-decoration-thickness: 1.5pt; text-underline-offset: 3pt; }
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


def render(script, version, role, label, actor):
    marked = mark_lines(script, role)
    count = marked.count('<p class="mine">')
    title = "早知道就出門了 · " + label + "台詞本"
    page = (
        '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>' + title + "</title>"
        "<style>" + CSS % {"title": label + "（" + actor + "）"} + "</style></head><body>"
        '<div class="cover"><h1>早知道就出門了</h1>'
        '<p class="role">' + label + "（" + actor + " 飾）台詞本</p>"
        '<p class="meta">共 ' + str(count) + " 句台詞 · 單一場景：飯店房間 · 約 7 分半 · 劇本 " + version.group(1) + "（" + version.group(2) + "）</p>"
        '<p class="legend">加粗＋<span class="say">底線</span>＝你的台詞。（　）裡是動作，不用唸出來。</p></div>'
        + marked + "</body></html>"
    )
    return page, count


def main():
    html = PAGE.read_text(encoding="utf-8")
    version = re.search(r'版本 (v[\d.]+) · 更新時間 ([\d\- :]+)', html)
    script = html[html.index('<h2 id="script">'):html.index('<h2 id="notes">')]
    script = re.sub(r'<h2 id="script">[^<]*</h2>\s*<p>.*?</p>', '', script, count=1, flags=re.S)
    SIDES.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        for role, slug, label, actor in ROLES:
            page, count = render(script, version, role, label, actor)
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
