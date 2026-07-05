
import ctypes
from ctypes import wintypes
import json
import threading
import os
import sys
import webbrowser

import webview

WINDOW_TITLE = "GENIUSY'S Steamworks Builder"

import store
import build_engine
import vdf_import


def resource_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


class Api:
    def __init__(self):
        self._window = None
        self.config = store.load_config()
        self._runner = None
        self._maximized = False

    def win_minimize(self):
        if self._window:
            self._window.minimize()
        return True

    def win_toggle_maximize(self):
        if not self._window:
            return False
        if self._maximized:
            self._window.restore()
        else:
            self._window.maximize()
        self._maximized = not self._maximized
        return self._maximized

    def win_close(self):
        if self._window:
            self._window.destroy()
        return True

    def start_resize(self, edge):
        if edge not in _EDGES:
            return False
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
            if not hwnd:
                return False
            threading.Thread(
                target=_resize_loop, args=(hwnd, edge), daemon=True
            ).start()
        except Exception:
            return False
        return True

    def _js(self, fn, *args):
        if not self._window:
            return
        payload = ", ".join(json.dumps(a, ensure_ascii=False) for a in args)
        try:
            self._window.evaluate_js(f"window.{fn}({payload})")
        except Exception:
            pass

    def get_state(self):
        cb = self.config.get("contentBuilderPath", "")
        ok, msg_key, msg_params = build_engine.validate(cb)
        return {
            "config": {
                "contentBuilderPath": cb,
                "steamUsername": self.config.get("steamUsername", ""),
                "hasPassword": store.has_password(self.config.get("steamUsername", "")),
            },
            "profiles": self.config.get("profiles", []),
            "contentBuilderOk": ok,
            "contentBuilderMsgKey": msg_key,
            "contentBuilderMsgParams": msg_params,
        }

    def save_settings(self, content_builder_path, username, password):
        self.config["contentBuilderPath"] = content_builder_path.strip()
        old_user = self.config.get("steamUsername", "")
        new_user = username.strip()
        self.config["steamUsername"] = new_user
        if password:
            store.set_password(new_user, password)
        elif old_user and old_user != new_user:
            pw = store.get_password(old_user)
            if pw:
                store.set_password(new_user, pw)
        store.save_config(self.config)
        return self.get_state()

    def clear_password(self):
        store.delete_password(self.config.get("steamUsername", ""))
        return self.get_state()

    def save_profiles(self, profiles):
        self.config["profiles"] = profiles
        store.save_config(self.config)
        return True

    def import_existing(self):
        cb = self.config.get("contentBuilderPath", "")
        ok, msg_key, msg_params = build_engine.validate(cb)
        if not ok:
            return {"ok": False, "msgKey": msg_key, "params": msg_params, "imported": []}
        imported = vdf_import.import_profiles(cb)
        existing_ids = {p.get("appID") for p in self.config.get("profiles", [])}
        added = [p for p in imported if p.get("appID") not in existing_ids]
        self.config.setdefault("profiles", []).extend(added)
        store.save_config(self.config)
        return {"ok": True, "msgKey": "import_done", "params": {"n": len(added)}, "count": len(added)}

    def pick_folder(self, start=""):
        result = self._window.create_file_dialog(
            webview.FileDialog.FOLDER,
            directory=start or os.path.expanduser("~"),
        )
        if result:
            return result[0]
        return ""

    def detect_exe(self, path):
        try:
            if not path or not os.path.isdir(path):
                return ""
            for name in sorted(os.listdir(path)):
                if name.lower().endswith(".exe") and os.path.isfile(os.path.join(path, name)):
                    return name
        except Exception:
            pass
        return ""

    def open_path(self, path):
        if path and os.path.exists(path):
            os.startfile(path)
            return True
        return False

    def open_partner_page(self, app_id):
        if app_id:
            webbrowser.open(f"https://partner.steamgames.com/apps/builds/{app_id}")
        return True

    def start_build(self, profile, preview):
        if self._runner and self._runner.is_running():
            return {"ok": False, "msgKey": "err_build_running", "params": {}}

        cb = self.config.get("contentBuilderPath", "")
        ok, msg_key, msg_params = build_engine.validate(cb)
        if not ok:
            return {"ok": False, "msgKey": msg_key, "params": msg_params}

        username = self.config.get("steamUsername", "")
        if not username:
            return {"ok": False, "msgKey": "err_no_username", "params": {}}
        password = store.get_password(username)

        if not profile.get("appID"):
            return {"ok": False, "msgKey": "err_no_appid", "params": {}}
        if not any(d.get("depotID") and d.get("contentPath") for d in profile.get("depots", [])):
            return {"ok": False, "msgKey": "err_no_depot", "params": {}}

        try:
            app_vdf = build_engine.generate_app_vdf(profile, cb, preview_override=bool(preview))
        except Exception as e:
            return {"ok": False, "msgKey": "err_vdf_failed", "params": {"err": str(e)}}

        self._runner = build_engine.BuildRunner(
            on_output=lambda kind, text: self._js("onBuildOutput", kind, text),
            on_guard_needed=lambda line: self._js("onGuardNeeded", line),
            on_done=lambda success, code: self._js("onBuildDone", success, code),
        )
        self._runner.start(cb, username, password, app_vdf)
        return {"ok": True, "vdf": app_vdf}

    def submit_guard_code(self, code):
        if self._runner:
            self._runner.submit_guard_code(code)
        return True

    def cancel_build(self):
        if self._runner:
            self._runner.cancel()
        return True


