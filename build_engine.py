
import codecs
import os
import re
import subprocess
import threading

try:
    import conpty
except Exception:
    conpty = None

# VT/ANSI escape sequences that ConPTY injects around the real text.
_ANSI_RE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"        # CSI ... final byte
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC ... BEL/ST
    r"|\x1b[@-Z\\-_]"                 # two-byte escapes
)


def _strip_ansi(s):
    return _ANSI_RE.sub("", s).replace("\x00", "").replace("\x07", "")


def _q(s):
    return '"' + str(s).replace('"', '') + '"'


def paths(content_builder):
    cb = os.path.abspath(content_builder)
    return {
        "root": cb,
        "steamcmd": os.path.join(cb, "builder", "steamcmd.exe"),
        "scripts": os.path.join(cb, "scripts"),
        "output": os.path.join(cb, "output"),
        "content": os.path.join(cb, "content"),
    }


def validate(content_builder):
    if not content_builder:
        return False, "err_cb_not_set", {}
    p = paths(content_builder)
    if not os.path.isfile(p["steamcmd"]):
        return False, "err_steamcmd_not_found", {"path": p["steamcmd"]}
    return True, "ok", {}


def depot_file_name(depot_id):
    return f"depot_{depot_id}.vdf"


def app_file_name(app_id):
    return f"app_{app_id}.vdf"


def generate_depot_vdf(depot, scripts_dir):
    depot_id = depot["depotID"]
    content_path = os.path.abspath(depot["contentPath"]) if depot.get("contentPath") else ""
    exclusions = depot.get("exclusions") or []

    lines = [
        '"DepotBuildConfig"',
        "{",
        f'\t"DepotID" {_q(depot_id)}',
        f'\t"contentroot" {_q(content_path)}',
        '\t"FileMapping"',
        "\t{",
        '\t\t"LocalPath" "*"',
        '\t\t"DepotPath" "."',
        '\t\t"recursive" "1"',
        "\t}",
    ]
    for ex in exclusions:
        ex = ex.strip()
        if ex:
            lines.append(f'\t"FileExclusion" {_q(ex)}')
    lines.append("}")
    lines.append("")

    path = os.path.join(scripts_dir, depot_file_name(depot_id))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def generate_app_vdf(profile, content_builder, preview_override=None):
    p = paths(content_builder)
    scripts_dir = p["scripts"]
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(p["output"], exist_ok=True)

    app_id = profile["appID"]
    preview = preview_override if preview_override is not None else profile.get("preview", False)

    depot_lines = []
    for depot in profile.get("depots", []):
        if not depot.get("depotID"):
            continue
        depot_path = generate_depot_vdf(depot, scripts_dir)
        depot_lines.append(f'\t\t{_q(depot["depotID"])}\t{_q(depot_path)}')

    lines = [
        '"appbuild"',
        "{",
        f'\t"appid" {_q(app_id)}',
        f'\t"desc" {_q(profile.get("description", ""))}',
        f'\t"buildoutput" {_q(p["output"])}',
        '\t"contentroot" ""',
        f'\t"setlive" {_q(profile.get("branch", ""))}',
        f'\t"preview" {_q("1" if preview else "0")}',
        '\t"local" ""',
        '\t"depots"',
        "\t{",
        *depot_lines,
        "\t}",
        "}",
        "",
    ]

    app_path = os.path.join(scripts_dir, app_file_name(app_id))
    with open(app_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return app_path



_GUARD_PROMPTS = (
    "steam guard code",
    "two-factor code",
    "enter the current code",
)
_SUCCESS_MARKERS = ("Successfully finished appid", "App build successful")
_FAILURE_MARKERS = ("FAILED", "ERROR!", "Login Failure", "Invalid Password")


class BuildRunner:

    def __init__(self, on_output, on_guard_needed, on_done):
        self.on_output = on_output
        self.on_guard_needed = on_guard_needed
        self.on_done = on_done
        self.proc = None
        self._guard_sent = False
        self._result = None

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, content_builder, username, password, app_vdf_path):
        p = paths(content_builder)
        args = [p["steamcmd"], "+login", username]
        if password:
            args.append(password)
        args += ["+run_app_build", app_vdf_path, "+quit"]

        shown = list(args)
        if password and len(shown) > 3:
            shown[3] = "********"
        self.on_output("cmd", "> " + " ".join(shown) + "\n")

        self.proc = None
        if conpty is not None and conpty.available():
            # A pseudo-console makes steamcmd flush its output line by line
            # instead of block-buffering it until the process exits.
            try:
                self.proc = conpty.spawn(args, cwd=p["root"])
            except Exception:
                self.proc = None
        if self.proc is None:
            self.proc = subprocess.Popen(
                args,
                cwd=p["root"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        threading.Thread(target=self._pump, daemon=True).start()

    def submit_guard_code(self, code):
        if self.proc and self.proc.stdin:
            try:
                # Under a pseudo-console steamcmd reads its input like a real
                # terminal: the Enter key is a carriage return (\r), not a line
                # feed (\n). Sending only \n leaves it waiting forever with the
                # digits typed but never submitted. \r\n satisfies both the
                # ConPTY path and the plain-pipe fallback.
                self.proc.stdin.write((code + "\r\n").encode("utf-8"))
                self.proc.stdin.flush()
                self._guard_sent = True
                self.on_output("info", "[Steam Guard code submitted]\n")
            except (OSError, ValueError):
                pass

    def cancel(self):
        if self.is_running():
            try:
                self.proc.terminate()
            except OSError:
                pass

    def _pump(self):
        line = ""
        stream = self.proc.stdout
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while True:
            chunk = stream.read(4096)
            if not chunk:
                break
            text = decoder.decode(chunk)
            for ch in text:
                if ch in ("\n", "\r"):
                    if line:
                        self._emit_line(line)
                        line = ""
                    continue
                line += ch
                if not self._guard_sent:
                    low = _strip_ansi(line).lower()
                    if any(g in low for g in _GUARD_PROMPTS):
                        self.on_output("prompt", _strip_ansi(line) + "\n")
                        self.on_guard_needed(_strip_ansi(line))
                        line = ""

        if line:
            self._emit_line(line)

        code = self.proc.wait()
        success = self._result == "success" or (code == 0 and self._result != "fail")
        self.on_done(success, code)

    def _emit_line(self, line):
        line = _strip_ansi(line).rstrip()
        if not line:
            return
        kind = "out"
        if any(m in line for m in _SUCCESS_MARKERS):
            kind = "success"
            self._result = "success"
        elif any(m in line for m in _FAILURE_MARKERS):
            kind = "error"
            self._result = "fail"
        self.on_output(kind, line + "\n")
