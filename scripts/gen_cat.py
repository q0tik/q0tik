#!/usr/bin/env python3
"""Текила — полосатая пиксельная кошка, которая идёт и катит клубок.

Цвета сняты пипеткой с настоящей фотографии Текилы.
Анимация покадровая (steps): у пиксель-арта поворот на произвольный
угол размывает сетку, поэтому даже клубок кувыркается шагами по 90°.
"""

PX = 6
W, H = 480, 130

C = {
    "O": "#33260f",  # обводка
    "B": "#b88c4e",  # шубка   — с фото, золотистый бок
    "K": "#614b28",  # полоски — с фото, кольца на хвосте
    "W": "#ece2cc",  # белый   — с фото, передняя лапка
    "P": "#d99a91",  # носик
    "E": "#241a0c",  # глаз
    "Y": "#a8dbf0",  # клубок светлый
    "y": "#3d84ad",  # нить — контрастная, иначе поворот не читается
    "b": "#2a6b91",  # обводка клубка — синяя, а не чёрная:
}                    # с чёрной он читался как консервная банка

# Корпус: голова + туловище (без хвоста и лап). Полоски табби на боку.
BODY = [
    "....................",
    "............O...O...",
    "...........OKO.OKO..",
    "..........OBBBBBBBO.",
    ".........OBBKBBBBBBO",
    ".........OBBEBBBWWPO",
    "......OOOOBBBBBBBWOO",
    ".....OBKBBKBBKBBBBO.",
    "...OBBKBBKBBKBBBBBO.",
    "...OWWWWWWWWWWWWWO..",
    "...OOOOOOOOOOOOOOO..",
]

BLINK = [(12, 5)]  # веко поверх глаза

# Хвост — полосатый, две позы
# Обе позы — замкнутые силуэты: в каждой строке обводка слева и справа,
# а верхняя строка накрывает шерсть под собой. Иначе в кадре зияет дыра.
# Качается только кончик: основание в обеих позах одинаковое и вплотную
# примыкает к спине. Иначе у стыка возникает запертая прозрачная клетка.
TAILS = [
    [".OO..", "OKKO.", "OBBO.", "OKKO.", "OBBO.", "OKKO."],
    ["..OO.", ".OKKO", ".OBBO", "OKKO.", "OBBO.", "OKKO."],
]
TAIL_AT = (1, 2)

# Фазы шага: тёмные лапы, белые носочки
LEGS = [
    ["....K..K....K..K....", "...WW..WW..WW..WW..."],
    [".....KK......KK.....", "....WW.WW...WW.WW..."],
    ["...K....K...K....K..", "..WW....WW.WW....WW."],
    [".....KK......KK.....", "....WW.WW...WW.WW..."],
]

# Клубок — пиксельный, а не идеальный круг
# Узор намеренно НЕсимметричный: нить идёт по диагонали, поэтому при
# повороте на 90° картинка заметно меняется и видно, что клубок катится.
BALL = [
    ".bbb.",
    "byYYb",
    "bYyYb",
    "bYYyb",
    ".bbb.",
]

# страховка от опечаток в картах
_w = len(BODY[0])
_maps = [("BODY", BODY)] + [(f"LEGS[{i}]", f) for i, f in enumerate(LEGS)]
for _n, _m in _maps:
    bad = [(len(r), r) for r in _m if len(r) != _w]
    assert not bad, f"{_n}: ожидалось {_w} символов, получено {bad}"


def _cells(*layers):
    """Занятые клетки для набора (карта, смещение_x, смещение_y)."""
    out = set()
    for m, ox, oy in layers:
        for ry, row in enumerate(m):
            for x, ch in enumerate(row):
                if ch != ".":
                    out.add((ox + x, oy + ry))
    return out


