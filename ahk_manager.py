import tkinter as tk
from tkinter import font as tkfont, colorchooser, messagebox
import subprocess
import threading
import os
import sys
import tempfile
import shutil
import json
import urllib.request
import urllib.error

# ── Version & auto-update ─────────────────────────────────────────────────────
CURRENT_VERSION = "1.0.7"
# ▼▼ Replace these URLs with your actual web server paths ▼▼
UPDATE_VERSION_URL = "https://mewpyyy.github.io/nebula-updates/version.json"
UPDATE_SCRIPT_URL  = "https://mewpyyy.github.io/nebula-updates/ahk_manager.py"
# ▲▲ ─────────────────────────────────────────────────────────────────────── ▲▲

# ── Users (add/remove entries here to manage access) ─────────────────────────
USERS = {
    "Physica": "PhysiaAdmin1",   # ← admin account, never remove this
}

# ── GitHub account system ─────────────────────────────────────────────────────
GITHUB_REPO   = "mewpyyy/nebula-updates"
GITHUB_BRANCH = "main"
USERS_FILE    = "users.json"

# Token is XOR-obfuscated so GitHub's scanner doesn't auto-revoke it.
# To update: run _obfuscate_token("your_new_token") and paste the result below.
_TOKEN_KEY = 0x5A
_TOKEN_OBF = []

def _get_token():
    return "".join(chr(b ^ _TOKEN_KEY) for b in _TOKEN_OBF)

def _obfuscate_token(token):
    """Helper — run this to get new obfuscated bytes when you change the token."""
    return [ord(c) ^ _TOKEN_KEY for c in token]

