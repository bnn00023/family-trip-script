import math
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "blocking"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

STAGE = (40, 70, 760, 430)
CELL = 20
REACH = 56
WIDTH = 800

CAST = {
    "阿嬤": ("嬤", "#b5543c"),
    "阿明": ("明", "#2f6fd0"),
    "淑芬": ("芬", "#2e8b57"),
    "小瑜": ("瑜", "#c98a00"),
}

FURNITURE = [
    ("床（兩張椅子）", (320, 84, 460, 118)),
    ("行李箱", (90, 334, 200, 384)),
    ("桌子", (560, 320, 700, 368)),
]
DOOR = (640, 70, 740, 70)

OPENING = {
    "阿嬤": (390, 132, "坐"),
    "淑芬": (145, 316, "跪"),
    "小瑜": (400, 240, "站"),
    "阿明": (690, 82, "站"),
}

SCENES = [
    ("第一段　補宣誓", "0:00–1:00", (630, 344), [
        ("阿明", 600, 300, "站", "抱鍋從門口進場，放上桌"),
        ("阿明", 395, 188, "站", "兩步走到中央，擋在小瑜和床之間"),
    ]),
    ("第二段　秤重", "1:00–2:30", (630, 344), [
        ("小瑜", 250, 290, "站", "走位：退到行李箱旁，秤重"),
        ("阿明", 222, 356, "跪", "走位：到行李箱另一側，跪下壓箱蓋"),
        ("阿明", 292, 300, "站", "「小瑜。」走到小瑜旁邊制止"),
    ]),
    ("第三段　翻舊帳", "2:30–4:30", (630, 344), [
        ("小瑜", 330, 245, "站", "頂嘴，往床走一步"),
        ("小瑜", 392, 206, "站", "又往床走一步，站到阿嬤正前方"),
        ("阿明", 392, 168, "站", "「好了好了」走進來站到兩人中間，背對阿嬤"),
    ]),
    ("第四段　爆發", "4:30–5:30", (520, 404), [
        ("淑芬", 368, 222, "站", "走位：站起來走到中央，正面對阿嬤"),
        ("小瑜", 440, 230, "站", "走位：站到淑芬旁邊"),
        ("阿明", 215, 298, "站", "走位：退到行李箱旁"),
        ("阿明", 195, 312, "站", "「不是錢！」之後再退半步"),
        ("阿嬤", 390, 140, "站", "站起來，離開床"),
        ("阿明", 318, 182, "站", "「媽，妳休息…」想上前扶，被揮開"),
        ("阿嬤", 520, 300, "站", "慢慢走到桌子旁"),
        ("阿嬤", 520, 362, "跪", "把鍋抱到地上，扶桌緣跪下，掀蓋"),
    ]),
    ("第五段　鍋蓋", "5:30–7:00", (520, 404), [
        ("阿明", 215, 298, "站", "走位：回到行李箱旁"),
        ("小瑜", 472, 378, "跪", "走過去跪在阿嬤旁邊，拿起御守"),
        ("淑芬", 578, 394, "蹲", "走過去蹲下來，拿起陶碗"),
        ("阿明", 532, 304, "蹲", "走過去蹲在後面，倒清酒敬淑芬"),
    ]),
    ("第六段　收尾", "7:00–7:30", (520, 404), [
        ("小瑜", 450, 318, "站", "站起來，舉手機錄影，重新宣誓"),
        ("淑芬", 405, 318, "站", "舉手，走到小瑜旁邊"),
        ("小瑜", 245, 300, "站", "拍手，走向行李箱，其他人跟著動（燈暗）"),
    ]),
]

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


def walk():
    pos = {who: [spot] for who, spot in OPENING.items()}
    scenes = []
    for title, time, pot, beats in SCENES:
        paths = {who: [(pos[who][-1][0], pos[who][-1][1], pos[who][-1][2], None)] for who in CAST}
        for index, (who, x, y, posture, label) in enumerate(beats):
            paths[who].append((x, y, posture, index))
        for who in CAST:
            pos[who].append(paths[who][-1][:3])
        scenes.append((title, time, pot, beats, paths))
    return scenes


