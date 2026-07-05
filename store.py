
import json
import os
import sys
import uuid

import keyring

KEYRING_SERVICE = "GENIUS Steamworks Builder"


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(app_dir(), "genius_config.json")


DEFAULT_CONFIG = {
    "contentBuilderPath": "",
    "steamUsername": "",
    "profiles": [],
}


def _auto_detect_content_builder():
    here = app_dir()
    candidates = []
    cur = here
    for _ in range(5):
        candidates.append(os.path.join(cur, "tools", "ContentBuilder"))
        cur = os.path.dirname(cur)
    for c in candidates:
        if os.path.isfile(os.path.join(c, "builder", "steamcmd.exe")):
            return os.path.abspath(c)
    return ""


def load_config():
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            cfg = dict(DEFAULT_CONFIG)
    else:
        cfg = dict(DEFAULT_CONFIG)

    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)

    if not cfg.get("contentBuilderPath"):
        cfg["contentBuilderPath"] = _auto_detect_content_builder()

    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return True



def set_password(username, password):
    if not username:
        return False
    if password:
        keyring.set_password(KEYRING_SERVICE, username, password)
    return True


def get_password(username):
    if not username:
        return ""
    try:
        return keyring.get_password(KEYRING_SERVICE, username) or ""
    except keyring.errors.KeyringError:
        return ""


def delete_password(username):
    try:
        keyring.delete_password(KEYRING_SERVICE, username)
    except keyring.errors.KeyringError:
        pass
    return True


def has_password(username):
    return bool(get_password(username))



def new_profile_id():
    return uuid.uuid4().hex
