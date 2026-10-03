#!/usr/bin/env python3
"""Render the public team roster into the org profile README.

Replaces only the text between <!-- TEAMS:START --> and <!-- TEAMS:END -->
in profile/README.md. Standard library only.

Usage:
    GH_TOKEN=... python3 .github/scripts/render_teams.py [--dry-run] [--show-private-count]

See docs/team-roster.md for setup.
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")
START = "<!-- TEAMS:START -->"
END = "<!-- TEAMS:END -->"
AVATAR_SIZE = 20


def fail(message):
    sys.exit(f"error: {message}")


def api_get_all(path, token):
    """GET every page of a list endpoint and return the combined items."""
    url = f"{API_URL}{path}?per_page=100"
    items = []
    while url:
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "xubuntu-team-roster",
        })
        try:
            with urllib.request.urlopen(request) as response:
                items.extend(json.load(response))
                match = re.search(r'<([^>]+)>;\s*rel="next"', response.headers.get("Link", ""))
                url = match.group(1) if match else None
        except urllib.error.HTTPError as err:
            try:
                detail = json.load(err).get("message", "")
            except (ValueError, AttributeError):
                detail = ""
            hint = ""
            if err.code == 401:
                hint = " The token is missing, invalid or expired."
            elif err.code in (403, 404):
                hint = (" The GitHub App probably lacks the Organization > Members: read"
                        " permission, or is not installed on the org.")
            fail(f"GET {path} returned HTTP {err.code} {detail!r}.{hint}")
    return items


def fetch(org, token):
    """Return (teams, members_by_slug, public_logins)."""
    teams = [t for t in api_get_all(f"/orgs/{org}/teams", token) if t["privacy"] == "closed"]
    members = {t["slug"]: api_get_all(f"/orgs/{org}/teams/{t['slug']}/members", token) for t in teams}
    public = {m["login"] for m in api_get_all(f"/orgs/{org}/public_members", token)}
    return teams, members, public


def render_member(member):
    login = member["login"]
    profile = f"https://github.com/{login}"
    avatar_url = member["avatar_url"]
    avatar = f"{avatar_url}{'&' if '?' in avatar_url else '?'}s={AVATAR_SIZE * 2}"
    return (f'<a href="{profile}"><img src="{avatar}" width="{AVATAR_SIZE}" '
            f'height="{AVATAR_SIZE}" alt=""></a> [@{login}]({profile})')


def render_team(team, members, public, show_private_count, depth):
    level = "#" * min(3 + depth, 6)
    lines = [f"{level} {html.escape(team['name'])}", ""]
    description = (team.get("description") or "").strip()
    if description:
        lines += [html.escape(" ".join(description.split())), ""]

    visible = sorted((m for m in members if m["login"] in public), key=lambda m: m["login"].lower())
    hidden = len(members) - len(visible)
    entries = [render_member(m) for m in visible]
    if show_private_count and hidden:
        entries.append(f"+{hidden} private member{'s' if hidden != 1 else ''}")
    lines += [" &nbsp; ".join(entries) if entries else "_No public members._", ""]
    return lines


def render(teams, members, public, show_private_count=False):
    """Render the roster as Markdown, nesting child teams under their parent."""
    slugs = {t["slug"] for t in teams}
    children = {}
    for team in teams:
        parent = (team.get("parent") or {}).get("slug")
        # A child of a skipped (secret) team is shown at the top level.
        children.setdefault(parent if parent in slugs else None, []).append(team)

    lines = []

    def walk(parent, depth):
        for team in sorted(children.get(parent, []), key=lambda t: t["name"].lower()):
            lines.extend(render_team(team, members[team["slug"]], public, show_private_count, depth))
            walk(team["slug"], depth + 1)

    walk(None, 0)
    if not lines:
        lines = ["_No public teams._", ""]
    return "\n".join(lines).rstrip() + "\n"


def splice(readme, section):
    """Return readme with the marked section replaced (or appended if absent)."""
    block = f"{START}\n{section}{END}"
    if START not in readme and END not in readme:
        if not readme:
            return f"{block}\n"
        separator = "\n" if readme.endswith("\n") else "\n\n"
        return f"{readme}{separator}{block}\n"
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(START) > readme.index(END):
        fail(f"expected exactly one {START} followed by one {END} in the README")
    before, rest = readme.split(START)
    _, after = rest.split(END)
    return f"{before}{block}{after}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--org", default="Xubuntu")
    parser.add_argument("--readme", default="profile/README.md")
    parser.add_argument("--dry-run", action="store_true", help="print the section instead of writing it")
    parser.add_argument("--show-private-count", action="store_true",
                        help='append "+N private members" for members with hidden org membership')
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        fail("set GH_TOKEN to a token that can read org team membership")

    section = render(*fetch(args.org, token), show_private_count=args.show_private_count)
    if args.dry_run:
        print(section, end="")
        return

    try:
        with open(args.readme, encoding="utf-8") as f:
            readme = f.read()
    except FileNotFoundError:
        readme = ""
    updated = splice(readme, section)
    if updated != readme:
        os.makedirs(os.path.dirname(args.readme) or ".", exist_ok=True)
        with open(args.readme, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"Updated {args.readme}")
    else:
        print(f"{args.readme} is already up to date")


if __name__ == "__main__":
    main()