def cells():
    left, top, right, bottom = STAGE
    for x in range(left, right, CELL):
        for y in range(top, bottom, CELL):
            center = (x + CELL / 2, y + CELL / 2)
            if not any(fx0 <= center[0] <= fx1 and fy0 <= center[1] <= fy1 for _, (fx0, fy0, fx1, fy1) in FURNITURE):
                yield x, y, center


def segment_distance(point, start, end):
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    ratio = 0 if length == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - ax - ratio * dx, py - ay - ratio * dy)


def touched(center, paths):
    for points in paths.values():
        spots = [(x, y) for x, y, _, _ in points]
        if any(segment_distance(center, a, b) <= REACH for a, b in zip(spots, spots[1:] or spots)):
            return True
    return False


def stage_base(extra):
    left, top, right, bottom = STAGE
    parts = [
        '<rect x="%d" y="%d" width="%d" height="%d" fill="#fffdf9" stroke="#9c9188" stroke-width="1.5"/>' % (left, top, right - left, bottom - top),
        extra,
    ]
    for name, (x0, y0, x1, y1) in FURNITURE:
        parts.append('<rect x="%d" y="%d" width="%d" height="%d" rx="4" fill="#efe6da" stroke="#9c9188"/>' % (x0, y0, x1 - x0, y1 - y0))
        parts.append('<text x="%d" y="%d" text-anchor="middle" font-size="12" fill="#6f655c">%s</text>' % ((x0 + x1) / 2, (y0 + y1) / 2 + 4, name))
    x0, y, x1, _ = DOOR
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#fffdf9" stroke-width="4"/>' % (x0, y, x1, y))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#9c9188" stroke-width="1.5" stroke-dasharray="4 4"/>' % (x0, y, x1, y))
    parts.append('<text x="%d" y="%d" text-anchor="middle" font-size="12" fill="#6f655c">門口（側台入口）</text>' % ((x0 + x1) / 2, y - 6))
    parts.append('<text x="%d" y="%d" font-size="12" fill="#6f655c">舞台左</text>' % (left + 6, (top + bottom) / 2))
    parts.append('<text x="%d" y="%d" text-anchor="end" font-size="12" fill="#6f655c">舞台右</text>' % (right - 6, (top + bottom) / 2))
    parts.append('<rect x="%d" y="%d" width="%d" height="22" rx="4" fill="#f3ebe1" stroke="#9c9188"/>' % (left, bottom + 10, right - left))
    parts.append('<text x="%d" y="%d" text-anchor="middle" font-size="13" fill="#2b2622">觀眾席</text>' % (WIDTH / 2, bottom + 26))
    return "\n".join(parts)


def hatch(blank):
    return "\n".join('<rect x="%d" y="%d" width="%d" height="%d" fill="url(#blank)"/>' % (x, y, CELL, CELL) for x, y in blank)


def defs():
    arrows = "".join(
        '<marker id="arrow-%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0 0 L10 5 L0 10 z" fill="%s"/></marker>' % (char, color)
        for char, color in CAST.values()
    )
    return (
        "<defs>" + arrows +
        '<pattern id="blank" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="8" height="8" fill="#f1ece4"/><line x1="0" y1="0" x2="0" y2="8" stroke="#d6cbbd" stroke-width="2"/></pattern>'
        "</defs>"
    )


def pot_icon(x, y):
    return (
        '<circle cx="%d" cy="%d" r="9" fill="#3b3631"/>'
        '<text x="%d" y="%d" text-anchor="middle" font-size="10" fill="#fff">鍋</text>' % (x, y, x, y + 3.5)
    )


def actor(x, y, who, posture, faded=False):
    char, color = CAST[who]
    if faded:
        return (
            '<circle cx="%d" cy="%d" r="15" fill="#fff" stroke="%s" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.8"/>'
            '<text x="%d" y="%d" text-anchor="middle" font-size="13" fill="%s" opacity="0.8">%s</text>' % (x, y, color, x, y + 4.5, color, char)
        )
    return (
        '<circle cx="%d" cy="%d" r="17" fill="%s" stroke="#fff" stroke-width="2"/>'
        '<text x="%d" y="%d" text-anchor="middle" font-size="15" font-weight="700" fill="#fff">%s</text>'
        '<rect x="%d" y="%d" width="22" height="16" rx="8" fill="#fff" stroke="%s"/>'
        '<text x="%d" y="%d" text-anchor="middle" font-size="11" fill="%s">%s</text>'
        % (x, y, color, x, y + 5, char, x + 10, y + 9, color, x + 21, y + 21, color, posture)
    )


