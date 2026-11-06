"""生成 GitHub 个人主页的 SVG 卡片，并更新 README 里自动维护的区块。

本地运行：python scripts/build.py           只用 data/*.json 里的数据重新画图
Actions 里：GITHUB_TOKEN=xxx python scripts/build.py --fetch  先抓 GitHub 和 CSDN 的最新数据

抓取失败时保留 data/*.json 里的旧数据，不会把主页弄坏。
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, ASSETS = ROOT / "data", ROOT / "assets"
CN = timezone(timedelta(hours=8))
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei','Noto Sans CJK SC',sans-serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"

THEMES = {
    "light": dict(bg="#ffffff", card="#ffffff", border="#d0d7de", text="#1f2328", sub="#656d76", soft="#f6f8fa",
                  track="#eaeef2"),
    "dark": dict(bg="#0d1117", card="#0d1117", border="#30363d", text="#e6edf3", sub="#8b949e", soft="#161b22",
                 track="#21262d"),
}
ACCENT_A, ACCENT_B = "#7c3aed", "#06b6d4"
LANG_COLORS = {"C++": "#f34b7d", "C": "#555555", "Python": "#3572A5", "HTML": "#e34c26", "JavaScript": "#f1e05a",
               "Java": "#b07219", "CMake": "#DA3434", "Shell": "#89e051", "Other": "#8b949e"}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def text_width(s: str, size: float) -> float:
    w = 0.0
    for ch in s:
        w += size if ord(ch) > 0x2E80 else size * (0.62 if ch.isupper() or ch.isdigit() else 0.55)
    return w


def wrap(s: str, size: float, max_w: float, max_lines: int = 2) -> list[str]:
    """按词换行：英文单词、数字和 / . _ - 连成一个整体，中文逐字。"""
    tokens = re.findall(r"[A-Za-z0-9_./+#-]+|\s|.", s)
    lines, cur = [], ""
    for tok in tokens:
        if text_width(cur + tok, size) > max_w and cur.strip():
            lines.append(cur.rstrip())
            cur = tok.lstrip()
            if len(lines) == max_lines:
                lines[-1] = lines[-1][:-1] + "…"
                return lines
        else:
            cur += tok
    lines.append(cur.rstrip())
    return lines


def fmt_num(n: int | float) -> str:
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return f"{n:,}"


def write(name: str, svg: str) -> None:
    (ASSETS / name).write_text(svg, encoding="utf-8")


def gradient_defs(uid: str) -> str:
    return (f'<linearGradient id="g{uid}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{ACCENT_A}"/><stop offset="1" stop-color="{ACCENT_B}"/></linearGradient>')


# ---------------------------------------------------------------- 横幅
def banner(p: dict) -> str:
    roles = p["roles"]
    n = len(roles)
    dur = n * 3
    role_svg = []
    for i, r in enumerate(roles):
        # 每句显示 3 秒：淡入、停留、淡出
        a, b = i / n, (i + 1) / n
        kt = f"0;{a:.4f};{a + 0.02:.4f};{b - 0.02:.4f};{b:.4f};1"
        vals = "0;0;1;1;0;0"
        role_svg.append(
            f'<text x="80" y="214" class="role" opacity="0">{esc(r)}'
            f'<animate attributeName="opacity" values="{vals}" keyTimes="{kt}" dur="{dur}s" repeatCount="indefinite"/></text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="300" viewBox="0 0 1200 300">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#1e1b4b"/><stop offset="0.55" stop-color="#312e81"/><stop offset="1" stop-color="#0e7490"/>
  </linearGradient>
  <linearGradient id="hl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#c4b5fd"/><stop offset="1" stop-color="#67e8f9"/></linearGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#ffffff" stroke-opacity="0.06"/></pattern>
  <clipPath id="clip"><rect width="1200" height="300" rx="20"/></clipPath>
  <style>
    .name{{font:800 64px {FONT};fill:#fff;letter-spacing:1px}}
    .tag{{font:500 26px {FONT};fill:url(#hl)}}
    .role{{font:400 22px {FONT};fill:#e0e7ff}}
    .mono{{font:500 15px {MONO};fill:#a5b4fc}}
    .chip{{font:600 14px {FONT};fill:#e0f2fe}}
  </style>
</defs>
<g clip-path="url(#clip)">
  <rect width="1200" height="300" fill="url(#bg)"/>
  <rect width="1200" height="300" fill="url(#grid)"/>
  <circle cx="1040" cy="60" r="160" fill="#22d3ee" opacity="0.12"><animate attributeName="r" values="150;175;150" dur="8s" repeatCount="indefinite"/></circle>
  <circle cx="940" cy="280" r="120" fill="#a78bfa" opacity="0.14"><animate attributeName="cy" values="280;250;280" dur="10s" repeatCount="indefinite"/></circle>
  <path d="M0 250 C 200 210, 400 290, 600 250 S 1000 210, 1200 250 V300 H0Z" fill="#ffffff" opacity="0.06">
    <animate attributeName="d" dur="12s" repeatCount="indefinite" values="M0 250 C 200 210, 400 290, 600 250 S 1000 210, 1200 250 V300 H0Z;M0 245 C 220 280, 420 220, 620 255 S 980 280, 1200 240 V300 H0Z;M0 250 C 200 210, 400 290, 600 250 S 1000 210, 1200 250 V300 H0Z"/>
  </path>
  <text x="80" y="62" class="mono">$ whoami</text>
  <text x="80" y="132" class="name">{esc(p["name"])}</text>
  <text x="80" y="174" class="tag">{esc(p["tagline"])}</text>
  {"".join(role_svg)}
  <rect x="80" y="234" width="2" height="24" fill="#67e8f9"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>
  <g transform="translate(900,120)">
    <rect width="220" height="120" rx="14" fill="#0f172a" opacity="0.55" stroke="#ffffff" stroke-opacity="0.15"/>
    <circle cx="20" cy="18" r="5" fill="#f87171"/><circle cx="36" cy="18" r="5" fill="#fbbf24"/><circle cx="52" cy="18" r="5" fill="#34d399"/>
    <text x="18" y="52" class="mono">#include &lt;life&gt;</text>
    <text x="18" y="76" class="mono" fill="#67e8f9">while (alive) {{</text>
    <text x="34" y="98" class="mono">learn(); share();</text>
    <text x="18" y="116" class="mono">}}</text>
  </g>
  <g transform="translate(900,62)">
    <rect width="130" height="30" rx="15" fill="#ffffff" fill-opacity="0.12"/>
    <text x="65" y="20" text-anchor="middle" class="chip">CSDN · {esc(p["nickname"])}</text>
  </g>
</g>
</svg>'''


# ---------------------------------------------------------------- 项目卡片
def repo_card(item: dict, stars: int, theme: str, login: str) -> str:
    t = THEMES[theme]
    lines = wrap(item["desc"], 14, 370, 2)
    desc = "".join(f'<tspan x="24" dy="{0 if i == 0 else 22}">{esc(s)}</tspan>' for i, s in enumerate(lines))
    color = LANG_COLORS.get(item["lang"], "#8b949e")
    uid = re.sub(r"\W", "", item["repo"]) + theme
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="150" viewBox="0 0 420 150">
<defs>{gradient_defs(uid)}</defs>
<rect x="0.5" y="0.5" width="419" height="149" rx="12" fill="{t["card"]}" stroke="{t["border"]}"/>
<rect x="0.5" y="0.5" width="4" height="149" rx="2" fill="url(#g{uid})"/>
<g font-family="{FONT}">
  <path transform="translate(24,22)" fill="{t["sub"]}" d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z"/>
  <text x="46" y="35" font-size="17" font-weight="700" fill="url(#g{uid})">{esc(item["title"])}</text>
  <text x="{46 + text_width(item["title"], 17) + 10:.0f}" y="35" font-size="13" fill="{t["sub"]}">{esc(login)}/{esc(item["repo"])}</text>
  <text x="24" y="70" font-size="14" fill="{t["text"]}">{desc}</text>
  <circle cx="30" cy="124" r="6" fill="{color}"/>
  <text x="42" y="129" font-size="13" fill="{t["sub"]}">{esc(item["lang"])}</text>
  <path transform="translate({58 + text_width(item["lang"], 13):.0f},116)" fill="{t["sub"]}" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>
  <text x="{78 + text_width(item["lang"], 13):.0f}" y="129" font-size="13" fill="{t["sub"]}">{stars}</text>
</g>
</svg>'''


# ---------------------------------------------------------------- 统计卡片
def stat_box(x: float, y: float, w: float, value: str, label: str, t: dict, uid: str) -> str:
    return (f'<g transform="translate({x:.0f},{y})"><rect width="{w:.0f}" height="78" rx="10" fill="{t["soft"]}"/>'
            f'<text x="{w / 2:.0f}" y="38" text-anchor="middle" font-size="24" font-weight="800" fill="url(#g{uid})">{esc(value)}</text>'
            f'<text x="{w / 2:.0f}" y="62" text-anchor="middle" font-size="13" fill="{t["sub"]}">{esc(label)}</text></g>')


def csdn_card(c: dict, theme: str) -> str:
    t = THEMES[theme]
    uid = "csdn" + theme
    stats = [(fmt_num(c["views"]), "总访问量"), (str(c["articles"]), "原创文章"), (fmt_num(c["likes"]), "获赞"),
             (fmt_num(c["favorites"]), "被收藏"), (str(c["fans"]), "粉丝")]
    gap = 12
    w = (776 - gap * (len(stats) - 1)) / len(stats)
    boxes = "".join(stat_box(24 + i * (w + gap), 66, w, v, l, t, uid) for i, (v, l) in enumerate(stats))
    cols = c["columns"][:8]
    top = max(v for _, v in cols) if cols else 1
    bars = []
    for i, (name, v) in enumerate(cols):
        col, row = i % 2, i // 2
        x, y = 24 + col * 400, 192 + row * 30
        bw = 230 * v / top
        bars.append(
            f'<text x="{x}" y="{y + 12}" font-size="13" fill="{t["text"]}">{esc(name)}</text>'
            f'<rect x="{x + 100}" y="{y + 2}" width="230" height="12" rx="6" fill="{t["track"]}"/>'
            f'<rect x="{x + 100}" y="{y + 2}" width="{bw:.1f}" height="12" rx="6" fill="url(#g{uid})"/>'
            f'<text x="{x + 340}" y="{y + 12}" font-size="12" fill="{t["sub"]}">{v} 篇</text>'
        )
    h = 192 + ((len(cols) + 1) // 2) * 30 + 22
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="824" height="{h}" viewBox="0 0 824 {h}">
<defs>{gradient_defs(uid)}</defs>
<rect x="0.5" y="0.5" width="823" height="{h - 1}" rx="14" fill="{t["card"]}" stroke="{t["border"]}"/>
<g font-family="{FONT}">
  <rect x="24" y="22" width="58" height="26" rx="6" fill="#fc5531"/>
  <text x="53" y="40" text-anchor="middle" font-size="14" font-weight="800" fill="#fff">CSDN</text>
  <text x="94" y="41" font-size="18" font-weight="700" fill="{t["text"]}">海盗船长y 的技术博客</text>
  <text x="800" y="41" text-anchor="end" font-size="12" fill="{t["sub"]}">总排名 {c["rank"]:,} · 更新于 {esc(c["updated"])}</text>
  {boxes}
  <text x="24" y="178" font-size="14" font-weight="700" fill="{t["text"]}">专栏分布</text>
  {"".join(bars)}
</g>
</svg>'''


def github_card(g: dict, theme: str) -> str:
    t = THEMES[theme]
    uid = "gh" + theme
    stats = [(str(g["original_repos"]), "原创仓库"), (str(g["public_repos"]), "公开仓库"), (str(g["stars"]), "获得 Star"),
             (str(g["followers"]), "关注者"),
             (fmt_num(g["contributions"]) if g.get("contributions") is not None else "—", "近一年贡献")]
    gap = 12
    w = (776 - gap * (len(stats) - 1)) / len(stats)
    boxes = "".join(stat_box(24 + i * (w + gap), 62, w, v, l, t, uid) for i, (v, l) in enumerate(stats))
    langs = g["languages"]
    total = sum(v for _, v in langs) or 1
    x, segs, legend = 24.0, [], []
    for i, (name, v) in enumerate(langs):
        wseg = 776 * v / total
        segs.append(f'<rect x="{x:.1f}" y="182" width="{wseg:.1f}" height="12" fill="{LANG_COLORS.get(name, "#8b949e")}"/>')
        x += wseg
        lx = 24 + i * 156
        legend.append(f'<circle cx="{lx + 6}" cy="220" r="5" fill="{LANG_COLORS.get(name, "#8b949e")}"/>'
                      f'<text x="{lx + 16}" y="225" font-size="13" fill="{t["text"]}">{esc(name)} '
                      f'<tspan fill="{t["sub"]}">{v / total * 100:.0f}%</tspan></text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="824" height="250" viewBox="0 0 824 250">
<defs>{gradient_defs(uid)}<clipPath id="bar{uid}"><rect x="24" y="182" width="776" height="12" rx="6"/></clipPath></defs>
<rect x="0.5" y="0.5" width="823" height="249" rx="14" fill="{t["card"]}" stroke="{t["border"]}"/>
<g font-family="{FONT}">
  <path transform="translate(24,22) scale(1.4)" fill="{t["text"]}" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
  <text x="56" y="41" font-size="18" font-weight="700" fill="{t["text"]}">GitHub 数据</text>
  <text x="800" y="41" text-anchor="end" font-size="12" fill="{t["sub"]}">更新于 {esc(g["updated"])}</text>
  {boxes}
  <text x="24" y="170" font-size="14" font-weight="700" fill="{t["text"]}">原创仓库语言占比</text>
  <g clip-path="url(#bar{uid})"><rect x="24" y="182" width="776" height="12" fill="{t["track"]}"/>{"".join(segs)}</g>
  {"".join(legend)}
</g>
</svg>'''


# ---------------------------------------------------------------- 抓取
def http_get(url: str, token: str | None = None, data: bytes | None = None) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "fxianglong-profile-builder"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def fetch_github(p: dict, old: dict) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    login = p["login"]
    user = json.loads(http_get(f"https://api.github.com/users/{login}", token))
    repos = json.loads(http_get(f"https://api.github.com/users/{login}/repos?per_page=100&type=owner", token))
    own = [r for r in repos if not r["fork"] and not r["private"]]
    langs: dict[str, int] = {}
    for r in own:
        try:
            for k, v in json.loads(http_get(r["languages_url"], token)).items():
                langs[k] = langs.get(k, 0) + v
        except Exception as e:  # noqa: BLE001
            print("languages failed", r["name"], e, file=sys.stderr)
    top = sorted(langs.items(), key=lambda x: -x[1])
    lang_list = top[:4] + ([("Other", sum(v for _, v in top[4:]))] if len(top) > 4 else [])
    contributions = old.get("contributions")
    if token:
        q = {"query": f'{{user(login:"{login}"){{contributionsCollection{{contributionCalendar{{totalContributions}}}}}}}}'}
        try:
            res = json.loads(http_get("https://api.github.com/graphql", token, json.dumps(q).encode()))
            contributions = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        except Exception as e:  # noqa: BLE001
            print("graphql failed", e, file=sys.stderr)
    return {
        "updated": datetime.now(CN).strftime("%Y-%m-%d"),
        "public_repos": user["public_repos"],
        "original_repos": len(own),
        "stars": sum(r["stargazers_count"] for r in own),
        "followers": user["followers"],
        "contributions": contributions,
        "languages": lang_list or old["languages"],
        "repo_stars": {r["name"]: r["stargazers_count"] for r in repos},
    }


def fetch_csdn(p: dict, old: dict) -> dict:
    new = dict(old)
    try:
        root = ET.fromstring(http_get(p["csdn_rss"]))
        items = []
        for it in root.iter("item"):
            title, link = (it.findtext("title") or "").strip(), (it.findtext("link") or "").strip()
            try:
                date = parsedate_to_datetime(it.findtext("pubDate")).astimezone(CN).strftime("%Y-%m-%d")
            except Exception:  # noqa: BLE001
                date = ""
            if title and link:
                items.append({"title": title, "url": link, "date": date})
        if items:
            new["latest"] = items[:5]
    except Exception as e:  # noqa: BLE001
        print("csdn rss failed", e, file=sys.stderr)
    try:
        page = http_get(p["csdn_url"]).decode("utf-8", "ignore")
        patterns = {"views": r'"?visitCount"?\s*[:=]\s*"?(\d+)', "articles": r'"?originalCount"?\s*[:=]\s*"?(\d+)',
                    "fans": r'"?fansCount"?\s*[:=]\s*"?(\d+)'}
        for k, pat in patterns.items():
            m = re.search(pat, page)
            # 这些数字只会增长：抓到的值明显变小说明匹配错了，保留旧值
            if m and int(m.group(1)) >= old.get(k, 0) * 0.9:
                new[k] = int(m.group(1))
    except Exception as e:  # noqa: BLE001
        print("csdn page failed", e, file=sys.stderr)
    new["updated"] = datetime.now(CN).strftime("%Y-%m-%d")
    return new


# ---------------------------------------------------------------- README
def replace_block(text: str, name: str, body: str) -> str:
    pat = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    return pat.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def update_readme(p: dict, c: dict) -> None:
    readme = ROOT / "README.md"
    text = readme.read_text("utf-8")
    latest = "\n".join(f"- `{a['date']}` [{a['title']}]({a['url']})" for a in c["latest"][:5])
    hot = "\n".join(f"- [{a['title']}]({a['url']}) · {a['views']:,} 阅读" for a in p["hot_articles"])
    text = replace_block(text, "CSDN-LATEST", latest)
    text = replace_block(text, "CSDN-HOT", hot)
    readme.write_text(text, "utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="抓取 GitHub 和 CSDN 的最新数据")
    args = ap.parse_args()
    ASSETS.mkdir(exist_ok=True)
    p = json.loads((DATA / "profile.json").read_text("utf-8"))
    c = json.loads((DATA / "csdn.json").read_text("utf-8"))
    g = json.loads((DATA / "github.json").read_text("utf-8"))
    if args.fetch:
        try:
            g = fetch_github(p, g)
        except Exception as e:  # noqa: BLE001
            print("github fetch failed, keep old data", e, file=sys.stderr)
        c = fetch_csdn(p, c)
        (DATA / "github.json").write_text(json.dumps(g, ensure_ascii=False, indent=2) + "\n", "utf-8")
        (DATA / "csdn.json").write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", "utf-8")

    write("banner.svg", banner(p))
    for theme in THEMES:
        write(f"csdn-{theme}.svg", csdn_card(c, theme))
        write(f"github-{theme}.svg", github_card(g, theme))
        for item in p["featured"]:
            write(f"repo-{item['repo']}-{theme}.svg",
                  repo_card(item, g.get("repo_stars", {}).get(item["repo"], 0), theme, p["login"]))
    update_readme(p, c)
    print("done")


if __name__ == "__main__":
    main()
