
import os
import re
import glob

import store


_TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|(\{)|(\})')


def _strip_comments(text):
    out = []
    for line in text.splitlines():
        in_q = False
        cut = None
        for i, ch in enumerate(line):
            if ch == '"':
                in_q = not in_q
            elif ch == "/" and not in_q and i + 1 < len(line) and line[i + 1] == "/":
                cut = i
                break
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def parse_vdf(text):
    text = _strip_comments(text)
    tokens = []
    for m in _TOKEN.finditer(text):
        if m.group(1) is not None:
            tokens.append(("str", m.group(1)))
        elif m.group(2):
            tokens.append(("open", "{"))
        else:
            tokens.append(("close", "}"))

    pos = 0

    def parse_block():
        nonlocal pos
        d = {}
        while pos < len(tokens):
            kind, val = tokens[pos]
            if kind == "close":
                pos += 1
                break
            if kind == "str":
                key = val
                pos += 1
                if pos < len(tokens) and tokens[pos][0] == "open":
                    pos += 1
                    d[key.lower()] = parse_block()
                elif pos < len(tokens) and tokens[pos][0] == "str":
                    v = tokens[pos][1]
                    pos += 1
                    if key.lower() in d:
                        if isinstance(d[key.lower()], list):
                            d[key.lower()].append(v)
                        else:
                            d[key.lower()] = [d[key.lower()], v]
                    else:
                        d[key.lower()] = v
                else:
                    pos += 1
            else:
                pos += 1
        return d

    if tokens and tokens[0][0] == "str":
        root_key = tokens[0][1]
        pos = 1
        if pos < len(tokens) and tokens[pos][0] == "open":
            pos += 1
            return {root_key.lower(): parse_block()}
    return {}


def import_profiles(content_builder):
    from build_engine import paths

    scripts = paths(content_builder)["scripts"]
    profiles = []
    for app_path in sorted(glob.glob(os.path.join(scripts, "app_*.vdf"))):
        try:
            with open(app_path, "r", encoding="utf-8", errors="replace") as f:
                data = parse_vdf(f.read())
        except OSError:
            continue
        app = data.get("appbuild") or data.get("AppBuild".lower()) or {}
        app_id = app.get("appid")
        if not app_id:
            continue

        depots_block = app.get("depots", {})
        depots = []
        if isinstance(depots_block, dict):
            for depot_id, ref in depots_block.items():
                depot = _read_depot(depot_id, ref, scripts, content_builder)
                depots.append(depot)

        profiles.append({
            "id": store.new_profile_id(),
            "name": app.get("desc") or f"App {app_id}",
            "appID": str(app_id),
            "description": app.get("desc", ""),
            "branch": app.get("setlive", "") if isinstance(app.get("setlive", ""), str) else "",
            "preview": str(app.get("preview", "0")) == "1",
            "depots": depots,
        })
    return profiles


def _read_depot(depot_id, ref, scripts, content_builder):
    depot = {"depotID": str(depot_id), "contentPath": "", "exclusions": []}
    depot_path = ref
    if not os.path.isabs(depot_path):
        depot_path = os.path.join(scripts, os.path.basename(ref))
    if not os.path.isfile(depot_path):
        depot_path = os.path.join(scripts, f"depot_{depot_id}.vdf")
    if os.path.isfile(depot_path):
        try:
            with open(depot_path, "r", encoding="utf-8", errors="replace") as f:
                d = parse_vdf(f.read())
            cfg = d.get("depotbuildconfig") or d.get("depotbuild") or {}
            depot["contentPath"] = cfg.get("contentroot", "") or ""
            ex = cfg.get("fileexclusion")
            if isinstance(ex, list):
                depot["exclusions"] = ex
            elif isinstance(ex, str):
                depot["exclusions"] = [ex]
        except OSError:
            pass
    return depot
