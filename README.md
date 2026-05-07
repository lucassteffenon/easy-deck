<img width="1600" height="736" alt="easydeck" src="https://github.com/user-attachments/assets/24f7bdaf-21ec-4fa7-928a-deac5c32f9fc" />

# EasyDeck — Controle Remoto via Celular

Rode no PC → acesse do celular pelo Wi-Fi.

## Instalação rápida

```bash
pip install -r requirements.txt
python server.py
```

O terminal vai mostrar o IP. Ex:
```
Celular:    http://192.168.1.105:8888
```

Abra esse endereço no browser do celular (mesma rede Wi-Fi).

---

## Instalar como PWA (opcional)

No Android Chrome: menu → "Adicionar à tela inicial"  
No iPhone Safari: compartilhar → "Adicionar à Tela de Início"

Vira um ícone como app, sem barra do browser.

---

## Tipos de ação

| Tipo | O que faz | Exemplo de valor |
|------|-----------|-----------------|
| `script` | Executa comando shell | `python3 /home/user/script.py` |
| `hotkey` | Simula tecla (xdotool/PowerShell) | `ctrl+c` / `super+l` |
| `app` | Abre aplicativo | `firefox` / `notepad` |
| `url` | Abre no navegador do PC | `https://github.com` |
| `media` | Controle de mídia | `play_pause` / `volume_up` |
| `obs` | OBS (implemente em server.py) | `StartRecording` |
| `spotify` | Spotify via D-Bus (Linux) | `play` / `next` |

### Valores de mídia disponíveis
`play_pause` · `next_track` · `prev_track` · `volume_up` · `volume_down` · `mute`

---

## Estrutura

```
easy-deck/
├── server.py          # FastAPI — rode no PC
├── requirements.txt
├── config/
│   └── deck.json      # Configuração dos botões (auto-gerada)
└── static/
    ├── index.html     # Frontend mobile
    └── manifest.json  # PWA manifest
```

## Adicionar nova integração

Edite `server.py`, função `execute_action()`:

```python
elif t == "minha_integracao":
    return run_cmd(f"meu_comando {v}")
```

## Firewall (Linux)

Se o celular não conectar:
```bash
sudo ufw allow 8888
```

## Firewall (Windows)

Adicione regra de entrada na porta 8888 no Windows Defender Firewall.
