"""
MacroDeck Server — Roda no PC, recebe comandos do celular via HTTP
Execute: python server.py
Acesse no celular: http://<IP-DO-PC>:7777
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
STATIC_DIR = BASE_DIR / "static"
CONFIG_FILE = CONFIG_DIR / "deck.json"
SYSTEM = platform.system()  # Windows | Linux | Darwin

CONFIG_DIR.mkdir(exist_ok=True)

app = FastAPI(title="MacroDeck Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ───────────────────────────────────────────────────────────────────
class Action(BaseModel):
    type: str   # script | hotkey | app | url | obs | spotify | media
    value: str

class Button(BaseModel):
    id: str
    label: str
    icon: str
    color: str
    action: Action

class Page(BaseModel):
    id: str
    name: str
    buttons: list[Button]

class DeckConfig(BaseModel):
    pages: list[Page]
    currentPage: str

class ExecuteRequest(BaseModel):
    action: Action

# ─── Config helpers ───────────────────────────────────────────────────────────
def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default_config()

def save_config(data: dict) -> bool:
    try:
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[ERRO] Salvar config: {e}")
        return False

def default_config() -> dict:
    btns_win = [
        {"id":"1","label":"Bloco de notas","icon":"📝","color":"#1a1a2e","action":{"type":"app","value":"notepad"}},
        {"id":"2","label":"Calculadora","icon":"🔢","color":"#0d1b2a","action":{"type":"app","value":"calc"}},
        {"id":"3","label":"Volume +","icon":"🔊","color":"#1a2e1a","action":{"type":"media","value":"volume_up"}},
        {"id":"4","label":"Volume -","icon":"🔇","color":"#2e1a1a","action":{"type":"media","value":"volume_down"}},
        {"id":"5","label":"Play/Pause","icon":"⏯","color":"#2e2a0a","action":{"type":"media","value":"play_pause"}},
        {"id":"6","label":"Próxima faixa","icon":"⏭","color":"#0a1a2e","action":{"type":"media","value":"next_track"}},
        {"id":"7","label":"Lock Screen","icon":"🔒","color":"#1a0a2e","action":{"type":"script","value":"rundll32.exe user32.dll,LockWorkStation"}},
        {"id":"8","label":"Screenshot","icon":"📸","color":"#0a2e1a","action":{"type":"hotkey","value":"PrintScreen"}},
    ]
    btns_linux = [
        {"id":"1","label":"Terminal","icon":"💻","color":"#1a1a2e","action":{"type":"app","value":"x-terminal-emulator"}},
        {"id":"2","label":"Navegador","icon":"🌐","color":"#0d1b2a","action":{"type":"app","value":"xdg-open https://google.com"}},
        {"id":"3","label":"Volume +","icon":"🔊","color":"#1a2e1a","action":{"type":"script","value":"pactl set-sink-volume @DEFAULT_SINK@ +10%"}},
        {"id":"4","label":"Volume -","icon":"🔇","color":"#2e1a1a","action":{"type":"script","value":"pactl set-sink-volume @DEFAULT_SINK@ -10%"}},
        {"id":"5","label":"Play/Pause","icon":"⏯","color":"#2e2a0a","action":{"type":"media","value":"play_pause"}},
        {"id":"6","label":"Próxima faixa","icon":"⏭","color":"#0a1a2e","action":{"type":"media","value":"next_track"}},
        {"id":"7","label":"Lock Screen","icon":"🔒","color":"#1a0a2e","action":{"type":"script","value":"loginctl lock-session"}},
        {"id":"8","label":"Screenshot","icon":"📸","color":"#0a2e1a","action":{"type":"script","value":"scrot ~/screenshot-$(date +%s).png"}},
    ]
    buttons = btns_win if SYSTEM == "Windows" else btns_linux
    return {
        "pages": [{"id": "main", "name": "Principal", "buttons": buttons}],
        "currentPage": "main"
    }

# ─── Action executor ──────────────────────────────────────────────────────────
def run_cmd(cmd: str, shell: bool = True) -> dict:
    try:
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip() or result.stderr.strip() or "OK"
        return {"ok": result.returncode == 0, "output": output}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Timeout (10s)"}
    except Exception as e:
        return {"ok": False, "output": str(e)}

def open_app(value: str) -> dict:
    if SYSTEM == "Windows":
        return run_cmd(f'start "" {value}')
    elif SYSTEM == "Darwin":
        return run_cmd(f'open -a "{value}"')
    else:
        return run_cmd(f'{value} &')

def media_action(value: str) -> dict:
    """Controle de mídia cross-platform"""
    if SYSTEM == "Windows":
        key_map = {
            "play_pause": "0xB3",
            "next_track": "0xB0",
            "prev_track": "0xB1",
            "volume_up":  "0xAF",
            "volume_down":"0xAE",
            "mute":       "0xAD",
        }
        key = key_map.get(value)
        if not key:
            return {"ok": False, "output": f"Ação de mídia desconhecida: {value}"}
        ps = f"$wsh = New-Object -ComObject wscript.shell; $wsh.SendKeys([char]{key})"
        return run_cmd(f'powershell -Command "{ps}"')

    elif SYSTEM == "Linux":
        xdotool_map = {
            "play_pause": "XF86AudioPlay",
            "next_track": "XF86AudioNext",
            "prev_track": "XF86AudioPrev",
            "volume_up":  "XF86AudioRaiseVolume",
            "volume_down":"XF86AudioLowerVolume",
            "mute":       "XF86AudioMute",
        }
        key = xdotool_map.get(value)
        if not key:
            return {"ok": False, "output": f"Ação desconhecida: {value}"}
        return run_cmd(f"xdotool key {key}")

    elif SYSTEM == "Darwin":
        applescript_map = {
            "play_pause": 'tell application "Music" to playpause',
            "next_track": 'tell application "Music" to next track',
            "prev_track": 'tell application "Music" to previous track',
        }
        script = applescript_map.get(value, "")
        if script:
            return run_cmd(f"osascript -e '{script}'")
        return {"ok": False, "output": f"Sem suporte para {value} no macOS"}

    return {"ok": False, "output": "Sistema não suportado"}

def execute_action(action: Action) -> dict:
    t, v = action.type, action.value

    if t == "script":
        return run_cmd(v)

    elif t == "hotkey":
        if SYSTEM == "Windows":
            ps = f"$wsh = New-Object -ComObject wscript.shell; $wsh.SendKeys('{v}')"
            return run_cmd(f'powershell -Command "{ps}"')
        elif SYSTEM == "Linux":
            return run_cmd(f"xdotool key {v}")
        elif SYSTEM == "Darwin":
            return run_cmd(f"osascript -e 'tell application \"System Events\" to key code {v}'")

    elif t == "app":
        return open_app(v)

    elif t == "url":
        if SYSTEM == "Windows":
            return run_cmd(f'start "" "{v}"')
        elif SYSTEM == "Darwin":
            return run_cmd(f'open "{v}"')
        else:
            return run_cmd(f'xdg-open "{v}"')

    elif t == "media":
        return media_action(v)

    elif t == "obs":
        # Requer obs-websocket + lib obsws-python
        return {"ok": False, "output": "OBS: configure obsws-python e adapte em server.py"}

    elif t == "spotify":
        if SYSTEM == "Linux":
            dbus_map = {
                "play":  "PlayPause",
                "pause": "PlayPause",
                "next":  "Next",
                "prev":  "Previous",
            }
            method = dbus_map.get(v, v)
            cmd = (
                f"dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify "
                f"/org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.{method}"
            )
            return run_cmd(cmd)
        return {"ok": False, "output": "Spotify via D-Bus: apenas Linux"}

    elif t == "none":
        return {"ok": True, "output": "Nenhuma ação configurada"}

    return {"ok": False, "output": f"Tipo desconhecido: {t}"}

# ─── Rotas API ────────────────────────────────────────────────────────────────
@app.get("/api/config")
def get_config():
    return load_config()

@app.post("/api/config")
def post_config(data: DeckConfig):
    ok = save_config(data.model_dump())
    if not ok:
        raise HTTPException(500, "Erro ao salvar configuração")
    return {"ok": True}

@app.post("/api/execute")
def post_execute(req: ExecuteRequest):
    result = execute_action(req.action)
    print(f"[EXEC] {req.action.type}:{req.action.value} → {result}")
    return result

@app.get("/api/system")
def get_system():
    import socket
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "127.0.0.1"
    return {"system": SYSTEM, "hostname": hostname, "ip": ip}

# ─── Frontend estático ────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import socket

    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    ip = get_local_ip()
    port = 8888
    print(f"""
╔══════════════════════════════════════╗
║         MacroDeck Server             ║
╠══════════════════════════════════════╣
║  PC local:   http://localhost:{port}   ║
║  Celular:    http://{ip}:{port}  ║
║                                      ║
║  Certifique-se que o celular está    ║
║  na mesma rede Wi-Fi!                ║
╚══════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