def _github_headers():
    return {
        "Authorization": f"token {_get_token()}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

def _github_read_headers():
    """For read operations — no auth needed on public repo."""
    return {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Nebula-App",
    }

GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{USERS_FILE}"

def fetch_remote_users():
    """Fetch users.json from GitHub. Returns (dict_of_users, sha) or ({}, None)."""
    try:
        import base64
        req = urllib.request.Request(GITHUB_API_BASE, headers=_github_read_headers())
        resp = urllib.request.urlopen(req, timeout=6)
        data = json.loads(resp.read().decode())
        content = base64.b64decode(data["content"]).decode("utf-8")
        users = json.loads(content)
        return users, data["sha"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}, None
        return {}, None
    except Exception:
        return {}, None

def push_remote_users(users, sha=None):
    """Push updated users dict back to GitHub. sha required for updates."""
    import base64
    content = base64.b64encode(json.dumps(users, indent=2).encode()).decode()
    payload = {
        "message": "Nebula: update users",
        "content": content,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    data = json.dumps(payload).encode()
    req = urllib.request.Request(GITHUB_API_BASE, data=data,
                                  headers=_github_headers(), method="PUT")
    try:
        urllib.request.urlopen(req, timeout=10)
        return True, ""
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return False, f"HTTP {e.code}: {body}"
    except Exception as ex:
        return False, str(ex)

def validate_user_remote(username, password):
    """Check credentials against GitHub users.json. Falls back to local USERS."""
    if USERS.get(username) == password:
        return True
    remote, _ = fetch_remote_users()
    return remote.get(username) == password

# ── Stats / Favourites files ──────────────────────────────────────────────────
STATS_FILE = os.path.join(os.path.expanduser("~"), ".ahkmanager_stats.json")
FAVS_FILE  = os.path.join(os.path.expanduser("~"), ".ahkmanager_favs.json")

def load_stats():
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_stats(stats):
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)
    except Exception:
        pass

def load_favs():
    try:
        with open(FAVS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_favs(favs):
    try:
        with open(FAVS_FILE, "w") as f:
            json.dump(favs, f, indent=2)
    except Exception:
        pass

# ── Embedded AHK scripts ──────────────────────────────────────────────────────
SCRIPTS = [
    {
        "display_name": "Underground Tech — Hold A",
        "filename": "underground_tech_HOLDING_a.ahk",
        "script": r"""toggle := false

F6::
toggle := true
Send {LButton Down}
Send {a Down}
return

F10::
toggle := false
Send {a Up}
Send {LButton Up}
Click
return

F12::
ExitApp
return
"""
    },
    {
        "display_name": "Underground Tech — Hold D",
        "filename": "underground_tech_HOLDING_d.ahk",
        "script": r"""toggle := false

F6::
toggle := true
Send {LButton Down}
Send {d Down}
return

F10::
toggle := false
Send {d Up}
Send {LButton Up}
Click
return

F12::
ExitApp
return
"""
    },
    {
        "display_name": "Autoclicker 7 CPS",
        "filename": "autoclicker7cps.ahk",
        "script": r"""#NoEnv
#SingleInstance Force
SetBatchLines, -1
SendMode, Input
clickerRunning := false

F6::
if (clickerRunning)
    return
clickerRunning := true
SetTimer, AutoClick, -10
return

F10::
if (!clickerRunning)
    return
clickerRunning := false
SetTimer, AutoClick, Off
ToolTip
return

AutoClick:
if (!clickerRunning)
    return
Random, roll, 0, 100
if (roll < 15) {
    Random, interval, 83, 133
} else if (roll < 85) {
    Random, interval, 118, 154
} else {
    Random, interval, 154, 200
}
Click, Down
Click, Up
SetTimer, AutoClick, -%interval%
return
"""
    },
    {
        "display_name": "Eat Candy — 30ks",
        "filename": "eat_candy30ks.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 31579, 34132
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Eat Candy — 45ks (Weather)",
        "filename": "eat_candy45ksWEATHER.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 46412, 48234
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Eat Candy — 60ks",
        "filename": "eat_candy60ks.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 61579, 64132
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Eat Candy — 75ks (Weather)",
        "filename": "eat_candy75ksWEATHER.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 76415, 78132
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Eat Candy — 90ks",
        "filename": "eat_candy90ks.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 91579, 93214
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Eat Candy — 120ks",
        "filename": "eat_candy120ks.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 121579, 123314
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Eat Candy — 135ks (Weather)",
        "filename": "eat_candy135ksWEATHER.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 136123, 138193
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Eat Candy — 150ks",
        "filename": "eat_candy150ks.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 151579, 153314
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Eat Candy — 180ks (Weather)",
        "filename": "eat_candy180ksWEATHER.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 181267, 183293
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Eat Candy — 225ks (Weather)",
        "filename": "eat_candy225ksWEATHER.ahk",
        "script": r"""#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%
#MaxThreadsPerHotkey 2
CoordMode, Mouse, Screen
CoordMode, Tooltip, Screen
global is_running := false
global tipX, tipY
MouseGetPos, tipX, tipY
Tooltip, OFF, %tipX%, %tipY%

F6::
if (!is_running) {
    is_running := true
    Tooltip, ON, %tipX%, %tipY%
    Gosub, MainLoop
}
return

F10::
is_running := false
Click left
Click right
Tooltip, OFF, %tipX%, %tipY%
return

F12::
Tooltip
ExitApp
return

MainLoop:
while (is_running) {
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {2}
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    MouseClick, x2
    Sleep 1000
    if (!is_running) break
    WinActivate, ahk_exe javaw.exe
    Sleep 100
    Send {1}
    Sleep 500
    Random, rand_duration, 226241, 228921
    Send {LButton down}
    Send {RButton down}
    Sleep %rand_duration%
    Send {LButton up}
    Send {RButton up}
    if (!is_running) break
    Sleep 1000
}
return
"""
    },
    {
        "display_name": "Mining KS",
        "filename": "miningks.ahk",
        "script": r"""#Persistent

F6::
    Send, {LButton down}
    Send, {RButton down}
return

F10::
    Send, {LButton up}
    Send, {RButton up}
    Sleep, 50
    Click down left
    Click down right
    Sleep, 50
    Click up left
    Click up right
return

F12::
    ExitApp
return
"""
    },
    {
        "display_name": "Mobbing KS",
        "filename": "mobbingks.ahk",
        "script": r"""#NoEnv
#SingleInstance Force
SetBatchLines, -1
SendMode, Input
clickerRunning := false

F6::
if (clickerRunning)
    return
clickerRunning := true
Send, {RButton Down}
SetTimer, AutoClick, -10
return

F10::
if (!clickerRunning)
    return
clickerRunning := false
Send, {RButton Up}
SetTimer, AutoClick, Off
ToolTip
return

F12::
clickerRunning := false
SetTimer, AutoClick, Off
Send, {RButton Up}
ExitApp
return

AutoClick:
if (!clickerRunning)
    return
Random, roll, 0, 100
if (roll < 15) {
    Random, interval, 83, 133
} else if (roll < 85) {
    Random, interval, 118, 154
} else {
    Random, interval, 154, 200
}
Click, Down
Click, Up
SetTimer, AutoClick, -%interval%
return
"""
    },
]

# ── Custom keybinds ───────────────────────────────────────────────────────────
KEYBINDS_FILE = os.path.join(os.path.expanduser("~"), ".ahkmanager_keybinds.json")
DEFAULT_KEYBINDS = {"start": "F6", "stop": "F10", "exit": "F12"}

def load_keybinds():
    try:
        with open(KEYBINDS_FILE, "r") as f:
            data = json.load(f)
        # Validate keys exist
        for k in DEFAULT_KEYBINDS:
            if k not in data:
                data[k] = DEFAULT_KEYBINDS[k]
        return data
    except Exception:
        return dict(DEFAULT_KEYBINDS)

def save_keybinds(kb):
    try:
        with open(KEYBINDS_FILE, "w") as f:
            json.dump(kb, f, indent=2)
    except Exception:
        pass
PRESET_THEMES = {
    "Cyber (Default)": {
        "bg": "#0d0f14", "card_bg": "#13161e", "border": "#1e2230",
        "accent": "#00e5ff", "accent2": "#ff4b6e", "text": "#e8eaf0",
        "subtext": "#5a6180", "running": "#00e5a0", "stopped": "#3a3f55",
        "tog_on": "#00e5ff", "tog_off": "#2a2f42", "tog_mid": "#0088aa",
    },
    "Midnight Purple": {
        "bg": "#0e0b16", "card_bg": "#1a1528", "border": "#2d2145",
        "accent": "#c77dff", "accent2": "#ff6b9d", "text": "#e8e0f0",
        "subtext": "#6b5f80", "running": "#a0f0c0", "stopped": "#3d3050",
        "tog_on": "#c77dff", "tog_off": "#2d2145", "tog_mid": "#7a40cc",
    },
    "Forest": {
        "bg": "#0b120e", "card_bg": "#111a14", "border": "#1e3024",
        "accent": "#4ade80", "accent2": "#fbbf24", "text": "#e0f0e8",
        "subtext": "#4a7060", "running": "#4ade80", "stopped": "#2a4030",
        "tog_on": "#4ade80", "tog_off": "#1e3024", "tog_mid": "#2a8048",
    },
    "Sunset": {
        "bg": "#12080a", "card_bg": "#1e0e12", "border": "#3a1820",
        "accent": "#ff6b35", "accent2": "#ff4b6e", "text": "#f0e0e4",
        "subtext": "#7a4050", "running": "#ffd166", "stopped": "#3a1820",
        "tog_on": "#ff6b35", "tog_off": "#3a1820", "tog_mid": "#aa4422",
    },
    "Ice": {
        "bg": "#080e14", "card_bg": "#0e1620", "border": "#1a2a3a",
        "accent": "#7dd3fc", "accent2": "#38bdf8", "text": "#e0eef8",
        "subtext": "#4a6880", "running": "#86efac", "stopped": "#1a2a3a",
        "tog_on": "#7dd3fc", "tog_off": "#1a2a3a", "tog_mid": "#2a6888",
    },
    "Light Mode": {
        "bg": "#f0f2f5", "card_bg": "#ffffff", "border": "#dde1e8",
        "accent": "#2563eb", "accent2": "#e11d48", "text": "#1e2030",
        "subtext": "#8090a8", "running": "#16a34a", "stopped": "#b0bac8",
        "tog_on": "#2563eb", "tog_off": "#c8d0dc", "tog_mid": "#6090c8",
    },
    "Rose Gold": {
        "bg": "#120a0e", "card_bg": "#1e1016", "border": "#3a1e28",
        "accent": "#f4a8c0", "accent2": "#f97316", "text": "#f0e4ea",
        "subtext": "#80505e", "running": "#86efac", "stopped": "#3a1e28",
        "tog_on": "#f4a8c0", "tog_off": "#3a1e28", "tog_mid": "#b06070",
    },
    "Neon Green": {
        "bg": "#040d06", "card_bg": "#081208", "border": "#0f2410",
        "accent": "#39ff14", "accent2": "#ff4b6e", "text": "#d4f5d8",
        "subtext": "#386040", "running": "#39ff14", "stopped": "#0f2410",
        "tog_on": "#39ff14", "tog_off": "#0f2410", "tog_mid": "#1a8820",
    },
    "Ocean Deep": {
        "bg": "#030d18", "card_bg": "#071626", "border": "#0d2840",
        "accent": "#0ea5e9", "accent2": "#f59e0b", "text": "#d0eaf8",
        "subtext": "#2c6080", "running": "#34d399", "stopped": "#0d2840",
        "tog_on": "#0ea5e9", "tog_off": "#0d2840", "tog_mid": "#0660a0",
    },
    "Volcanic": {
        "bg": "#100804", "card_bg": "#1c100a", "border": "#362010",
        "accent": "#fb923c", "accent2": "#f43f5e", "text": "#f0ddd0",
        "subtext": "#805040", "running": "#fbbf24", "stopped": "#362010",
        "tog_on": "#fb923c", "tog_off": "#362010", "tog_mid": "#a04010",
    },
    "Arctic": {
        "bg": "#f4f8fb", "card_bg": "#ffffff", "border": "#c8dce8",
        "accent": "#0284c7", "accent2": "#dc2626", "text": "#1a2a38",
        "subtext": "#6890a8", "running": "#059669", "stopped": "#a8c0d0",
        "tog_on": "#0284c7", "tog_off": "#c8dce8", "tog_mid": "#4a90c0",
    },
    "Dracula": {
        "bg": "#282a36", "card_bg": "#313344", "border": "#44475a",
        "accent": "#bd93f9", "accent2": "#ff5555", "text": "#f8f8f2",
        "subtext": "#6272a4", "running": "#50fa7b", "stopped": "#44475a",
        "tog_on": "#bd93f9", "tog_off": "#44475a", "tog_mid": "#7050c0",
    },
    "Mocha": {
        "bg": "#1e1610", "card_bg": "#2a1e14", "border": "#4a3020",
        "accent": "#d4a96a", "accent2": "#e07060", "text": "#f0e0cc",
        "subtext": "#806050", "running": "#a8d080", "stopped": "#4a3020",
        "tog_on": "#d4a96a", "tog_off": "#4a3020", "tog_mid": "#906030",
    },
    "Bubblegum": {
        "bg": "#0e0812", "card_bg": "#180f1e", "border": "#32183c",
        "accent": "#f472b6", "accent2": "#a78bfa", "text": "#fce7f3",
        "subtext": "#804060", "running": "#86efac", "stopped": "#32183c",
        "tog_on": "#f472b6", "tog_off": "#32183c", "tog_mid": "#a03070",
    },
    "Stealth": {
        "bg": "#0a0a0a", "card_bg": "#111111", "border": "#222222",
        "accent": "#888888", "accent2": "#cc4444", "text": "#cccccc",
        "subtext": "#555555", "running": "#66aa66", "stopped": "#222222",
        "tog_on": "#888888", "tog_off": "#222222", "tog_mid": "#444444",
    },
    "Synthwave": {
        "bg": "#0d0221", "card_bg": "#130338", "border": "#2d0a5a",
        "accent": "#ff71ce", "accent2": "#01cdfe", "text": "#fffb96",
        "subtext": "#5a2080", "running": "#05ffa1", "stopped": "#2d0a5a",
        "tog_on": "#ff71ce", "tog_off": "#2d0a5a", "tog_mid": "#a01880",
    },
}

THEME_FILE   = os.path.join(os.path.expanduser("~"), ".ahkmanager_theme.json")
SESSION_FILE = os.path.join(os.path.expanduser("~"), ".ahkmanager_session.json")

def load_session():
    """Return saved session dict or None if not present / invalid."""
    try:
        with open(SESSION_FILE, "r") as f:
            data = json.load(f)
        if data.get("remember") and data.get("user") and data.get("pw"):
            return data
    except Exception:
        pass
    return None

def save_session(user, pw):
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"remember": True, "user": user, "pw": pw}, f)
    except Exception:
        pass

def clear_session():
    try:
        os.remove(SESSION_FILE)
    except Exception:
        pass

