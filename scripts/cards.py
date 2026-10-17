#!/usr/bin/env python3
"""Generate the SVG cards of the profile README (header, stats and languages).

Stdlib only. Reads public data from the GitHub GraphQL API with GITHUB_TOKEN and
writes a dark and a light variant of every card into assets/.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from html import escape
from pathlib import Path

USER = "achedon12"
OUT = Path(__file__).resolve().parent.parent / "assets"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

THEMES = {
    "dark": {
        "bg": "#0f1115", "panel": "#15181e", "border": "#262b34", "grid": "#1d2128",
        "text": "#e6e8eb", "muted": "#8b929e", "faint": "#5b626e",
        "amber": "#f5a524", "cyan": "#5ccfe6", "green": "#3ddc84", "rose": "#f2777a",
    },
    "light": {
        "bg": "#f6f7f9", "panel": "#ffffff", "border": "#dde1e7", "grid": "#eef0f3",
        "text": "#1b1f24", "muted": "#59606b", "faint": "#8d949e",
        "amber": "#b86e00", "cyan": "#0b7f96", "green": "#16884a", "rose": "#c43d43",
    },
}

# Lucide icons (24x24, stroke based).
ICONS = {
    "star": '<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/>',
    "commit": '<circle cx="12" cy="12" r="3"/><line x1="3" x2="9" y1="12" y2="12"/><line x1="15" x2="21" y1="12" y2="12"/>',
    "pr": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" x2="6" y1="9" y2="21"/>',
    "issue": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="1"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "activity": '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
    "tag": '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    "package": '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><path d="m3.3 7 7.703 4.734a2 2 0 0 0 1.994 0L20.7 7"/>',
}

EXCLUDED_LANGS = {"Dockerfile", "Makefile", "Procfile", "Batchfile", "PowerShell"}


# --------------------------------------------------------------------------- data

def graphql(query: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is required")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": USER},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.load(res)
    if body.get("errors"):
        sys.exit(json.dumps(body["errors"], indent=2))
    return body["data"]


def fetch() -> dict:
    repos = """
      repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
        totalCount
        nodes {
          stargazerCount
          languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
            edges { size node { name color } }
          }
        }
      }"""
    data = graphql(f"""{{
      user(login: "{USER}") {{
        followers {{ totalCount }}
        pullRequests {{ totalCount }}
        issues {{ totalCount }}
        contributionsCollection {{ contributionYears contributionCalendar {{ totalContributions }} }}
        {repos}
      }}
    }}""")
    user = data["user"]
    years = user["contributionsCollection"]["contributionYears"]
    per_year = graphql("{ user(login: \"%s\") { %s } }" % (USER, " ".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z")'
        " { totalCommitContributions contributionCalendar { totalContributions } }"
        for y in years
    )))["user"]

    langs: dict[str, list] = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in EXCLUDED_LANGS:
                continue
            entry = langs.setdefault(name, [0, edge["node"]["color"] or "#8b929e"])
            entry[0] += edge["size"]

    return {
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        "repos": user["repositories"]["totalCount"],
        "followers": user["followers"]["totalCount"],
        "prs": user["pullRequests"]["totalCount"],
        "issues": user["issues"]["totalCount"],
        "commits": sum(v["totalCommitContributions"] for v in per_year.values()),
        "contrib_year": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "contrib_total": sum(v["contributionCalendar"]["totalContributions"] for v in per_year.values()),
        "since": min(years),
        "langs": sorted(langs.items(), key=lambda kv: -kv[1][0]),
    }


# --------------------------------------------------------------------------- svg helpers

def icon(name: str, x: float, y: float, size: float, color: str, width: float = 2) -> str:
    s = size / 24
    return (
        f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" color="{color}" '
        f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>'
    )



def fmt(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 10000 else f"{n:,}".replace(",", " ")


def frame(w: int, h: int, t: dict, body: str, label: str, style: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(label)}">'
        f"<title>{escape(label)}</title>"
        f"<style>text{{font-family:{SANS}}}.m{{font-family:{MONO}}}{style}</style>"
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{t["panel"]}" stroke="{t["border"]}"/>'
        f"{body}</svg>"
    )



# --------------------------------------------------------------------------- cards

def led(cx: float, cy: float, color: str, r: float = 3.5, pulse: bool = False) -> str:
    cls = ' class="pulse"' if pulse else ""
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r * 2.6}" fill="{color}" opacity="0.18"{cls}/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
    )



def header(t: dict) -> str:
    w, h = 1200, 320
    cx, cy = 960, 160
    planets = [
        (68, 0, "Symfony", "amber", 38),
        (106, 200, "Next.js", "cyan", 60),
        (106, 20, "React", "cyan", 60),
        (144, 120, "Docker", "green", 90),
        (144, 300, "MySQL", "amber", 90),
        (144, 210, "TypeScript", "cyan", 90),
    ]
    orbits = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["border"]}" stroke-dasharray="2 6"/>'
        for r in (68, 106, 144)
    )
    sats = []
    for r, start, name, color, period in planets:
        px, py = cx + r, cy
        tw = len(name) * 7.4 + 22
        sats.append(
            f'<g class="spin" style="animation-duration:{period}s;animation-delay:-{period * start / 360:.1f}s">'
            f'<g class="spin rev" style="transform-origin:{px}px {py}px;animation-duration:{period}s;'
            f'animation-delay:-{period * start / 360:.1f}s">'
            f"{led(px, py, t[color], 3.2)}"
            f'<rect x="{px + 9}" y="{py - 11}" width="{tw}" height="22" rx="11" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'<text class="m" x="{px + 9 + tw / 2}" y="{py + 4}" text-anchor="middle" font-size="12" fill="{t["text"]}">{name}</text>'
            "</g></g>"
        )
    body = f"""