def scene_svg(number, title, time, pot, beats, paths):
    blank = [(x, y) for x, y, center in cells() if not touched(center, paths)]
    total = sum(1 for _ in cells())
    body = []
    for who, points in paths.items():
        color = CAST[who][1]
        for (ax, ay, _, _), (bx, by, _, index) in zip(points, points[1:]):
            gap = math.hypot(bx - ax, by - ay)
            if gap < 1:
                continue
            ratio = max(0.0, (gap - 20) / gap)
            body.append(
                '<line x1="%d" y1="%d" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2.5" marker-end="url(#arrow-%s)"/>'
                % (ax, ay, ax + (bx - ax) * ratio, ay + (by - ay) * ratio, color, CAST[who][0])
            )
            mx, my = ((ax + bx) / 2, (ay + by) / 2) if gap >= 48 else (bx - 30, by - 24)
            body.append('<circle cx="%.1f" cy="%.1f" r="9" fill="#fff" stroke="%s"/>' % (mx, my, color))
            body.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="12" fill="%s">%s</text>' % (mx, my + 4, color, CIRCLED[index]))
    markers = []
    for who, points in paths.items():
        for x, y, posture, _ in points[:-1]:
            markers.append(actor(x, y, who, posture, faded=True))
        x, y, posture, _ = points[-1]
        markers.append(actor(x, y, who, posture))
    left, top, right, bottom = STAGE
    lines = [
        '<text x="%d" y="%d" font-size="13" fill="%s">%s <tspan fill="#2b2622">%s：%s</tspan></text>'
        % (left, bottom + 66 + 22 * i, CAST[who][1], CIRCLED[i], who, label)
        for i, (who, _, _, _, label) in enumerate(beats)
    ]
    height = bottom + 66 + 22 * len(beats) + 52
    legend = (
        '<text x="%d" y="%d" font-size="11.5" fill="#6f655c">實心＝這段結束時的位置，虛線圈＝出發點，數字＝移動順序，右下小標是姿式。</text>'
        '<text x="%d" y="%d" font-size="11.5" fill="#6f655c">斜線區＝這段沒有人到過的地板（離每個人與移動路線都超過約兩個身位）。</text>'
        % (left, height - 34, left, height - 16)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="PingFang TC, Noto Sans TC, Microsoft JhengHei, sans-serif">'
        % (WIDTH, height, WIDTH, height) + defs() +
        '<rect width="100%%" height="100%%" fill="#faf6f0"/>'
        '<text x="%d" y="34" font-size="20" font-weight="700" fill="#2b2622">%s <tspan font-size="14" font-weight="400" fill="#6f655c">%s</tspan></text>' % (left, title, time) +
        '<text x="%d" y="34" text-anchor="end" font-size="13" fill="#6f655c">空白 %d%%</text>' % (right, round(100 * len(blank) / total)) +
        stage_base(hatch(blank)) + pot_icon(*pot) + "\n".join(body) + "\n".join(markers) + "\n".join(lines) + legend + "</svg>"
    )


