# Maritime Coast Radio Simulator

**Version 1.2.0**

Automated maritime radio simulator for training and demo use. Hold **Push to Talk**, speak a VHF message, and the coast station listens, logs the traffic, and replies with generated voice plus a written entry.

## Maritime procedures

| Call | Meaning | System response |
| --- | --- | --- |
| **Mayday** | Distress — threat to life | Urgent acknowledgement and coordination |
| **Pan Pan Pan** | Urgency — immediate attention, not life-threatening | Urgent acknowledgement, request details |
| **Sécurité / Securitay** | Safety broadcast | Logged only — **no voice reply** |
| **Unintelligible traffic** | Broken or unreadable transmission | *"Vessel calling, please repeat."* |
| **Bluff Fishermans Radio — departing** | Vessel leaving port | Ask number of persons on board |
| **Bluff Fishermans Radio — returning** | Vessel back in port | Acknowledge return |

## Features

- Push-to-talk listening via the browser microphone
- Speech-to-text on the client (Web Speech API)
- Rule-based maritime coast-station brain
- Generated voice reply (browser text-to-speech)
- Live traffic log and vessel status board
- Optional text fallback if speech recognition is unavailable

## Requirements

- Python 3.10+
- A Chromium-based browser is recommended (Chrome / Edge) for best speech support
- Microphone permission when prompted

## Quick start

```powershell
cd C:\Users\Alex\radio-dispatch
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Try these phrases

- `Mayday Mayday Mayday, this is fishing vessel Blue Horizon, taking on water`
- `Pan Pan Pan, this is yacht Serenity, disabled near harbour entrance`
- `Securitay, submerged log reported near channel marker 12`
- `This is FV Ocean Star, Bluff Fishermans Radio, back in port`
- `Bluff Fishermans Radio, this is Southern Cross, departing Bluff harbour`
- `static` or `[unintelligible]` — triggers *"Vessel calling, please repeat."*

## Architecture

| Layer | Role |
| --- | --- |
| `static/` | PTT UI, mic capture, speech recognition, TTS playback |
| `app/dispatch/` | Parses maritime traffic and builds coast-station replies |
| `app/storage.py` | SQLite traffic log + vessel status |
| `app/main.py` | FastAPI server and WebSocket live updates |

This is a simulation tool. It is not a replacement for live maritime emergency communications equipment or procedures.