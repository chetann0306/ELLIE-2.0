import os
import platform
import shutil
import subprocess
import eel
import pygame
import webbrowser
import urllib.parse
import requests
import re
from backend.config import ASSISTANT_NAME

try:
    pygame.mixer.init()
except Exception:
    pass


@eel.expose
def play_assistant_sound():
    try:
        sound_file = os.path.join(os.path.dirname(__file__), "..", "frontend", "assets", "audio", "start_sound.mp3")
        sound_file = os.path.abspath(sound_file)
        if os.path.exists(sound_file):
            pygame.mixer.music.load(sound_file)
            pygame.mixer.music.play()
        else:
            print("Assistant start sound not found:", sound_file)
    except Exception as e:
        print("play_assistant_sound error:", e)


def _run_nonblocking(cmd, use_shell=False):
    try:
        if use_shell:
            subprocess.Popen(cmd, shell=True)
        else:
            if isinstance(cmd, (list, tuple)):
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, ""
    except Exception as e:
        return False, str(e)


def openCommand(query):
    """
    Attempt to open an application described by `query`.
    Returns { status: "opened"|"failed", target: "<target>", error: "<msg>" }.
    This function will speak "Opening <target>" (via backend.command.speak) before attempting to open.
    """
    try:
        from backend.command import speak
    except Exception:
        def speak(text, run_async=True):
            print("TTS unavailable; would say:", text)

    if not query or not isinstance(query, str):
        return {"status": "failed", "target": None, "error": "invalid query"}

    original = query.strip()
    lowered = original.lower()

    assistant_lower = ASSISTANT_NAME.lower() if ASSISTANT_NAME else ""
    if assistant_lower and assistant_lower in lowered:
        lowered = lowered.replace(assistant_lower, " ").strip()

    # Added YouTube auto-play 
    if "youtube" in lowered and "play" in lowered:
        try:
            idx = lowered.find("play")
            search_query = lowered[idx + len("play"):].replace("on youtube", "").strip()
            if not search_query:
                speak("What do you want me to play on YouTube?", run_async=True)
                return {"status": "failed", "target": "YouTube", "error": "no search query"}

            speak(f"Playing {search_query} on YouTube", run_async=True)
            encoded_query = urllib.parse.quote_plus(search_query)

            search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
            html = requests.get(search_url).text
            video_ids = re.findall(r"watch\?v=(\S{11})", html)

            if not video_ids:
                speak("I couldn’t find that video on YouTube.", run_async=True)
                return {"status": "failed", "target": "YouTube", "error": "no video found"}

            video_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
            webbrowser.open(video_url)
            return {"status": "opened", "target": f"YouTube - {search_query}", "error": ""}

        except Exception as e:
            speak("Something went wrong while playing on YouTube.", run_async=True)
            return {"status": "failed", "target": "YouTube", "error": str(e)}

    target = None
    for kw in ("open ", "launch ", "start "):
        if kw in lowered:
            idx = lowered.find(kw)
            target = lowered[idx + len(kw):].strip()
            break

    if not target:
        return {"status": "failed", "target": None, "error": "no target found"}

    for p in ("please ", "the ", "a "):
        if target.startswith(p):
            target = target[len(p):].strip()

    APP_ALIASES = {
        "notepad": {"windows": "notepad.exe", "mac": "TextEdit", "linux": "gedit"},
        "calculator": {"windows": "calc.exe", "mac": "Calculator", "linux": "gnome-calculator"},
        "chrome": {"windows": "chrome", "mac": "Google Chrome", "linux": "google-chrome"},
        "edge": {"windows": "msedge", "mac": "Microsoft Edge", "linux": "microsoft-edge"},
        "vscode": {"windows": "code", "mac": "Visual Studio Code", "linux": "code"},
        "youtube": {"windows": "https://www.youtube.com", "mac": "https://www.youtube.com", "linux": "https://www.youtube.com"},
        "spotify": {"windows": "https://open.spotify.com", "mac": "https://open.spotify.com", "linux": "https://open.spotify.com"},
        "whatsapp": {"windows": "https://web.whatsapp.com", "mac": "https://web.whatsapp.com", "linux": "https://web.whatsapp.com"},
    }

    matched_alias = None
    resolved = None
    t = target.lower()
    for alias in APP_ALIASES:
        if alias in t:
            resolved = APP_ALIASES[alias]
            matched_alias = alias
            break

    try:
        speak(f"Opening {matched_alias or target}", run_async=True)
    except Exception:
        print("Could not run speak before opening.")

    host = platform.system().lower()
    try:
        if resolved:
            if host.startswith("windows"):
                cmd = resolved.get("windows")
                if not cmd:
                    return {"status": "failed", "target": target, "error": "no mapping for windows"}
                if shutil.which(cmd):
                    ok, err = _run_nonblocking([cmd])
                else:
                    ok, err = _run_nonblocking(f'start "" "{cmd}"', use_shell=True)
                if not ok:
                    return {"status": "failed", "target": matched_alias or target, "error": err}
                return {"status": "opened", "target": matched_alias or target, "error": ""}
            elif "darwin" in host:
                cmd = resolved.get("mac")
                if not cmd:
                    return {"status": "failed", "target": target, "error": "no mapping for mac"}
                ok, err = _run_nonblocking(['open', '-a', cmd])
                if not ok:
                    return {"status": "failed", "target": matched_alias or target, "error": err}
                return {"status": "opened", "target": matched_alias or target, "error": ""}
            else:
                cmd = resolved.get("linux") or resolved.get("windows") or resolved.get("mac")
                if not cmd:
                    return {"status": "failed", "target": target, "error": "no mapping for linux"}
                if shutil.which(cmd):
                    ok, err = _run_nonblocking([cmd])
                    if not ok:
                        return {"status": "failed", "target": matched_alias or target, "error": err}
                else:
                    rc = os.system(f'xdg-open "{cmd}" >/dev/null 2>&1')
                    if rc != 0:
                        ok, err = _run_nonblocking(cmd)
                        if not ok:
                            return {"status": "failed", "target": matched_alias or target, "error": err}
                return {"status": "opened", "target": matched_alias or target, "error": ""}
        else:

            if host.startswith("windows"):
                ok, err = _run_nonblocking(f'start "" "{target}"', use_shell=True)
                if not ok:
                    return {"status": "failed", "target": target, "error": err}
                return {"status": "opened", "target": target, "error": ""}
            elif "darwin" in host:
                ok, err = _run_nonblocking(['open', '-a', target])
                if not ok:
                    return {"status": "failed", "target": target, "error": err}
                return {"status": "opened", "target": target, "error": ""}
            else:
                rc = os.system(f'xdg-open "{target}" >/dev/null 2>&1')
                if rc == 0:
                    return {"status": "opened", "target": target, "error": ""}
                ok, err = _run_nonblocking(target)
                if not ok:
                    return {"status": "failed", "target": target, "error": err}
                return {"status": "opened", "target": target, "error": ""}
    except Exception as e:
        return {"status": "failed", "target": target, "error": str(e)}
