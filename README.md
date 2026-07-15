# Radio Dispatch System

Automated radio dispatch simulator for training and demo use. Hold **Push to Talk**, speak a radio message, and the dispatcher listens, logs the traffic, and replies with generated voice plus a written entry.

## Features

- Push-to-talk listening via the browser microphone
- Speech-to-text on the client (Web Speech API)
- Rule-based dispatch brain for common radio traffic
- Generated voice reply (browser text-to-speech)
- Live dispatch log and unit status board
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

- `Dispatch, Unit 12 is 10-8`
- `Unit 12 requesting 10-20`
- `Engine 5 on scene, structure fire, requesting backup`
- `Medic 3 transporting Code 3 to General Hospital`
- `Unit 7 returning to station, 10-7`
- `All units, traffic stop on Main Street`

## Architecture

| Layer | Role |
| --- | --- |
| `static/` | PTT UI, mic capture, speech recognition, TTS playback |
| `app/dispatch/` | Parses radio traffic and builds dispatcher replies |
| `app/storage.py` | SQLite dispatch log + unit status |
| `app/main.py` | FastAPI server and WebSocket live updates |

This is a simulation tool. It is not a replacement for live emergency communications equipment or procedures.