def _holes(cells):
    """Прозрачные клетки, запертые со всех четырёх сторон.

    Именно так появлялась «дырка» в хвосте: сама по себе каждая карта
    выглядит нормально, дыра возникает только на стыке слоёв — и только
    в отдельных кадрах, поэтому глазами её легко пропустить.
    """
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    bad = []
    for y in range(min(ys), max(ys) + 1):
        for x in range(min(xs), max(xs) + 1):
            if (x, y) in cells:
                continue
            if all((x + dx, y + dy) in cells
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                bad.append((x, y))
    return bad


# проверяем КАЖДОЕ сочетание кадров хвоста и лап
for _ti, _tf in enumerate(TAILS):
    for _li, _lf in enumerate(LEGS):
        _h = _holes(_cells((BODY, 0, 0), (_tf, *TAIL_AT), (_lf, 0, 11)))
        assert not _h, f"дыра в спрайте: хвост {_ti}, лапы {_li}, клетки {_h}"


def rects(rows, ox=0, oy=0):
    """Схлопывает горизонтальные серии одинаковых пикселей в один <rect>."""
    out = []
    for ry, row in enumerate(rows):
        x = 0
        while x < len(row):
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            run = 1
            while x + run < len(row) and row[x + run] == ch:
                run += 1
            out.append(
                f'<rect x="{(ox+x)*PX}" y="{(oy+ry)*PX}" '
                f'width="{run*PX}" height="{PX}" fill="{C[ch]}"/>'
            )
            x += run
    return "\n        ".join(out)


def frames(maps, cls, period, oy=0, ox=0):
    """Покадровая анимация через переключение opacity."""
    n = len(maps)
    css, svg = [], []
    for i, m in enumerate(maps):
        a, b = 100 * i / n, 100 * (i + 1) / n
        kf = f"0%,{a-0.01:.2f}%{{opacity:0}}" if i else ""
        kf += f"{a:.2f}%,{b-0.01:.2f}%{{opacity:1}}"
        kf += f"{b:.2f}%,100%{{opacity:0}}" if i < n - 1 else ""
        css.append(f"    @keyframes {cls}{i} {{ {kf} }}")
        css.append(f"    .{cls}{i} {{ animation: {cls}{i} {period} steps(1) infinite; }}")
        svg.append(f'      <g class="{cls}{i}">\n        {rects(m, ox, oy)}\n      </g>')
    return "\n".join(css), "\n".join(svg)


leg_css, leg_svg = frames(LEGS, "lg", ".6s", oy=11)
tail_css, tail_svg = frames(TAILS, "tl", "1.4s", ox=TAIL_AT[0], oy=TAIL_AT[1])

CAT_W = _w * PX
BALL_X = CAT_W + 6
BALL_Y = 8 * PX
BALL_SIZE = len(BALL[0]) * PX
START = -(BALL_X + BALL_SIZE + 20)   # всё целиком за левым краем
GROUND = 13 * PX + 6

blink_svg = "\n      ".join(
    f'<rect class="blink" x="{x*PX}" y="{y*PX}" width="{PX}" height="{PX}" fill="{C["B"]}"/>'
    for x, y in BLINK
)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Tequila, a tabby pixel cat, walking and rolling a ball of yarn">
  <style>
    .walker {{ animation: walk 12s linear infinite; }}
    @keyframes walk {{
      from {{ transform: translateX({START}px); }}
      to   {{ transform: translateX({W + 30}px); }}
    }}

    /* покачивание в такт шагам */
    .bob {{ animation: bob .6s ease-in-out infinite; }}
    @keyframes bob {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-2px)}} }}

{leg_css}
{tail_css}

    /* моргает изредка */
    .blink {{ opacity: 0; animation: blink 5s steps(1) infinite; }}
    @keyframes blink {{ 0%,96%{{opacity:0}} 96.5%,98.5%{{opacity:1}} 99%,100%{{opacity:0}} }}

    /* клубок кувыркается шагами по 90°, чтобы пиксели остались на сетке */
    .ball {{ transform-box: fill-box; transform-origin: center;
            animation: tumble .8s steps(4) infinite; }}
    @keyframes tumble {{ from{{transform:rotate(0)}} to{{transform:rotate(360deg)}} }}

    .ground {{ stroke:#808080; stroke-opacity:.35; stroke-width:2;
              stroke-linecap:round; stroke-dasharray:6 8; }}
  </style>

  <line class="ground" x1="8" y1="{GROUND}" x2="{W-8}" y2="{GROUND}"/>

  <g class="walker">
    <g class="bob">
      <g>
{tail_svg}
      </g>
      <g>
        {rects(BODY)}
      </g>
      {blink_svg}
{leg_svg}
    </g>

    <!-- перенос и вращение РАЗНЫМИ группами: CSS-свойство transform
         перебивает одноимённый SVG-атрибут, и мяч улетел бы в 0,0 -->
    <g transform="translate({BALL_X},{BALL_Y})">
      <g class="ball">
        {rects(BALL)}
      </g>
    </g>
  </g>
</svg>
'''

import pathlib, sys
out = pathlib.Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(svg, encoding="utf-8")
print(f"{out} — {len(svg)} байт | спрайт {CAT_W}x{13*PX}px | старт {START}px")
