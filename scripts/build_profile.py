#!/usr/bin/env python3
"""Builds assets/neofetch.svg and assets/metrics.svg from live public GitHub data.
Stdlib only. Uses GITHUB_TOKEN if present (higher API limits), falls back to public pages."""
import json, os, re, sys, math, datetime as dt, urllib.request, urllib.error
from html import escape

USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "VijayLabKit"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")

FONT = "'JetBrains Mono','Fira Code','SF Mono',Consolas,'DejaVu Sans Mono','Courier New',monospace"
RED, HOT, BG, LINE, DIM, FG = "#ff2d2d", "#ff4d4d", "#05070a", "#252b36", "#8b949e", "#e6edf3"

def http(url, accept=None, auth=False):
    h = {"User-Agent": "Mozilla/5.0 (profile-builder)"}
    if accept: h["Accept"] = accept
    if auth and TOKEN: h["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read().decode("utf-8", "replace")

# ---------------- data ----------------
def get_calendar():
    html = http(f"https://github.com/users/{USER}/contributions")
    tips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>', html))
    days = []
    for m in re.finditer(r'<td[^>]*?data-date="([\d-]+)"[^>]*?id="([^"]+)"[^>]*?data-level="(\d)"', html):
        date, cid, lvl = m.group(1), m.group(2), int(m.group(3))
        t = tips.get(cid, "")
        n = re.match(r"(\d+) contribution", t)
        days.append((date, lvl, int(n.group(1)) if n else 0))
    days.sort()
    if not days:
        raise RuntimeError("no calendar cells parsed")
    return days

def get_repos():
    """returns (repo_count, [(language, weight)], mode)"""
    try:
        repos = json.loads(http(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner", "application/vnd.github+json", True))
        if not isinstance(repos, list): raise RuntimeError("api")
        own = [r for r in repos if not r.get("fork")]
        agg = {}
        try:
            for r in own:
                langs = json.loads(http(r["languages_url"], "application/vnd.github+json", True))
                for k, v in langs.items(): agg[k] = agg.get(k, 0) + v
            if agg: return len(repos), sorted(agg.items(), key=lambda kv: -kv[1]), "by code size"
        except Exception:
            pass
        agg = {}
        for r in own:
            if r.get("language"): agg[r["language"]] = agg.get(r["language"], 0) + 1
        return len(repos), sorted(agg.items(), key=lambda kv: -kv[1]), "by repository"
    except Exception:
        html = http(f"https://github.com/{USER}?tab=repositories")
        names = re.findall(r'itemprop="name codeRepository"[^>]*>\s*([^<\s]+)', html)
        langs = re.findall(r'itemprop="programmingLanguage">([^<]+)<', html)
        agg = {}
        for l in langs: agg[l] = agg.get(l, 0) + 1
        return len(names), sorted(agg.items(), key=lambda kv: -kv[1]), "by repository"

def streaks(days):
    best = cur = run = 0
    for _, _, n in days:
        run = run + 1 if n > 0 else 0
        best = max(best, run)
    # current streak: walk back from the last day, allowing today to be empty
    i = len(days) - 1
    if days[i][2] == 0: i -= 1
    cur = 0
    while i >= 0 and days[i][2] > 0:
        cur += 1; i -= 1
    return best, cur

# ---------------- shared ----------------
def svg_open(w, h, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{escape(label)}">')

def lang_colors(n):
    pal = [HOT, "#c92a2a", "#9b2226", "#6b1a1d", "#454c58", "#2d333d"]
    return pal[:n] + [pal[-1]] * max(0, n - len(pal))

# ---------------- neofetch ----------------
def build_neofetch(days, repo_count):
    art = json.load(open(os.path.join(HERE, "ascii.json")))
    rows, eyes, cols = art["rows"], art["eyes"], art["cols"]
    fs, cw, lh = 12, 7.2, 14.4
    x_art, y0 = 40, 92
    x_info = x_art + cols * cw + 44
    total = sum(n for _, _, n in days)
    best, cur = streaks(days)
    active = sum(1 for _, _, n in days if n > 0)

    art_svg = ""
    for r, line in enumerate(rows):
        y = y0 + r * lh
        out, i = "", 0
        while i < len(line):
            red = eyes[r][i] == "1"
            j = i
            while j < len(line) and (eyes[r][j] == "1") == red: j += 1
            seg = escape(line[i:j])
            fill = RED if red else "#c9d1d9"
            op = "1" if red else "0.9"
            out += f'<tspan fill="{fill}" fill-opacity="{op}">{seg}</tspan>'
            i = j
        art_svg += f'<text x="{x_art}" y="{y:.1f}" font-size="{fs}" xml:space="preserve" textLength="{cols*cw:.1f}" lengthAdjust="spacing">{out}</text>\n'

    KEYW = 128
    info = [
        ("head", "ishan@zeroday"),
        ("kv", "Role", "Security Researcher · Developer · Red Team"),
        ("kv", "Org", "ZeroDay Security Services (founder)"),
        ("kv", "Location", "Siliguri, West Bengal, India"),
        ("kv", "Focus", "Offensive Security / AI Security"),
        ("kv", "Community", "OWASP Siliguri · CyRaksha Siliguri"),
        ("gap",),
        ("sec", "Stack"),
        ("kv", "Languages", "Python, C, Java, Bash, PowerShell, PHP"),
        ("kv", "Tooling", "Burp Suite, Nmap, Metasploit, Wireshark, Nessus"),
        ("kv", "Frameworks", "OWASP, MITRE ATT&CK, NIST"),
        ("gap",),
        ("sec", "Projects"),
        ("kv", "Building", "VulnScope Pro · OWASP LLM Lab · PromptPwn"),
        ("gap",),
        ("sec", "Contact"),
        ("kv", "Email", "vijayishanchowdhury@gmail.com"),
        ("kv", "LinkedIn", "in/vijay-ishan"),
        ("kv", "GitHub", USER),
        ("gap",),
        ("sec", "GitHub"),
        ("kv", "Repos", f"{repo_count} public"),
        ("kv", "Activity", f"{total} contributions / 12 mo · {active} active days · {cur}d streak"),
    ]
    svg_info, delay = "", 0.3
    for i, it in enumerate(info):
        y = y0 + i * lh
        if it[0] == "gap": continue
        a = f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="0.15s" fill="freeze"/>'
        delay += 0.11
        if it[0] == "head":
            svg_info += f'<g opacity="0">{a}<text x="{x_info}" y="{y:.1f}" font-size="13" font-weight="700"><tspan fill="{HOT}">{escape(it[1])}</tspan></text><rect x="{x_info+len(it[1])*7.8+10:.0f}" y="{y-4:.1f}" width="{980-(x_info+len(it[1])*7.8+10):.0f}" height="1" fill="{LINE}"/></g>\n'
        elif it[0] == "sec":
            svg_info += f'<g opacity="0">{a}<text x="{x_info}" y="{y:.1f}" font-size="12.5" font-weight="700" fill="{FG}">- {escape(it[1])}</text><rect x="{x_info+(len(it[1])+3)*7.5+4:.0f}" y="{y-4:.1f}" width="{980-(x_info+(len(it[1])+3)*7.5+4):.0f}" height="1" fill="{LINE}"/></g>\n'
        else:
            k, v = it[1], it[2]
            kw = len(k) * 7.5
            dots_w = max(0, KEYW - kw - 8)
            svg_info += (f'<g opacity="0">{a}<text x="{x_info}" y="{y:.1f}" font-size="12.5" fill="{HOT}">{escape(k)}</text>'
                         f'<text x="{x_info+kw+4:.1f}" y="{y:.1f}" font-size="12.5" fill="#3a414c" textLength="{dots_w:.1f}" lengthAdjust="spacing">{"."*int(dots_w/7.5)}</text>'
                         f'<text x="{x_info+KEYW:.1f}" y="{y:.1f}" font-size="12.5" fill="{FG}" xml:space="preserve">{escape(v)}</text></g>\n')
    H = int(y0 + max(len(rows), len(info)) * lh + 40)
    cur_y = y0 + len(info) * lh
    return f'''{svg_open(1000, H, "Terminal card: ASCII hooded figure with profile details of Ishan Chowdhury")}
<defs><linearGradient id="bar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#11151b"/><stop offset="1" stop-color="#0b0e13"/></linearGradient>
<radialGradient id="g" cx="20%" cy="45%" r="45%"><stop offset="0" stop-color="{RED}" stop-opacity="0.10"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient></defs>
<g font-family="{FONT}">
  <rect x="0.5" y="0.5" width="999" height="{H-1}" rx="8" fill="{BG}" stroke="{LINE}"/>
  <rect x="1" y="1" width="998" height="{H-2}" rx="8" fill="url(#g)"/>
  <path d="M0.5 8.5a8 8 0 0 1 8-8H991.5a8 8 0 0 1 8 8V44H0.5Z" fill="url(#bar)"/>
  <line x1="0" y1="44.5" x2="1000" y2="44.5" stroke="{LINE}"/>
  <circle cx="26" cy="23" r="6" fill="{RED}"/><circle cx="48" cy="23" r="6" fill="#3a414c"/><circle cx="70" cy="23" r="6" fill="#3a414c"/>
  <text x="500" y="28" font-size="13" fill="{DIM}" text-anchor="middle" letter-spacing="1">ishan@zeroday: ~ — neofetch</text>
  <text x="40" y="72" font-size="12.5" fill="{DIM}"><tspan fill="{RED}">$</tspan> neofetch --profile</text>
{art_svg}{svg_info}
  <rect x="{x_info}" y="{cur_y-10:.1f}" width="8" height="14" fill="{RED}" opacity="0"><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.01;0.5;0.51;1" dur="1.1s" begin="3s" repeatCount="indefinite"/></rect>
</g>
</svg>
'''

# ---------------- metrics ----------------
def iso_calendar(days, x_min, x_max, y_min, y_max):
    # arrange into week columns (Sun..Sat)
    weeks, col = [], [None] * 7
    for date, lvl, n in days:
        wd = (dt.date.fromisoformat(date).weekday() + 1) % 7  # Sunday=0
        if wd == 0 and any(c is not None for c in col):
            weeks.append(col); col = [None] * 7
        col[wd] = (date, lvl, n)
    weeks.append(col)
    W = len(weeks)
    mx = max((n for _, _, n in days), default=1) or 1
    t = 8.4
    A, B = t * 0.866, t * 0.5
    maxh = 78
    def P(u, v, h=0): return ((u - v) * A, (u + v) * B - h)
    cells = []
    for w in range(W):
        for d in range(7):
            c = weeks[w][d]
            if c is None: continue
            date, lvl, n = c
            h = 1.6 if n == 0 else 6 + math.sqrt(n / mx) * maxh
            cells.append((w + d, w, d, lvl, h))
    cells.sort()
    # bounding box
    xs, ys = [], []
    for _, w, d, lvl, h in cells:
        for (u, v, hh) in [(w, d, h), (w + 1, d + 1, 0), (w + 1, d, h), (w, d + 1, h)]:
            x, y = P(u, v, hh); xs.append(x); ys.append(y)
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    sc = min((x_max - x_min) / bw, (y_max - y_min) / bh, 1.35)
    ox = x_min + ((x_max - x_min) - bw * sc) / 2 - min(xs) * sc
    oy = y_min + ((y_max - y_min) - bh * sc) / 2 - min(ys) * sc
    pal = {0: ("#121820", "#0c1015", "#0e1218"), 1: ("#7a1a1f", "#4d1014", "#5f1318"), 2: ("#b0222a", "#701519", "#8a1a20"),
           3: ("#e02b33", "#9a1b21", "#bb2128"), 4: ("#ff5a5a", "#c92a2a", "#e23636")}
    g = 0.06
    out = f'<g transform="translate({ox:.1f} {oy:.1f}) scale({sc:.3f})">'
    for _, w, d, lvl, h in cells:
        top, left, right = pal[lvl]
        N, E = P(w + g, d + g, h), P(w + 1 - g, d + g, h)
        S, Wp = P(w + 1 - g, d + 1 - g, h), P(w + g, d + 1 - g, h)
        Sb, Wb, Eb = P(w + 1 - g, d + 1 - g), P(w + g, d + 1 - g), P(w + 1 - g, d + g)
        f = lambda p: f"{p[0]:.1f},{p[1]:.1f}"
        out += (f'<polygon points="{f(Wp)} {f(S)} {f(Sb)} {f(Wb)}" fill="{left}"/>'
                f'<polygon points="{f(S)} {f(E)} {f(Eb)} {f(Sb)}" fill="{right}"/>'
                f'<polygon points="{f(N)} {f(E)} {f(S)} {f(Wp)}" fill="{top}"/>')
    return out + "</g>"

def bars(values, labels, x, y, w, h, hot_idx=None):
    mx = max(values) or 1
    n = len(values)
    gap = 6
    bw = (w - gap * (n - 1)) / n
    out = ""
    for i, (v, l) in enumerate(zip(values, labels)):
        bh = 3 + (v / mx) * (h - 22) if v > 0 else 2
        bx = x + i * (bw + gap)
        col = HOT if v == mx and v > 0 else "#7a1a1f"
        out += f'<rect x="{bx:.1f}" y="{y+h-14-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2" fill="{col}"/>'
        out += f'<text x="{bx+bw/2:.1f}" y="{y+h-2}" font-size="10" fill="{DIM}" text-anchor="middle">{escape(l)}</text>'
        if v > 0 and n <= 12:
            out += f'<text x="{bx+bw/2:.1f}" y="{y+h-14-bh-5:.1f}" font-size="10" fill="{FG}" text-anchor="middle">{v}</text>'
    return out

def build_metrics(days, repo_count, langs, mode):
    total = sum(n for _, _, n in days)
    best, cur = streaks(days)
    active = sum(1 for _, _, n in days if n > 0)
    bd = max(days, key=lambda d: d[2])
    bd_date = dt.date.fromisoformat(bd[0]).strftime("%d %b %Y")
    today = dt.date.today().strftime("%d %b %Y")
    W, H = 1000, 640
    out = [svg_open(W, H, f"GitHub metrics for {USER}: contribution map, streaks, activity and languages"),
           f'<defs><linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{RED}" stop-opacity="0"/><stop offset="0.5" stop-color="{RED}"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></linearGradient>'
           f'<radialGradient id="gl" cx="38%" cy="42%" r="50%"><stop offset="0" stop-color="{RED}" stop-opacity="0.09"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient></defs>',
           f'<g font-family="{FONT}">',
           f'<rect x="0.5" y="0.5" width="999" height="{H-1}" rx="10" fill="{BG}" stroke="{LINE}"/><rect x="1" y="1" width="998" height="{H-2}" rx="10" fill="url(#gl)"/>',
           f'<text x="28" y="38" font-size="14" font-weight="800" letter-spacing="3" fill="{HOT}">[ GITHUB METRICS ]</text>',
           f'<text x="250" y="38" font-size="13" fill="{DIM}">@{escape(USER)}</text>',
           f'<text x="972" y="38" font-size="12" fill="{DIM}" text-anchor="end">synced {today}</text>',
           f'<rect x="20" y="54" width="960" height="1" fill="{LINE}"/>',
           f'<rect x="20" y="53" width="120" height="3" fill="url(#sw)"><animate attributeName="x" values="20;860" dur="4s" repeatCount="indefinite"/></rect>',
           f'<text x="28" y="84" font-size="11" letter-spacing="2" fill="{DIM}">CONTRIBUTION MAP · LAST 12 MONTHS</text>']
    out.append(iso_calendar(days, 24, 640, 96, 428))

    tiles = [("CONTRIBUTIONS", str(total), "last 12 months"), ("ACTIVE DAYS", str(active), f"of {len(days)} days"),
             ("LONGEST STREAK", f"{best}d", "consecutive days"), ("CURRENT STREAK", f"{cur}d", "ongoing"),
             ("PUBLIC REPOS", str(repo_count), "owned"), ("BEST DAY", str(bd[2]), bd_date)]
    for i, (lab, val, sub) in enumerate(tiles):
        tx, ty = 676 + (i % 2) * 153, 76 + (i // 2) * 84
        out.append(f'<rect x="{tx}" y="{ty}" width="143" height="72" rx="6" fill="#0a0d12" stroke="{LINE}"/>'
                   f'<rect x="{tx}" y="{ty+12}" width="2" height="48" fill="{RED}"/>'
                   f'<text x="{tx+14}" y="{ty+22}" font-size="9.5" letter-spacing="1.5" fill="{DIM}">{lab}</text>'
                   f'<text x="{tx+14}" y="{ty+49}" font-size="26" font-weight="800" fill="#f5f7fa">{val}</text>'
                   f'<text x="{tx+14}" y="{ty+63}" font-size="10" fill="{HOT}">{escape(sub)}</text>')
    # recent 30 days
    rec = days[-30:]
    out.append(f'<text x="676" y="346" font-size="11" letter-spacing="2" fill="{DIM}">LAST 30 DAYS</text>')
    out.append(bars([n for _, _, n in rec], [""] * 30, 676, 354, 296, 76))

    out.append(f'<rect x="20" y="448" width="960" height="1" fill="{LINE}"/>')
    # weekday
    wk = [0] * 7
    for date, _, n in days: wk[(dt.date.fromisoformat(date).weekday() + 1) % 7] += n
    out.append(f'<text x="28" y="478" font-size="11" letter-spacing="2" fill="{DIM}">BY WEEKDAY</text>')
    out.append(bars(wk, list("SMTWTFS"), 28, 490, 270, 130))
    # month
    months = {}
    for date, _, n in days:
        k = date[:7]; months[k] = months.get(k, 0) + n
    keys = sorted(months)[-12:]
    out.append(f'<text x="330" y="478" font-size="11" letter-spacing="2" fill="{DIM}">BY MONTH</text>')
    out.append(bars([months[k] for k in keys], [dt.date.fromisoformat(k + "-01").strftime("%b") for k in keys], 330, 490, 310, 130))
    # languages
    out.append(f'<text x="676" y="478" font-size="11" letter-spacing="2" fill="{DIM}">LANGUAGES · {mode.upper()}</text>')
    top = langs[:5]
    tot = sum(v for _, v in langs) or 1
    cols = lang_colors(len(top))
    x = 676
    out.append(f'<clipPath id="lb"><rect x="676" y="492" width="296" height="10" rx="5"/></clipPath><g clip-path="url(#lb)"><rect x="676" y="492" width="296" height="10" fill="#10141a"/>')
    for (name, v), c in zip(top, cols):
        wv = 296 * v / tot
        out.append(f'<rect x="{x:.1f}" y="492" width="{wv:.1f}" height="10" fill="{c}"/>'); x += wv
    out.append('</g>')
    for i, ((name, v), c) in enumerate(zip(top, cols)):
        lx, ly = 676 + (i % 2) * 150, 530 + (i // 2) * 28
        out.append(f'<circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{c}"/><text x="{lx+18}" y="{ly}" font-size="12.5" fill="{FG}">{escape(name)}</text>'
                   f'<text x="{lx+18}" y="{ly+13}" font-size="10.5" fill="{DIM}">{100*v/tot:.0f}%</text>')
    out.append('</g></svg>')
    return "\n".join(out)

def main():
    days = get_calendar()
    repo_count, langs, mode = get_repos()
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "neofetch.svg"), "w").write(build_neofetch(days, repo_count))
    open(os.path.join(OUT, "metrics.svg"), "w").write(build_metrics(days, repo_count, langs, mode))
    print(f"ok: {len(days)} days, {sum(n for _,_,n in days)} contributions, {repo_count} repos, langs {langs[:5]} ({mode})")

if __name__ == "__main__":
    main()