def overview_svg(scenes):
    counts = {}
    for _, _, _, _, paths in scenes:
        for x, y, center in cells():
            counts[(x, y)] = counts.get((x, y), 0) + (1 if touched(center, paths) else 0)
    heat = []
    for (x, y), count in counts.items():
        if count:
            heat.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#c43c35" opacity="%.2f"/>' % (x, y, CELL, CELL, 0.06 + 0.09 * count))
    blank = [cell for cell, count in counts.items() if count == 0]
    trails = []
    for who in CAST:
        color = CAST[who][1]
        spots = [OPENING[who][:2]] + [(x, y) for _, _, _, _, paths in scenes for x, y, _, index in paths[who][1:]]
        trails.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.5" stroke-linejoin="round" opacity="0.9"/>' % (" ".join("%d,%d" % spot for spot in spots), color))
    finals = []
    for who in CAST:
        x, y, posture = OPENING[who]
        finals.append(actor(x, y, who, posture, faded=True))
    left, top, right, bottom = STAGE
    legend_items = "".join(
        '<circle cx="%d" cy="%d" r="7" fill="%s"/><text x="%d" y="%d" font-size="13" fill="#2b2622">%s</text>'
        % (left + 10 + 92 * i, bottom + 62, color, left + 22 + 92 * i, bottom + 67, who)
        for i, (who, (_, color)) in enumerate(CAST.items())
    )
    total = len(counts)
    usage = "　".join("%s %d%%" % (title.split("　")[0], round(100 * sum(1 for x, y, c in cells() if not touched(c, paths)) / total)) for title, _, _, _, paths in scenes)
    height = bottom + 150
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="PingFang TC, Noto Sans TC, Microsoft JhengHei, sans-serif">'
        % (WIDTH, height, WIDTH, height) + defs() +
        '<rect width="100%%" height="100%%" fill="#faf6f0"/>'
        '<text x="%d" y="34" font-size="20" font-weight="700" fill="#2b2622">全劇走位總覽 <tspan font-size="14" font-weight="400" fill="#6f655c">0:00–7:30</tspan></text>' % left +
        '<text x="%d" y="34" text-anchor="end" font-size="13" fill="#6f655c">整齣都沒人到過 %d%%</text>' % (right, round(100 * len(blank) / total)) +
        stage_base("\n".join(heat) + hatch(blank)) + "\n".join(trails) + "\n".join(finals) + legend_items +
        '<text x="%d" y="%d" font-size="12.5" fill="#2b2622">各段空白比例：%s</text>' % (left, bottom + 94, usage) +
        '<text x="%d" y="%d" font-size="11.5" fill="#6f655c">線＝每個角色整齣戲的移動軌跡（虛線圈是開場位置）。紅色越深＝越多段落有人經過，斜線區＝六段都沒有人到過。</text>' % (left, bottom + 118) +
        "</svg>"
    )


def page(images):
    figures = "".join('<section><img src="' + image.as_uri() + '"></section>' for image in images)
    return (
        '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>早知道就出門了 · 走位圖</title><style>'
        "@page { size: A4 landscape; margin: 8mm; }"
        "body { margin: 0; background: #faf6f0; }"
        "section { break-after: page; display: flex; justify-content: center; }"
        "section:last-child { break-after: auto; }"
        "section img { height: 190mm; max-width: 100%; object-fit: contain; }"
        "</style></head><body>" + figures + "</body></html>"
    )


def screenshot(svg, target, work):
    height = int(svg.split('height="', 1)[1].split('"', 1)[0])
    source = Path(work) / (target.stem + ".html")
    source.write_text('<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}</style></head><body>' + svg + "</body></html>", encoding="utf-8")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
         "--window-size=%d,%d" % (WIDTH, height), "--screenshot=" + str(target), source.as_uri()],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def main():
    scenes = walk()
    svgs = [scene_svg(number, *scene) for number, scene in enumerate(scenes, 1)]
    svgs.append(overview_svg(scenes))
    OUT.mkdir(exist_ok=True)
    names = ["scene-%d" % number for number in range(1, len(scenes) + 1)] + ["overview"]
    with tempfile.TemporaryDirectory() as work:
        for name, svg in zip(names, svgs):
            (OUT / (name + ".svg")).write_text(svg, encoding="utf-8")
            screenshot(svg, OUT / (name + ".png"), work)
            print("blocking/" + name + ".png")
        source = Path(work) / "blocking.html"
        source.write_text(page([OUT / (name + ".png") for name in [names[-1]] + names[:-1]]), encoding="utf-8")
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             "--print-to-pdf=" + str(OUT / "blocking.pdf"), source.as_uri()],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print("blocking/blocking.pdf")


if __name__ == "__main__":
    main()