def _apply_win11_rounding(hwnd):
    try:
        dwm = ctypes.windll.dwmapi
        pref = ctypes.c_int(2)
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
        color = ctypes.c_uint(0x003C312A)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(color), ctypes.sizeof(color))
    except Exception:
        pass


_MIN_W, _MIN_H = 940, 620
_VK_LBUTTON = 0x01

_EDGES = {
    "left":        (True, False, False, False),
    "right":       (False, True, False, False),
    "top":         (False, False, True, False),
    "bottom":      (False, False, False, True),
    "topleft":     (True, False, True, False),
    "topright":    (False, True, True, False),
    "bottomleft":  (True, False, False, True),
    "bottomright": (False, True, False, True),
}


def _dpi_scale(hwnd):
    try:
        return ctypes.windll.user32.GetDpiForWindow(hwnd) / 96.0
    except Exception:
        return 1.0


def _resize_loop(hwnd, edge):
    import time
    user32 = ctypes.windll.user32
    left, right, top, bottom = _EDGES[edge]
    scale = _dpi_scale(hwnd)
    min_w = int(_MIN_W * scale)
    min_h = int(_MIN_H * scale)

    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    sx, sy = pt.x, pt.y
    L0, T0, R0, B0 = rect.left, rect.top, rect.right, rect.bottom

    while user32.GetAsyncKeyState(_VK_LBUTTON) & 0x8000:
        user32.GetCursorPos(ctypes.byref(pt))
        dx, dy = pt.x - sx, pt.y - sy
        L, T, R, B = L0, T0, R0, B0
        if left:
            L = L0 + dx
        if right:
            R = R0 + dx
        if top:
            T = T0 + dy
        if bottom:
            B = B0 + dy
        if R - L < min_w:
            if left:
                L = R - min_w
            else:
                R = L + min_w
        if B - T < min_h:
            if top:
                T = B - min_h
            else:
                B = T + min_h
        user32.MoveWindow(hwnd, L, T, R - L, B - T, True)
        time.sleep(0.008)


def _on_window_shown():
    hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
    if not hwnd:
        return
    _apply_win11_rounding(hwnd)


def main():
    api = Api()
    index = os.path.join(resource_dir(), "ui", "index.html")
    window = webview.create_window(
        WINDOW_TITLE,
        index,
        js_api=api,
        width=1180,
        height=780,
        min_size=(940, 620),
        background_color="#0d1117",
        frameless=True,
        easy_drag=False,
    )
    api._window = window
    webview.start(_on_window_shown)


if __name__ == "__main__":
    main()