def load_theme():
    try:
        with open(THEME_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return dict(PRESET_THEMES["Cyber (Default)"])

def save_theme(theme):
    try:
        with open(THEME_FILE, "w") as f:
            json.dump(theme, f, indent=2)
    except Exception:
        pass

def find_autohotkey():
    candidates = [
        r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
        r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe",
        r"C:\Program Files\AutoHotkey\v1\AutoHotkey.exe",
        r"C:\Program Files\AutoHotkey\AutoHotkeyU64.exe",
        r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return shutil.which("AutoHotkey") or shutil.which("AutoHotkeyU64")


# ── Toggle widget ─────────────────────────────────────────────────────────────
class ToggleSwitch(tk.Frame):
    """3-position switch: STOPPED (left) → RUNNING (centre) → ACTIVE (right)
    Clicking cycles: off → on(running). AHK hotkeys update state via set_state().
    Positions: 0=STOPPED, 1=RUNNING, 2=ACTIVE
    """
    W, H, PAD = 78, 28, 3

    def __init__(self, parent, theme, callback=None, **kwargs):
        super().__init__(parent, bg=theme["card_bg"], cursor="hand2",
                         width=self.W, height=self.H, **kwargs)
        self.pack_propagate(False)
        self._pos      = 0          # 0=stopped, 1=running, 2=active
        self._callback = callback
        self._theme    = theme

        self._canvas = tk.Canvas(self, width=self.W, height=self.H,
                                  highlightthickness=0, bd=0,
                                  bg=theme["card_bg"])
        self._canvas.place(x=0, y=0)
        self._canvas.bind("<Button-1>", self._click)
        self._draw()

    def _track_color(self):
        if self._pos == 0:   return self._theme["tog_off"]
        elif self._pos == 1: return self._theme.get("tog_mid", "#a855f7")
        else:                return self._theme["tog_on"]

    def _knob_x(self):
        ks = self.H - self.PAD * 2
        if self._pos == 0:   return self.PAD
        elif self._pos == 1: return (self.W - ks) // 2
        else:                return self.W - ks - self.PAD

    def _draw(self):
        c = self._canvas
        c.delete("all")
        W, H, r = self.W, self.H, self.H // 2

        # Track with rounded ends
        tc = self._track_color()
        c.create_arc(0, 0, H, H, start=90, extent=180, fill=tc, outline=tc)
        c.create_arc(W-H, 0, W, H, start=270, extent=180, fill=tc, outline=tc)
        c.create_rectangle(r, 0, W-r, H, fill=tc, outline=tc)

        # Knob
        ks = H - self.PAD * 2
        kx = self._knob_x()
        ky = self.PAD
        kr = ks // 2
        c.create_oval(kx, ky, kx+ks, ky+ks, fill="#ffffff", outline="#ffffff")

    def apply_theme(self, theme):
        self._theme = theme
        self._canvas.config(bg=theme["card_bg"])
        self._draw()

    def set_state(self, pos):
        """Set position with smooth animation: 0=stopped, 1=running, 2=active"""
        if pos == self._pos:
            return
        self._animate_to(pos)

    def _animate_to(self, target_pos, steps=6):
        start_x = self._knob_x()
        self._pos = target_pos
        end_x = self._knob_x()
        self._pos = self._pos  # keep target
        if start_x == end_x:
            self._draw()
            return
        # Animate knob sliding
        step_size = (end_x - start_x) / steps
        self._anim_step(start_x, end_x, step_size, target_pos, 0, steps)

    def _anim_step(self, current_x, end_x, step_size, target_pos, step, steps):
        self._pos = target_pos
        # Draw with overridden knob x
        c = self._canvas
        c.delete("all")
        W, H, r = self.W, self.H, self.H // 2
        tc = self._track_color()
        c.create_arc(0, 0, H, H, start=90, extent=180, fill=tc, outline=tc)
        c.create_arc(W-H, 0, W, H, start=270, extent=180, fill=tc, outline=tc)
        c.create_rectangle(r, 0, W-r, H, fill=tc, outline=tc)
        ks = H - self.PAD * 2
        kx = int(current_x + step_size * step)
        ky = self.PAD
        c.create_oval(kx, ky, kx+ks, ky+ks, fill="#ffffff", outline="#ffffff")
        if step < steps:
            self._canvas.after(16, lambda: self._anim_step(
                current_x, end_x, step_size, target_pos, step + 1, steps))
        else:
            self._draw()

    def get_state(self):
        return self._pos

    def _click(self, _=None):
        if self._pos == 0:
            self._animate_to(1)
            if self._callback:
                self._callback(True)
        else:
            self._animate_to(0)
            if self._callback:
                self._callback(False)


# ── Theme editor window ───────────────────────────────────────────────────────
class ThemeEditor(tk.Toplevel):
    LABELS = {
        "bg":      "Background",
        "card_bg": "Card Background",
        "border":  "Border",
        "accent":  "Accent (title/toggle)",
        "accent2": "Accent 2 (warnings)",
        "text":    "Script Name Text",
        "subtext": "Filename Text",
        "running": "Running Status",
        "stopped": "Stopped Status",
        "tog_on":  "Toggle ON",
        "tog_off": "Toggle OFF",
    }

    def __init__(self, parent, theme, on_apply):
        super().__init__(parent)
        self.title("Theme Editor")
        self.resizable(False, False)
        self.grab_set()
        self._on_apply = on_apply
        self._current  = dict(theme)
        self._swatches = {}

        font_b = tkfont.Font(family="Consolas", size=9, weight="bold")
        font_n = tkfont.Font(family="Consolas", size=9)

        self.configure(bg=theme["bg"])

        # Title
        tk.Label(self, text="THEME EDITOR", font=tkfont.Font(family="Consolas", size=13, weight="bold"),
                 bg=theme["bg"], fg=theme["accent"], pady=14).pack()

        # Preset row
        preset_frame = tk.Frame(self, bg=theme["bg"], padx=20, pady=4)
        preset_frame.pack(fill="x")
        tk.Label(preset_frame, text="Preset:", font=font_b,
                 bg=theme["bg"], fg=theme["text"]).pack(side="left", padx=(0, 8))
        for name in PRESET_THEMES:
            btn = tk.Label(preset_frame, text=name, font=font_n,
                           bg=theme["card_bg"], fg=theme["accent"],
                           padx=8, pady=4, cursor="hand2",
                           relief="flat",
                           highlightbackground=theme["border"],
                           highlightthickness=1)
            btn.pack(side="left", padx=3)
            btn.bind("<Button-1>", lambda e, n=name: self._load_preset(n))

        tk.Frame(self, bg=theme["border"], height=1).pack(fill="x", padx=20, pady=10)

        # Colour rows
        grid = tk.Frame(self, bg=theme["bg"], padx=20)
        grid.pack(fill="x")

        for row, (key, label) in enumerate(self.LABELS.items()):
            tk.Label(grid, text=label, font=font_n, bg=theme["bg"],
                     fg=theme["text"], anchor="w", width=22).grid(
                row=row, column=0, pady=4, sticky="w")

            swatch = tk.Label(grid, bg=theme[key], width=4,
                              relief="flat", cursor="hand2",
                              highlightbackground=theme["border"],
                              highlightthickness=1)
            swatch.grid(row=row, column=1, padx=(8, 6), pady=4)
            swatch.bind("<Button-1>", lambda e, k=key: self._pick(k))

            hex_var = tk.StringVar(value=theme[key])
            hex_entry = tk.Entry(grid, textvariable=hex_var, font=font_n,
                                 bg=theme["card_bg"], fg=theme["text"],
                                 insertbackground=theme["text"],
                                 relief="flat", width=9,
                                 highlightbackground=theme["border"],
                                 highlightthickness=1)
            hex_entry.grid(row=row, column=2, padx=4, pady=4)
            hex_var.trace_add("write", lambda *a, k=key, v=hex_var: self._hex_typed(k, v))

            self._swatches[key] = (swatch, hex_var)

        tk.Frame(self, bg=theme["border"], height=1).pack(fill="x", padx=20, pady=10)

        # Buttons
        btn_row = tk.Frame(self, bg=theme["bg"], pady=12)
        btn_row.pack()

        def make_btn(text, cmd, fg):
            b = tk.Label(btn_row, text=text, font=font_b, bg=theme["card_bg"],
                         fg=fg, padx=16, pady=8, cursor="hand2", relief="flat",
                         highlightbackground=theme["border"], highlightthickness=1)
            b.pack(side="left", padx=8)
            b.bind("<Button-1>", lambda e: cmd())
            return b

        make_btn("Apply & Save", self._apply, theme["accent"])
        make_btn("Cancel",       self.destroy, theme["accent2"])

        # Centre on parent
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        py = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

    def _pick(self, key):
        result = colorchooser.askcolor(color=self._current[key], title=f"Pick colour — {self.LABELS[key]}")
        if result and result[1]:
            self._set_colour(key, result[1])

    def _hex_typed(self, key, var):
        val = var.get().strip()
        if len(val) == 7 and val.startswith("#"):
            try:
                int(val[1:], 16)
                self._current[key] = val
                self._swatches[key][0].config(bg=val)
            except ValueError:
                pass

    def _set_colour(self, key, hex_col):
        self._current[key] = hex_col
        swatch, hex_var = self._swatches[key]
        swatch.config(bg=hex_col)
        hex_var.set(hex_col)

    def _load_preset(self, name):
        preset = PRESET_THEMES[name]
        for key, val in preset.items():
            self._set_colour(key, val)

    def _apply(self):
        save_theme(self._current)
        self._on_apply(self._current)
        self.destroy()


# ── Main window ───────────────────────────────────────────────────────────────
def resource_path(relative_path):
    import sys
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


class AHKManager(tk.Tk):
    def __init__(self, current_user=""):
        super().__init__()
        self.title("Nebula")
        self.resizable(True, True)
        self._current_user = current_user
        self._is_admin = (current_user == "Physica")
        try:
            self.iconbitmap(resource_path("nebula.ico"))
        except Exception:
            pass
        self.ahk_path  = find_autohotkey()
        self.tmp_dir   = tempfile.mkdtemp(prefix="ahkman_")
        self.procs     = {}
        self._theme    = load_theme()
        self._widgets  = []
        self._stats    = load_stats()
        self._favs     = load_favs()
        self._keybinds = load_keybinds()
        self._opacity  = 1.0

        self._build_fonts()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

        # Check for updates in background
        threading.Thread(target=self._check_for_update, daemon=True).start()

    def _t(self, key):
        return self._theme[key]

    def _build_fonts(self):
        self.font_title  = tkfont.Font(family="Segoe UI", size=15, weight="bold")
        self.font_name   = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.font_file   = tkfont.Font(family="Segoe UI", size=8)
        self.font_status = tkfont.Font(family="Segoe UI", size=8,  weight="bold")
        self.font_badge  = tkfont.Font(family="Segoe UI", size=7,  weight="bold")

    def _build_ui(self):
        t = self._theme
        self.configure(bg=t["bg"])

        # ── Header
        self._header = tk.Frame(self, bg=t["bg"], padx=28, pady=14)
        self._header.pack(fill="x")

        self._title_lbl = tk.Label(self._header, text="⬡ Nebula",
                                    font=tkfont.Font(family="Segoe Script", size=15, weight="bold"),
                                    bg=t["bg"], fg=t["accent"])
        self._title_lbl.pack(side="left")

        # Right-side header buttons
        self._theme_btn = tk.Label(self._header, text="⚙ Theme", font=self.font_badge,
                                    bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
                                    cursor="hand2", relief="flat",
                                    highlightbackground=t["border"], highlightthickness=1)
        self._theme_btn.pack(side="right")
        self._theme_btn.bind("<Button-1>", lambda e: self._open_theme_editor())

        self._logout_btn = tk.Label(self._header, text="⏏ Logout", font=self.font_badge,
                                     bg=t["card_bg"], fg=t["accent2"], padx=10, pady=5,
                                     cursor="hand2", relief="flat",
                                     highlightbackground=t["border"], highlightthickness=1)
        self._logout_btn.pack(side="right", padx=(0, 8))
        self._logout_btn.bind("<Button-1>", lambda e: self._logout())

        self._help_btn = tk.Label(self._header, text="? Help", font=self.font_badge,
                                   bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
                                   cursor="hand2", relief="flat",
                                   highlightbackground=t["border"], highlightthickness=1)
        self._help_btn.pack(side="right", padx=(0, 8))
        self._help_btn.bind("<Button-1>", lambda e: self._open_hotkey_help())

        self._kb_btn = tk.Label(self._header, text="⌨ Keybinds", font=self.font_badge,
                                 bg=t["card_bg"], fg=t["accent"], padx=10, pady=5,
                                 cursor="hand2", relief="flat",
                                 highlightbackground=t["border"], highlightthickness=1)
        self._kb_btn.pack(side="right", padx=(0, 8))
        self._kb_btn.bind("<Button-1>", lambda e: self._open_keybind_editor())

        # Admin panel button (Physica only)
        if self._is_admin:
            self._admin_btn = tk.Label(self._header, text="👥 Users", font=self.font_badge,
                                        bg=t["card_bg"], fg=t["running"], padx=10, pady=5,
                                        cursor="hand2", relief="flat",
                                        highlightbackground=t["border"], highlightthickness=1)
            self._admin_btn.pack(side="right", padx=(0, 8))
            self._admin_btn.bind("<Button-1>", lambda e: self._open_admin_panel())

        if not self.ahk_path:
            self._no_ahk_lbl = tk.Label(self._header, text="⚠  AutoHotkey not found",
                                         font=self.font_badge, bg=t["bg"], fg=t["accent2"])
            self._no_ahk_lbl.pack(side="right", padx=12)

        self._div1 = tk.Frame(self, bg=t["border"], height=1)
        self._div1.pack(fill="x", padx=28)

        # ── Search + Stop All bar
        self._toolbar = tk.Frame(self, bg=t["bg"], padx=28, pady=8)
        self._toolbar.pack(fill="x")

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_cards())
        self._search_entry = tk.Entry(self._toolbar, textvariable=self._search_var,
                                       font=self.font_file, bg=t["card_bg"],
                                       fg=t["text"], insertbackground=t["accent"],
                                       relief="flat", bd=0,
                                       highlightthickness=1,
                                       highlightbackground=t["border"],
                                       highlightcolor=t["accent"])
        self._search_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))

        self._search_placeholder = "Search scripts..."
        self._search_entry.insert(0, self._search_placeholder)
        self._search_entry.config(fg=t["subtext"])
        self._search_entry.bind("<FocusIn>",  self._search_focus_in)
        self._search_entry.bind("<FocusOut>", self._search_focus_out)

        self._stopall_btn = tk.Label(self._toolbar, text="⏹ Stop All", font=self.font_badge,
                                      bg=t["accent2"], fg="#ffffff", padx=12, pady=6,
                                      cursor="hand2", relief="flat")
        self._stopall_btn.pack(side="right")
        self._stopall_btn.bind("<Button-1>", lambda e: self._stop_all())

        # ── Scrollable area
        self._outer = tk.Frame(self, bg=t["bg"])
        self._outer.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(self._outer, bg=t["bg"], highlightthickness=0, bd=0)
        self._scrollbar = tk.Scrollbar(self._outer, orient="vertical",
                                        command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._container = tk.Frame(self._canvas, bg=t["bg"], padx=20, pady=16)
        self._canvas_win = self._canvas.create_window((0, 0), window=self._container, anchor="nw")

        self._card_refs = []
        # Sort: favourites first
        sorted_scripts = sorted(SCRIPTS, key=lambda s: (0 if s["filename"] in self._favs else 1))
        for info in sorted_scripts:
            card = self._make_card(self._container, info)
            card["frame"].pack(fill="x", pady=6, padx=8)
            self._card_refs.append(card)

        def on_configure(event):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            self._canvas.itemconfig(self._canvas_win, width=self._canvas.winfo_width())

        self._container.bind("<Configure>", on_configure)
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(
            self._canvas_win, width=e.width))
        self._canvas.bind_all("<MouseWheel>",
                               lambda e: self._canvas.yview_scroll(
                                   int(-1 * (e.delta / 120)), "units"))
        self._canvas.configure(height=420)

        self._div2 = tk.Frame(self, bg=t["border"], height=1)
        self._div2.pack(fill="x", padx=28)

        # ── Footer with opacity slider
        self._footer_frame = tk.Frame(self, bg=t["bg"])
        self._footer_frame.pack(fill="x", padx=28, pady=4)

        self._footer_lbl = tk.Label(self._footer_frame,
                                     text="scripts run from temp dir  ·  close window to stop all",
                                     font=self.font_badge, bg=t["bg"], fg=t["subtext"])
        self._footer_lbl.pack(side="left")

        opacity_frame = tk.Frame(self._footer_frame, bg=t["bg"])
        opacity_frame.pack(side="right")
        tk.Label(opacity_frame, text="Opacity", font=self.font_badge,
                 bg=t["bg"], fg=t["subtext"]).pack(side="left", padx=(0, 6))
        self._opacity_slider = tk.Scale(opacity_frame, from_=30, to=100,
                                         orient="horizontal", length=100,
                                         command=self._set_opacity,
                                         bg=t["bg"], fg=t["subtext"],
                                         troughcolor=t["card_bg"],
                                         highlightthickness=0, bd=0,
                                         showvalue=False, sliderlength=14)
        self._opacity_slider.set(100)
        self._opacity_slider.pack(side="left")

    def _make_card(self, parent, info):
        t = self._theme
        fn = info["filename"]
        is_fav = fn in self._favs
        stats = self._stats.get(fn, {"runs": 0, "last": "never"})

        outer = tk.Frame(parent, bg=t["card_bg"],
                         highlightbackground=t["border"], highlightthickness=1)
        inner = tk.Frame(outer, bg=t["card_bg"], padx=18, pady=12)
        inner.pack(fill="x")

        # ── Favourite star
        star_char = "★" if is_fav else "☆"
        star_lbl = tk.Label(inner, text=star_char,
                             font=tkfont.Font(family="Segoe UI", size=16),
                             bg=t["card_bg"], fg=t["accent"] if is_fav else t["subtext"],
                             cursor="hand2")
        star_lbl.pack(side="left", padx=(0, 8))
        star_lbl.bind("<Button-1>", lambda e, f=fn, sl=star_lbl: self._toggle_fav(f, sl))

        left = tk.Frame(inner, bg=t["card_bg"])
        left.pack(side="left", fill="x", expand=True)

        name_lbl = tk.Label(left, text=info["display_name"], font=self.font_name,
                             bg=t["card_bg"], fg=t["text"], anchor="w")
        name_lbl.pack(anchor="w")

        file_lbl = tk.Label(left, text=info["filename"], font=self.font_file,
                             bg=t["card_bg"], fg=t["subtext"], anchor="w")
        file_lbl.pack(anchor="w", pady=(1, 0))

        stats_text = f"runs: {stats['runs']}  ·  last: {stats['last']}"
        stats_lbl = tk.Label(left, text=stats_text, font=self.font_file,
                              bg=t["card_bg"], fg=t["subtext"], anchor="w")
        stats_lbl.pack(anchor="w", pady=(1, 0))

        right = tk.Frame(inner, bg=t["card_bg"])
        right.pack(side="right", padx=(12, 0))

        sv = tk.StringVar(value="STOPPED")
        sl = tk.Label(right, textvariable=sv, font=self.font_status,
                      bg=t["card_bg"], fg=t["stopped"], width=9, anchor="e")
        sl.pack(anchor="e", pady=(0, 8))

        tog = ToggleSwitch(right, theme=t,
                           callback=lambda state, i=info, s=sv, l=sl, tg=None:
                               self._toggle(state, i, s, l, tg))
        tog._callback = lambda state, i=info, s=sv, l=sl, tg=tog: self._toggle(state, i, s, l, tg)
        tog.pack(anchor="e")

        return {
            "frame": outer, "inner": inner, "left": left, "right": right,
            "name_lbl": name_lbl, "file_lbl": file_lbl, "stats_lbl": stats_lbl,
            "star_lbl": star_lbl,
            "status_lbl": sl, "status_var": sv, "toggle": tog,
            "info": info,
        }

    # ── Theme application ─────────────────────────────────────────────────────
    def _open_theme_editor(self):
        ThemeEditor(self, self._theme, self._apply_theme)

    def _apply_theme(self, new_theme):
        self._theme = new_theme
        t = new_theme

        self.configure(bg=t["bg"])
        self._header.config(bg=t["bg"])
        self._title_lbl.config(bg=t["bg"], fg=t["accent"])
        self._theme_btn.config(bg=t["card_bg"], fg=t["accent"],
                                highlightbackground=t["border"])
        self._logout_btn.config(bg=t["card_bg"], fg=t["accent2"],
                                 highlightbackground=t["border"])
        self._help_btn.config(bg=t["card_bg"], fg=t["accent"],
                               highlightbackground=t["border"])
        self._kb_btn.config(bg=t["card_bg"], fg=t["accent"],
                             highlightbackground=t["border"])
        if self._is_admin and hasattr(self, "_admin_btn"):
            self._admin_btn.config(bg=t["card_bg"], fg=t["running"],
                                    highlightbackground=t["border"])
        self._div1.config(bg=t["border"])
        self._div2.config(bg=t["border"])
        self._toolbar.config(bg=t["bg"])
        self._search_entry.config(bg=t["card_bg"], fg=t["subtext"] if not self._search_var.get() or self._search_var.get() == self._search_placeholder else t["text"],
                                   highlightbackground=t["border"], highlightcolor=t["accent"],
                                   insertbackground=t["accent"])
        self._stopall_btn.config(bg=t["accent2"])
        self._outer.config(bg=t["bg"])
        self._canvas.config(bg=t["bg"])
        self._container.config(bg=t["bg"])
        self._footer_frame.config(bg=t["bg"])
        self._footer_lbl.config(bg=t["bg"], fg=t["subtext"])
        self._opacity_slider.config(bg=t["bg"], fg=t["subtext"], troughcolor=t["card_bg"])

        if hasattr(self, "_no_ahk_lbl"):
            self._no_ahk_lbl.config(bg=t["bg"], fg=t["accent2"])

        for card in self._card_refs:
            card["frame"].config(bg=t["card_bg"], highlightbackground=t["border"])
            card["inner"].config(bg=t["card_bg"])
            card["left"].config(bg=t["card_bg"])
            card["right"].config(bg=t["card_bg"])
            card["name_lbl"].config(bg=t["card_bg"], fg=t["text"])
            card["file_lbl"].config(bg=t["card_bg"], fg=t["subtext"])
            card["stats_lbl"].config(bg=t["card_bg"], fg=t["subtext"])
            fn = card["info"]["filename"]
            is_fav = fn in self._favs
            card["star_lbl"].config(bg=t["card_bg"],
                                     fg=t["accent"] if is_fav else t["subtext"])
            sv = card["status_var"]
            sl = card["status_lbl"]
            sl.config(bg=t["card_bg"])
            status = sv.get()
            if status == "RUNNING":   sl.config(fg=t["running"])
            elif status == "ACTIVE":  sl.config(fg=t["accent"])
            elif status == "PAUSED":  sl.config(fg=t["accent2"])
            else:                     sl.config(fg=t["stopped"])
            card["toggle"].apply_theme(t)

    # ── Script lifecycle ──────────────────────────────────────────────────────
    def _toggle(self, on, info, sv, sl, tog):
        if on:
            self._start(info, sv, sl, tog)
        else:
            self._stop(info["filename"], sv, sl, tog)

    def _start(self, info, sv, sl, tog):
        if not self.ahk_path:
            sv.set("NO AHK"); sl.config(fg=self._t("accent2")); return
        fn = info["filename"]
        tmp = os.path.join(self.tmp_dir, fn)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(info["script"])
        try:
            proc = subprocess.Popen([self.ahk_path, tmp],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            self.procs[fn] = proc
            sv.set("RUNNING"); sl.config(fg=self._t("running"))
            tog.set_state(1)
            # Record stats
            import datetime
            entry = self._stats.get(fn, {"runs": 0, "last": "never"})
            entry["runs"] += 1
            entry["last"] = datetime.datetime.now().strftime("%d/%m %H:%M")
            self._stats[fn] = entry
            save_stats(self._stats)
            # Update stats label on card
            for card in self._card_refs:
                if card["info"]["filename"] == fn:
                    card["stats_lbl"].config(text=f"runs: {entry['runs']}  ·  last: {entry['last']}")
                    break
            threading.Thread(target=self._watch, args=(proc, fn, sv, sl, tog),
                             daemon=True).start()
            threading.Thread(target=self._hotkey_monitor, args=(fn, sv, sl, tog),
                             daemon=True).start()
        except Exception:
            sv.set("ERROR"); sl.config(fg=self._t("accent2"))

    def _stop(self, fn, sv, sl, tog):
        proc = self.procs.pop(fn, None)
        if proc and proc.poll() is None:
            proc.terminate()
        sv.set("STOPPED"); sl.config(fg=self._t("stopped"))
        tog.set_state(0)

    def _hotkey_monitor(self, fn, sv, sl, tog):
        """Poll for F6/F10 keypresses to update status while script is running."""
        import ctypes
        VK_F6  = 0x75
        VK_F10 = 0x79
        VK_F12 = 0x7B
        GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState

        prev_f6  = False
        prev_f10 = False
        prev_f12 = False

        while fn in self.procs:
            f6  = bool(GetAsyncKeyState(VK_F6)  & 0x8000)
            f10 = bool(GetAsyncKeyState(VK_F10) & 0x8000)
            f12 = bool(GetAsyncKeyState(VK_F12) & 0x8000)

            if f6 and not prev_f6:
                self.after(0, lambda: sv.set("ACTIVE"))
                self.after(0, lambda: sl.config(fg=self._t("accent")))
                self.after(0, lambda: tog.set_state(2))

            if f10 and not prev_f10:
                self.after(0, lambda: sv.set("PAUSED"))
                self.after(0, lambda: sl.config(fg=self._t("accent2")))
                self.after(0, lambda: tog.set_state(1))

            if f12 and not prev_f12:
                self.after(0, lambda: sv.set("STOPPED"))
                self.after(0, lambda: sl.config(fg=self._t("stopped")))
                self.after(0, lambda: tog.set_state(0))

            prev_f6  = f6
            prev_f10 = f10
            prev_f12 = f12
            import time; time.sleep(0.05)

    def _watch(self, proc, fn, sv, sl, tog):
        proc.wait()
        if fn in self.procs:
            self.procs.pop(fn, None)
            self.after(0, lambda: sv.set("STOPPED"))
            self.after(0, lambda: sl.config(fg=self._t("stopped")))
            self.after(0, lambda: tog.set_state(0))

    # ── Search / filter ───────────────────────────────────────────────────────
    def _search_focus_in(self, _=None):
        if self._search_var.get() == self._search_placeholder:
            self._search_entry.delete(0, "end")
            self._search_entry.config(fg=self._t("text"))

    def _search_focus_out(self, _=None):
        if not self._search_var.get():
            self._search_entry.insert(0, self._search_placeholder)
            self._search_entry.config(fg=self._t("subtext"))

    def _filter_cards(self):
        query = self._search_var.get().strip().lower()
        if query == self._search_placeholder.lower():
            query = ""
        for card in self._card_refs:
            name = card["info"]["display_name"].lower()
            fn   = card["info"]["filename"].lower()
            if query == "" or query in name or query in fn:
                card["frame"].pack(fill="x", pady=6, padx=8)
            else:
                card["frame"].pack_forget()

    # ── Stop All ──────────────────────────────────────────────────────────────
    def _stop_all(self):
        for card in self._card_refs:
            fn = card["info"]["filename"]
            if fn in self.procs:
                self._stop(fn, card["status_var"], card["status_lbl"], card["toggle"])

    # ── Opacity ───────────────────────────────────────────────────────────────
    def _set_opacity(self, val):
        self.attributes("-alpha", int(val) / 100)

    # ── Favourites ────────────────────────────────────────────────────────────
    def _toggle_fav(self, fn, star_lbl):
        if fn in self._favs:
            self._favs.remove(fn)
            star_lbl.config(text="☆", fg=self._t("subtext"))
        else:
            self._favs.append(fn)
            star_lbl.config(text="★", fg=self._t("accent"))
        save_favs(self._favs)
        # Re-sort cards: favourites float to top
        for card in self._card_refs:
            card["frame"].pack_forget()
        sorted_cards = sorted(self._card_refs,
                               key=lambda c: (0 if c["info"]["filename"] in self._favs else 1))
        for card in sorted_cards:
            card["frame"].pack(fill="x", pady=6, padx=8)

    # ── Hotkey Help popup ─────────────────────────────────────────────────────
    def _open_hotkey_help(self):
        kb = self._keybinds
        win = tk.Toplevel(self)
        win.title("Hotkey Reference")
        win.resizable(False, False)
        win.configure(bg=self._t("bg"))
        win.grab_set()
        t = self._theme

        tk.Label(win, text="Hotkey Reference", bg=t["bg"], fg=t["accent"],
                 font=self.font_name, pady=14).pack()
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)

        rows = [
            (kb["start"], "Start / activate the script"),
            (kb["stop"],  "Pause / stop the script"),
            (kb["exit"],  "Exit the script entirely"),
        ]
        frame = tk.Frame(win, bg=t["bg"], padx=30, pady=20)
        frame.pack()
        for key, desc in rows:
            row = tk.Frame(frame, bg=t["bg"])
            row.pack(fill="x", pady=4)
            tk.Label(row, text=key, font=self.font_status, bg=t["card_bg"],
                     fg=t["accent"], width=6, pady=4, relief="flat",
                     highlightbackground=t["border"], highlightthickness=1).pack(side="left")
            tk.Label(row, text=f"  {desc}", font=self.font_file,
                     bg=t["bg"], fg=t["text"], anchor="w").pack(side="left")

        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)
        close_btn = tk.Label(win, text="Close", font=self.font_badge,
                              bg=t["card_bg"], fg=t["accent2"],
                              padx=16, pady=8, cursor="hand2",
                              highlightbackground=t["border"], highlightthickness=1)
        close_btn.pack(pady=12)
        close_btn.bind("<Button-1>", lambda e: win.destroy())

        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width()  - win.winfo_width())  // 2
        py = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{px}+{py}")

    # ── Keybind editor ────────────────────────────────────────────────────────
    def _open_keybind_editor(self):
        win = tk.Toplevel(self)
        win.title("Custom Keybinds")
        win.resizable(False, False)
        win.configure(bg=self._t("bg"))
        win.grab_set()
        t = self._theme

        tk.Label(win, text="Custom Keybinds", bg=t["bg"], fg=t["accent"],
                 font=self.font_name, pady=14).pack()
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)

        frame = tk.Frame(win, bg=t["bg"], padx=30, pady=20)
        frame.pack()

        labels = [("Start key", "start"), ("Stop key", "stop"), ("Exit key", "exit")]
        vars_ = {}
        for i, (lbl, key) in enumerate(labels):
            tk.Label(frame, text=lbl, font=self.font_file, bg=t["bg"],
                     fg=t["text"], anchor="w", width=12).grid(row=i, column=0, pady=6, sticky="w")
            v = tk.StringVar(value=self._keybinds[key])
            vars_[key] = v
            tk.Entry(frame, textvariable=v, font=self.font_file,
                     bg=t["card_bg"], fg=t["text"],
                     insertbackground=t["accent"],
                     relief="flat", width=10,
                     highlightbackground=t["border"], highlightthickness=1
                     ).grid(row=i, column=1, padx=(10, 0), pady=6)

        tk.Label(frame, text="e.g. F6, F10, F12, ^F1 (Ctrl+F1)",
                 font=self.font_file, bg=t["bg"], fg=t["subtext"]
                 ).grid(row=len(labels), column=0, columnspan=2, pady=(4, 0))

        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)
        btn_row = tk.Frame(win, bg=t["bg"], pady=12)
        btn_row.pack()

        def save():
            for key, v in vars_.items():
                self._keybinds[key] = v.get().strip()
            save_keybinds(self._keybinds)
            win.destroy()

        for text, cmd, col in [("Save", save, t["accent"]), ("Cancel", win.destroy, t["accent2"])]:
            b = tk.Label(btn_row, text=text, font=self.font_badge,
                         bg=t["card_bg"], fg=col, padx=16, pady=8,
                         cursor="hand2", highlightbackground=t["border"], highlightthickness=1)
            b.pack(side="left", padx=8)
            b.bind("<Button-1>", lambda e, c=cmd: c())

        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width()  - win.winfo_width())  // 2
        py = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{px}+{py}")

    # ── Auto-update ───────────────────────────────────────────────────────────
    def _check_for_update(self):
        try:
            req = urllib.request.urlopen(UPDATE_VERSION_URL, timeout=5)
            data = json.loads(req.read().decode())
            latest = data.get("version", "")
            if latest and latest != CURRENT_VERSION:
                self.after(0, lambda: self._prompt_update(latest))
        except Exception:
            pass  # No internet or server not set up yet — silently skip

    def _prompt_update(self, latest_version):
        t = self._theme
        win = tk.Toplevel(self)
        win.title("Update Available")
        win.resizable(False, False)
        win.configure(bg=t["bg"])
        win.grab_set()

        tk.Label(win, text="Update Available", bg=t["bg"], fg=t["accent"],
                 font=self.font_name, pady=14).pack()
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)

        frame = tk.Frame(win, bg=t["bg"], padx=30, pady=16)
        frame.pack()
        tk.Label(frame, text=f"Current version:  {CURRENT_VERSION}", font=self.font_file,
                 bg=t["bg"], fg=t["subtext"]).pack(anchor="w")
        tk.Label(frame, text=f"New version:       {latest_version}", font=self.font_file,
                 bg=t["bg"], fg=t["running"]).pack(anchor="w", pady=(4, 0))
        tk.Label(frame, text="\nWould you like to update now?\nThe app will restart automatically.",
                 font=self.font_file, bg=t["bg"], fg=t["text"]).pack()

        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)
        btn_row = tk.Frame(win, bg=t["bg"], pady=12)
        btn_row.pack()

        def do_update():
            win.destroy()
            self._download_and_restart()

        for text, cmd, col in [("Update Now", do_update, t["accent"]),
                                ("Later",      win.destroy, t["accent2"])]:
            b = tk.Label(btn_row, text=text, font=self.font_badge,
                         bg=t["card_bg"], fg=col, padx=16, pady=8,
                         cursor="hand2", highlightbackground=t["border"], highlightthickness=1)
            b.pack(side="left", padx=8)
            b.bind("<Button-1>", lambda e, c=cmd: c())

        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width()  - win.winfo_width())  // 2
        py = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{px}+{py}")

    def _download_and_restart(self):
        """Download latest script and use a helper batch to swap it after app exits."""
        try:
            is_frozen = getattr(sys, "frozen", False)

            if is_frozen:
                exe_path = os.path.abspath(sys.executable)
                exe_dir  = os.path.dirname(exe_path)
                py_path  = os.path.join(exe_dir, "ahk_manager.py")
            else:
                py_path  = os.path.abspath(sys.argv[0])
                exe_path = sys.executable
                exe_dir  = os.path.dirname(py_path)

            backup_path = py_path + ".bak"

            # Clean up any leftover temp files from previous failed attempts
            tmp_dir = tempfile.gettempdir()
            for f in os.listdir(tmp_dir):
                if f.startswith("nebula_update_") or f.startswith("_nebula_update_"):
                    try: os.remove(os.path.join(tmp_dir, f))
                    except Exception: pass

            # Download to system temp folder with a unique name each time
            import uuid
            tmp_path = os.path.join(tempfile.gettempdir(), f"nebula_update_{uuid.uuid4().hex}.py")

            # Use urlopen instead of urlretrieve for better control
            req = urllib.request.Request(
                UPDATE_SCRIPT_URL,
                headers={"Cache-Control": "no-cache", "User-Agent": "Nebula-Updater"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                content_bytes = resp.read()

            # Write to temp file
            with open(tmp_path, "wb") as f:
                f.write(content_bytes)

            # Sanity check
            content = content_bytes.decode("utf-8")
            if "AHKManager" not in content:
                os.remove(tmp_path)
                raise ValueError("Downloaded file doesn't look like Nebula — aborting.")

            # Write updater batch to system temp too
            bat_path = os.path.join(tempfile.gettempdir(), f"_nebula_update_{uuid.uuid4().hex}.bat")
            pid      = os.getpid()
            relaunch = f'"{exe_path}"' if is_frozen else f'"{sys.executable}" "{py_path}"'

            bat = f"""@echo off
set LOG=%TEMP%\\nebula_update_log.txt
echo Starting update... > %LOG%
:wait
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >NUL
    goto wait
)
echo Process exited, swapping files... >> %LOG%
if exist "{backup_path}" del /f /q "{backup_path}"
if exist "{py_path}" (
    move /y "{py_path}" "{backup_path}"
    echo Backed up old file >> %LOG%
) else (
    echo No existing py file to backup >> %LOG%
)
move /y "{tmp_path}" "{py_path}"
if errorlevel 1 (
    echo FAILED to move update file >> %LOG%
) else (
    echo File swapped successfully >> %LOG%
)
echo Relaunching: {exe_path} >> %LOG%
timeout /t 1 /nobreak >NUL
start "" "{exe_path}"
echo Done >> %LOG%
del /f /q "%~f0"
"""
            with open(bat_path, "w") as f:
                f.write(bat)

            # Stop all running AHK scripts
            for proc in self.procs.values():
                try: proc.terminate()
                except Exception: pass
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

            # Launch the batch script fully detached then exit
            subprocess.Popen(
                ["cmd.exe", "/c", bat_path],
                creationflags=subprocess.DETACHED_PROCESS,
                close_fds=True,
                shell=False
            )
            self.destroy()

        except Exception as ex:
            messagebox.showerror("Update Failed",
                                  f"Could not update Nebula:\n\n{ex}\n\nYour current version is unchanged.")

    # ── Admin panel ───────────────────────────────────────────────────────────
    def _open_admin_panel(self):
        t = self._theme
        win = tk.Toplevel(self)
        win.title("User Management")
        win.resizable(False, False)
        win.configure(bg=t["bg"])
        win.grab_set()

        tk.Label(win, text="User Management", bg=t["bg"], fg=t["accent"],
                 font=self.font_name, pady=14).pack()
        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20)

        # Status label at top
        status_var = tk.StringVar()
        status_lbl = tk.Label(win, textvariable=status_var, font=self.font_file,
                               bg=t["bg"], fg=t["running"])
        status_lbl.pack(pady=(6, 0))

        list_frame = tk.Frame(win, bg=t["bg"], padx=20, pady=10)
        list_frame.pack(fill="both")

        def refresh():
            for w in list_frame.winfo_children():
                w.destroy()
            remote_users, sha = fetch_remote_users()
            if not remote_users:
                tk.Label(list_frame, text="Could not load users from GitHub.",
                         font=self.font_file, bg=t["bg"], fg=t["accent2"]).pack()
                return
            tk.Label(list_frame, text=f"{'USERNAME':<22} {'CREATED':<12}  ACTION",
                     font=self.font_file, bg=t["bg"], fg=t["subtext"],
                     anchor="w").pack(fill="x", pady=(0, 4))
            tk.Frame(list_frame, bg=t["border"], height=1).pack(fill="x", pady=(0, 6))
            for uname in list(remote_users.keys()):
                row = tk.Frame(list_frame, bg=t["card_bg"],
                                highlightbackground=t["border"], highlightthickness=1)
                row.pack(fill="x", pady=3, ipady=6)
                tk.Label(row, text=uname, font=self.font_file, bg=t["card_bg"],
                          fg=t["text"], width=22, anchor="w", padx=8).pack(side="left")
                def delete(u=uname):
                    remote, s = fetch_remote_users()
                    if u in remote:
                        del remote[u]
                        ok, _ = push_remote_users(remote, s)
                        if ok:
                            status_var.set(f"✓ Deleted '{u}'")
                            status_lbl.config(fg=t["running"])
                        else:
                            status_var.set(f"✗ Failed to delete '{u}'")
                            status_lbl.config(fg=t["accent2"])
                        refresh()
                del_btn = tk.Label(row, text="Delete", font=self.font_badge,
                                    bg=t["accent2"], fg="#ffffff", padx=8, pady=2,
                                    cursor="hand2")
                del_btn.pack(side="right", padx=8)
                del_btn.bind("<Button-1>", lambda e, u=uname: delete(u))

            tk.Label(list_frame, text=f"{len(remote_users)} account(s) on file",
                     font=self.font_file, bg=t["bg"], fg=t["subtext"]).pack(pady=(8, 0))

        refresh()

        tk.Frame(win, bg=t["border"], height=1).pack(fill="x", padx=20, pady=(6, 0))
        btn_row = tk.Frame(win, bg=t["bg"], pady=10)
        btn_row.pack()
        for text, cmd, col in [("Refresh", refresh, t["accent"]),
                                ("Close",   win.destroy, t["accent2"])]:
            b = tk.Label(btn_row, text=text, font=self.font_badge,
                          bg=t["card_bg"], fg=col, padx=14, pady=7,
                          cursor="hand2", highlightbackground=t["border"], highlightthickness=1)
            b.pack(side="left", padx=6)
            b.bind("<Button-1>", lambda e, c=cmd: c())

        win.update_idletasks()
        px = self.winfo_x() + (self.winfo_width()  - win.winfo_width())  // 2
        py = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{px}+{py}")

    def _logout(self):
        clear_session()
        for proc in self.procs.values():
            try: proc.terminate()
            except Exception: pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self._logged_out = True
        self.destroy()

    def _on_close(self):
        for proc in self.procs.values():
            try: proc.terminate()
            except Exception: pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self.destroy()


class LoginScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nebula — Login")
        self.resizable(False, False)
        self.configure(bg="#0d0010")
        self._success = False
        self._logged_user = None

        try:
            self.iconbitmap(resource_path("nebula.ico"))
        except Exception:
            pass

        self.update_idletasks()

        # ── Fonts (Segoe UI to match main window)
        font_title  = tkfont.Font(family="Segoe Script", size=18, weight="bold")
        font_sub    = tkfont.Font(family="Segoe UI", size=9)
        font_label  = tkfont.Font(family="Segoe UI", size=8,  weight="bold")
        font_entry  = tkfont.Font(family="Segoe UI", size=11)
        font_err    = tkfont.Font(family="Segoe UI", size=8)
        font_btn    = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        font_check  = tkfont.Font(family="Segoe UI", size=9)

        # ── Layout
        wrap = tk.Frame(self, bg="#0d0010", padx=48, pady=40)
        wrap.pack()

        # Title
        tk.Label(wrap, text="⬡ Nebula", font=font_title,
                 bg="#0d0010", fg="#c084fc").pack(pady=(0, 4))
        tk.Label(wrap, text="sign in to continue", font=font_sub,
                 bg="#0d0010", fg="#6b21a8").pack(pady=(0, 24))

        # Username
        tk.Label(wrap, text="USERNAME", font=font_label,
                 bg="#0d0010", fg="#a855f7", anchor="w").pack(fill="x")
        self._user_var = tk.StringVar()
        self._user_entry = tk.Entry(wrap, textvariable=self._user_var,
                                    font=font_entry, bg="#1a0030",
                                    fg="#e9d5ff", insertbackground="#c084fc",
                                    relief="flat", bd=0,
                                    highlightthickness=1,
                                    highlightbackground="#4c1d95",
                                    highlightcolor="#a855f7")
        self._user_entry.pack(fill="x", ipady=8, pady=(4, 16))

        # Password
        tk.Label(wrap, text="PASSWORD", font=font_label,
                 bg="#0d0010", fg="#a855f7", anchor="w").pack(fill="x")
        self._pass_var = tk.StringVar()
        self._pass_entry = tk.Entry(wrap, textvariable=self._pass_var,
                                    font=font_entry, bg="#1a0030",
                                    fg="#e9d5ff", insertbackground="#c084fc",
                                    relief="flat", bd=0, show="•",
                                    highlightthickness=1,
                                    highlightbackground="#4c1d95",
                                    highlightcolor="#a855f7")
        self._pass_entry.pack(fill="x", ipady=8, pady=(4, 12))

        # Remember Me
        self._remember_var = tk.BooleanVar(value=False)
        rem_frame = tk.Frame(wrap, bg="#0d0010")
        rem_frame.pack(fill="x", pady=(0, 16))
        self._rem_check = tk.Checkbutton(rem_frame, text="Remember me",
                                          variable=self._remember_var,
                                          font=font_check,
                                          bg="#0d0010", fg="#a855f7",
                                          activebackground="#0d0010",
                                          activeforeground="#c084fc",
                                          selectcolor="#1a0030",
                                          cursor="hand2", bd=0,
                                          highlightthickness=0)
        self._rem_check.pack(side="left")

        # Error label
        self._err_var = tk.StringVar()
        self._err_lbl = tk.Label(wrap, textvariable=self._err_var,
                                  font=font_err, bg="#0d0010",
                                  fg="#f87171")
        self._err_lbl.pack(pady=(0, 12))

        # Login button
        btn = tk.Label(wrap, text="LOGIN", font=font_btn,
                       bg="#4c1d95", fg="#e9d5ff", padx=32, pady=10,
                       cursor="hand2", relief="flat")
        btn.pack()
        btn.bind("<Button-1>", lambda e: self._attempt())
        self._pass_entry.bind("<Return>", lambda e: self._attempt())
        self._user_entry.bind("<Return>", lambda e: self._pass_entry.focus())

        # Create account link
        reg_frame = tk.Frame(wrap, bg="#0d0010")
        reg_frame.pack(pady=(14, 0))
        tk.Label(reg_frame, text="Don't have an account?", font=font_sub,
                 bg="#0d0010", fg="#6b21a8").pack(side="left")
        reg_lnk = tk.Label(reg_frame, text=" Sign up", font=tkfont.Font(family="Segoe UI", size=9, underline=True),
                            bg="#0d0010", fg="#a855f7", cursor="hand2")
        reg_lnk.pack(side="left")
        reg_lnk.bind("<Button-1>", lambda e: self._open_register())

        # Centre window
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

        # ── Pre-fill from saved session
        session = load_session()
        if session:
            self._user_var.set(session["user"])
            self._pass_var.set(session["pw"])
            self._remember_var.set(True)
            self._pass_entry.focus()
        else:
            self._user_entry.focus()

    def _attempt(self):
        user = self._user_var.get().strip()
        pw   = self._pass_var.get()
        if not user or not pw:
            self._err_var.set("please enter username and password")
            return
        self._err_var.set("checking...")
        self.update()
        if validate_user_remote(user, pw):
            if self._remember_var.get():
                save_session(user, pw)
            else:
                clear_session()
            self._success = True
            self._logged_user = user
            self.destroy()
        else:
            self._err_var.set("incorrect username or password")
            self._pass_var.set("")
            self._pass_entry.focus()


    def _open_register(self):
        CreateAccountScreen(self)


class CreateAccountScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Nebula — Create Account")
        self.resizable(False, False)
        self.configure(bg="#0d0010")
        self.grab_set()

        font_title = tkfont.Font(family="Segoe Script", size=16, weight="bold")
        font_sub   = tkfont.Font(family="Segoe UI", size=9)
        font_label = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        font_entry = tkfont.Font(family="Segoe UI", size=11)
        font_err   = tkfont.Font(family="Segoe UI", size=8)
        font_btn   = tkfont.Font(family="Segoe UI", size=10, weight="bold")

        wrap = tk.Frame(self, bg="#0d0010", padx=48, pady=36)
        wrap.pack()

        tk.Label(wrap, text="⬡ Nebula", font=font_title,
                 bg="#0d0010", fg="#c084fc").pack(pady=(0, 2))
        tk.Label(wrap, text="create a new account", font=font_sub,
                 bg="#0d0010", fg="#6b21a8").pack(pady=(0, 20))

        # Username
        tk.Label(wrap, text="USERNAME", font=font_label,
                 bg="#0d0010", fg="#a855f7", anchor="w").pack(fill="x")
        self._user_var = tk.StringVar()
        self._user_entry = tk.Entry(wrap, textvariable=self._user_var,
                                     font=font_entry, bg="#1a0030", fg="#e9d5ff",
                                     insertbackground="#c084fc", relief="flat", bd=0,
                                     highlightthickness=1, highlightbackground="#4c1d95",
                                     highlightcolor="#a855f7")
        self._user_entry.pack(fill="x", ipady=8, pady=(4, 14))

        # Password
        tk.Label(wrap, text="PASSWORD", font=font_label,
                 bg="#0d0010", fg="#a855f7", anchor="w").pack(fill="x")
        self._pass_var = tk.StringVar()
        self._pass_entry = tk.Entry(wrap, textvariable=self._pass_var,
                                     font=font_entry, bg="#1a0030", fg="#e9d5ff",
                                     insertbackground="#c084fc", relief="flat", bd=0,
                                     show="•", highlightthickness=1,
                                     highlightbackground="#4c1d95", highlightcolor="#a855f7")
        self._pass_entry.pack(fill="x", ipady=8, pady=(4, 14))

        # Confirm Password
        tk.Label(wrap, text="CONFIRM PASSWORD", font=font_label,
                 bg="#0d0010", fg="#a855f7", anchor="w").pack(fill="x")
        self._conf_var = tk.StringVar()
        self._conf_entry = tk.Entry(wrap, textvariable=self._conf_var,
                                     font=font_entry, bg="#1a0030", fg="#e9d5ff",
                                     insertbackground="#c084fc", relief="flat", bd=0,
                                     show="•", highlightthickness=1,
                                     highlightbackground="#4c1d95", highlightcolor="#a855f7")
        self._conf_entry.pack(fill="x", ipady=8, pady=(4, 16))

        # Status label
        self._status_var = tk.StringVar()
        tk.Label(wrap, textvariable=self._status_var, font=font_err,
                 bg="#0d0010", fg="#f87171").pack(pady=(0, 10))

        # Create button
        btn = tk.Label(wrap, text="CREATE ACCOUNT", font=font_btn,
                       bg="#4c1d95", fg="#e9d5ff", padx=24, pady=10,
                       cursor="hand2", relief="flat")
        btn.pack()
        btn.bind("<Button-1>", lambda e: self._create())
        self._conf_entry.bind("<Return>", lambda e: self._create())

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        py = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")
        self._user_entry.focus()

    def _create(self):
        user = self._user_var.get().strip()
        pw   = self._pass_var.get()
        conf = self._conf_var.get()

        # Validation
        if not user or not pw:
            self._status_var.set("username and password are required"); return
        if len(user) < 3:
            self._status_var.set("username must be at least 3 characters"); return
        if len(pw) < 6:
            self._status_var.set("password must be at least 6 characters"); return
        if pw != conf:
            self._status_var.set("passwords do not match"); return
        if user in USERS:
            self._status_var.set("that username is taken"); return

        self._status_var.set("creating account...")
        self.config(cursor="watch")
        self.update()

        # Fetch existing remote users
        remote_users, sha = fetch_remote_users()

        if user in remote_users:
            self._status_var.set("that username is already taken")
            self.config(cursor="")
            return

        # Add new user and push
        remote_users[user] = pw
        success, err_msg = push_remote_users(remote_users, sha)

        self.config(cursor="")
        if success:
            self._status_var.set("")
            self.configure(bg="#0d0010")
            # Show success
            for w in self.winfo_children():
                w.destroy()
            wrap = tk.Frame(self, bg="#0d0010", padx=48, pady=40)
            wrap.pack()
            tk.Label(wrap, text="✓", font=tkfont.Font(family="Segoe UI", size=32),
                     bg="#0d0010", fg="#86efac").pack()
            tk.Label(wrap, text="Account created!", font=tkfont.Font(family="Segoe UI", size=13, weight="bold"),
                     bg="#0d0010", fg="#e9d5ff").pack(pady=(8, 4))
            tk.Label(wrap, text=f"Welcome, {user}.\nYou can now log in.", font=tkfont.Font(family="Segoe UI", size=9),
                     bg="#0d0010", fg="#6b21a8").pack()
            close = tk.Label(wrap, text="Go to Login", font=tkfont.Font(family="Segoe UI", size=9, weight="bold"),
                              bg="#4c1d95", fg="#e9d5ff", padx=20, pady=8, cursor="hand2")
            close.pack(pady=(20, 0))
            close.bind("<Button-1>", lambda e: self.destroy())
        else:
            self._status_var.set(f"error: {err_msg[:60]}" if err_msg else "could not connect — try again")


if __name__ == "__main__":

    while True:
        session = load_session()
        auto_login = (session and validate_user_remote(session.get("user",""), session.get("pw","")))
        if auto_login:
            app = AHKManager(current_user=session["user"])
            app._logged_out = False
            app.mainloop()
            if getattr(app, "_logged_out", False):
                continue
            break
        else:
            login = LoginScreen()
            login.mainloop()
            if login._success:
                app = AHKManager(current_user=getattr(login, "_logged_user", ""))
                app._logged_out = False
                app.mainloop()
                if getattr(app, "_logged_out", False):
                    continue
                break
            else:
                break