<defs>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{t["grid"]}"/></pattern>
  <radialGradient id="core"><stop offset="0" stop-color="{t["amber"]}" stop-opacity=".55"/><stop offset="1" stop-color="{t["amber"]}" stop-opacity="0"/></radialGradient>
  <clipPath id="clip"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="12"/></clipPath>
</defs>
<g clip-path="url(#clip)">
  <rect width="{w}" height="{h}" fill="url(#dots)"/>
  {orbits}
  <circle cx="{cx}" cy="{cy}" r="44" fill="url(#core)"/>
  <circle cx="{cx}" cy="{cy}" r="24" fill="{t["bg"]}" stroke="{t["amber"]}" stroke-opacity=".7"/>
  <text class="m" x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="14" font-weight="700" fill="{t["amber"]}">LD</text>
  {"".join(sats)}
</g>
<text class="m" x="64" y="62" font-size="13" letter-spacing="2" fill="{t["faint"]}">STATION LD-001  ·  BESANÇON  ·  47.2378° N, 6.0241° E</text>
<text x="62" y="140" font-size="64" font-weight="700" letter-spacing="-1.5" fill="{t["text"]}">Léo Deroin</text>
<text x="64" y="182" font-size="22" fill="{t["muted"]}">Développeur fullstack <tspan fill="{t["faint"]}">—</tspan> Symfony, React, Next.js</text>
<rect x="64" y="216" width="318" height="38" rx="19" fill="{t["bg"]}" stroke="{t["border"]}"/>
{led(86, 235, t["green"], 4, pulse=True)}
<text class="m" x="102" y="240" font-size="14" fill="{t["text"]}">Disponible pour un CDI</text>
<text class="m" x="400" y="240" font-size="14" fill="{t["amber"]}">leoderoin.fr</text>
"""
    style = (
        f".spin{{transform-origin:{cx}px {cy}px;animation:spin linear infinite}}"
        ".rev{animation-direction:reverse}"
        "@keyframes spin{to{transform:rotate(360deg)}}"
        ".pulse{animation:pulse 2.4s ease-in-out infinite}"
        "@keyframes pulse{50%{opacity:.04}}"
        "@media (prefers-reduced-motion:reduce){.spin,.pulse{animation:none}}"
    )
    return frame(w, h, t, body, "Léo Deroin, développeur fullstack à Besançon", style)



def stats(t: dict, d: dict) -> str:
    w, h = 495, 230
    tiles = [
        ("star", "Étoiles", d["stars"], "amber"),
        ("commit", "Commits", d["commits"], "cyan"),
        ("pr", "Pull requests", d["prs"], "green"),
        ("activity", f"Contributions {d['contrib_year']} / an", d["contrib_total"], "amber"),
        ("folder", "Dépôts publics", d["repos"], "cyan"),
        ("users", "Followers", d["followers"], "green"),
    ]
    body = [
        f'<text class="m" x="24" y="38" font-size="12" letter-spacing="1.6" fill="{t["faint"]}">ACTIVITÉ GITHUB</text>',
        f'<text class="m" x="{w - 24}" y="38" font-size="12" text-anchor="end" fill="{t["faint"]}">depuis {d["since"]}</text>',
    ]
    tw, th = 141, 76
    for i, (ic, label, value, color) in enumerate(tiles):
        x = 24 + (i % 3) * (tw + 10)
        y = 56 + (i // 3) * (th + 10)
        label = label if ic != "activity" else "Contributions"
        body.append(
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="8" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'{icon(ic, x + 14, y + 14, 14, t[color])}'
            f'<text x="{x + 36}" y="{y + 26}" font-size="12" fill="{t["muted"]}">{label}</text>'
            f'<text x="{x + 14}" y="{y + 60}" font-size="26" font-weight="700" fill="{t["text"]}">{fmt(value)}</text>'
        )
    return frame(w, h, t, "".join(body), "Statistiques GitHub de achedon12")


def languages(t: dict, d: dict) -> str:
    w, h = 495, 230
    top = d["langs"][:8]
    total = sum(v[0] for _, v in top) or 1
    body = [f'<text class="m" x="24" y="38" font-size="12" letter-spacing="1.6" fill="{t["faint"]}">LANGAGES LES PLUS UTILISÉS</text>']
    x, bw = 24, w - 48
    body.append(f'<clipPath id="bar"><rect x="24" y="56" width="{bw}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
    for name, (size, color) in top:
        seg = bw * size / total
        body.append(f'<rect x="{x:.2f}" y="56" width="{seg + 0.5:.2f}" height="10" fill="{color}"/>')
        x += seg
    body.append("</g>")
    for i, (name, (size, color)) in enumerate(top):
        cx = 24 + (i % 2) * 230
        cy = 98 + (i // 2) * 34
        body.append(
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{color}"/>'
            f'<text x="{cx + 18}" y="{cy}" font-size="14" fill="{t["text"]}">{escape(name)}</text>'
            f'<text class="m" x="{cx + 210}" y="{cy}" font-size="13" text-anchor="end" fill="{t["muted"]}">{100 * size / total:.1f} %</text>'
        )
    return frame(w, h, t, "".join(body), "Langages les plus utilisés par achedon12")



def main() -> None:
    OUT.mkdir(exist_ok=True)
    data = fetch()
    for mode, t in THEMES.items():
        (OUT / f"header-{mode}.svg").write_text(header(t))
        (OUT / f"stats-{mode}.svg").write_text(stats(t, data))
        (OUT / f"languages-{mode}.svg").write_text(languages(t, data))
    print(f"cards written to {OUT}")


if __name__ == "__main__":
    main()
