#!/usr/bin/env python3
"""Рисует карточку статистики из публичного GitHub API. Только stdlib.

Дизайн:
  - панель со своим тёмным фоном, поэтому одинаково читается
    и на светлой, и на тёмной теме GitHub;
  - бары языков — ОДНА серия (доля кода), значит один цвет на все:
    цвет не должен дублировать длину;
  - у каждого бара свой лейбл и процент, так что ничего не спрятано
    за наведение (в README оно всё равно недоступно).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone

USER = os.environ.get("STATS_USER", "q0tik")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# — палитра —
SURFACE = "#1a1a19"   # фон панели (валидированная тёмная поверхность)
BORDER = "#2f2e2b"
INK = "#ffffff"       # основной текст
MUTED = "#c3c2b7"     # вторичный текст
TRACK = "#2a2926"     # подложка бара
# янтарь в тон шубки Текилы; проходит светлоту, хрому и контраст к SURFACE
ACCENT = "#c2882a"

W = 480
PAD = 18
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def api(path):
    """GET к API. Возвращает None при любой ошибке — лучше скрыть плитку,
    чем показать неверный ноль."""
    req = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-profile-card",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  ! {path} -> {e}", file=sys.stderr)
        return None


def search_count(q):
    d = api(f"search/issues?q={q}&per_page=1")
    return d.get("total_count") if isinstance(d, dict) else None


def collect():
    prof = api(f"users/{USER}") or {}
    repos = api(f"users/{USER}/repos?per_page=100&type=owner") or []
    own = [r for r in repos if not r.get("fork")]

    langs = Counter()
    for r in own:
        d = api(f"repos/{USER}/{r['name']}/languages")
        if d:
            langs.update(d)

    commits = api(f"search/commits?q=author:{USER}&per_page=1")
    return {
        "repos": len(own) or prof.get("public_repos"),
        "stars": sum(r.get("stargazers_count", 0) for r in own),
        "commits": commits.get("total_count") if isinstance(commits, dict) else None,
        "prs": search_count(f"author:{USER}+type:pr"),
        "issues": search_count(f"author:{USER}+type:issue"),
        "followers": prof.get("followers"),
        "since": (prof.get("created_at") or "")[:4],
        "langs": langs,
    }


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def human(n):
    return f"{n/1000:.1f}k".replace(".0k", "k") if n and n >= 1000 else str(n)


def bar(x, y, w, h, fill):
    """Бар со скруглённым правым (data) концом; левый прижат к базе."""
    r = min(h / 2, w)
    if w <= r:
        return f'<rect x="{x}" y="{y}" width="{max(w,1):.1f}" height="{h}" rx="{w/2:.1f}" fill="{fill}"/>'
    return (
        f'<path d="M{x} {y} H{x+w-r:.1f} A{r} {r} 0 0 1 {x+w-r:.1f} {y+h} '
        f'H{x} Z" fill="{fill}"/>'
    )


def render(s):
    top = PAD
    parts = []

    # — заголовок —
    parts.append(
        f'<text x="{PAD}" y="{top+14}" fill="{INK}" font-family="{FONT}" '
        f'font-size="15" font-weight="700">{esc(USER)}</text>'
    )
    if s["since"]:
        parts.append(
            f'<text x="{W-PAD}" y="{top+14}" fill="{MUTED}" font-family="{FONT}" '
            f'font-size="11" text-anchor="end">on GitHub since {s["since"]}</text>'
        )
    y = top + 34

    # — KPI-плитки: только те, что реально удалось получить —
    tiles = [(l, v) for l, v in (
        ("repos", s["repos"]), ("stars", s["stars"]),
        ("commits", s["commits"]), ("PRs", s["prs"]),
    ) if v is not None]

    if tiles:
        tw = (W - 2 * PAD) / len(tiles)
        for i, (label, val) in enumerate(tiles):
            cx = PAD + tw * i
            parts.append(
                f'<text x="{cx:.1f}" y="{y+20}" fill="{ACCENT}" font-family="{FONT}" '
                f'font-size="24" font-weight="700">{human(val)}</text>'
            )
            parts.append(
                f'<text x="{cx:.1f}" y="{y+36}" fill="{MUTED}" font-family="{FONT}" '
                f'font-size="11">{esc(label)}</text>'
            )
        y += 56

    # — языки —
    total = sum(s["langs"].values())
    if total:
        parts.append(
            f'<text x="{PAD}" y="{y+10}" fill="{MUTED}" font-family="{FONT}" '
            f'font-size="11" letter-spacing="1">MOST USED LANGUAGES</text>'
        )
        y += 24

        top6 = s["langs"].most_common(6)
        rest = total - sum(v for _, v in top6)
        rows = top6 + ([("Other", rest)] if rest > 0 else [])

        bx, bw, bh = 108, 268, 8
        for name, val in rows:
            pct = 100 * val / total
            parts.append(
                f'<text x="{PAD}" y="{y+8}" fill="{INK}" font-family="{FONT}" '
                f'font-size="11">{esc(name[:12])}</text>'
            )
            parts.append(f'<rect x="{bx}" y="{y+1}" width="{bw}" height="{bh}" rx="4" fill="{TRACK}"/>')
            parts.append(bar(bx, y + 1, bw * pct / 100, bh, ACCENT))
            parts.append(
                f'<text x="{W-PAD}" y="{y+8}" fill="{MUTED}" font-family="{FONT}" '
                f'font-size="11" text-anchor="end">{pct:.1f}%</text>'
            )
            y += 20

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parts.append(
        f'<text x="{W-PAD}" y="{y+12}" fill="{MUTED}" font-family="{FONT}" '
        f'font-size="9" text-anchor="end" opacity=".7">updated {stamp}</text>'
    )
    h = y + 24

    body = "\n  ".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
        f'viewBox="0 0 {W} {h}" role="img" aria-label="GitHub statistics for {esc(USER)}">\n'
        f'  <rect x=".5" y=".5" width="{W-1}" height="{h-1}" rx="10" '
        f'fill="{SURFACE}" stroke="{BORDER}"/>\n  {body}\n</svg>\n'
    )


if __name__ == "__main__":
    stats = collect()
    print("собрано:", {k: v for k, v in stats.items() if k != "langs"})
    print("языков:", len(stats["langs"]))

    out = sys.argv[1] if len(sys.argv) > 1 else "stats.svg"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(stats))
    print(f"записано: {out}")
