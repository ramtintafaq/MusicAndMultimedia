# Hand Music OSC Project

## 1. Project Description

This is a simple interactive audio project.

A webcam tracks one hand. The Python hand tracking script extracts:

- hand x position
- hand y position
- hand openness

These values are sent with OSC to another Python script. The second script creates sound in real time:

- openness controls volume
- x position controls stereo pan
- y position controls pitch

OBS captures the renderer window and audio, then streams them to MediaMTX. MediaMTX serves the stream locally to a browser.

## 2. Architecture

```text
Webcam
  |
  v
hand_tracking.py
  |
  | OSC messages on 127.0.0.1:9000
  v
renderer.py
  |
  v
OBS
  |
  v
MediaMTX
  |
  v
Browser
```

The two Python scripts communicate only with OSC.

## 3. Install Requirements

Create a virtual environment first. This avoids installing packages directly into the system Python.

```bash
python3.9 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If MediaPipe does not install, use Python 3.9, 3.10, 3.11, or 3.12.

If the virtual environment was created with Python 3.13, delete it and create it again with Python 3.9:

```bash
rm -rf .venv
python3.9 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 4. How To Run

### Start MediaMTX

Install MediaMTX and run it with the small config file:

```bash
mediamtx mediamtx.yml
```

The config file allows MediaMTX to accept the stream path used by OBS.

### Start the Renderer

In the project folder:

```bash
source .venv/bin/activate
python renderer.py
```

This opens a small visual window and starts the audio renderer.

### Start Hand Tracking

Open another terminal in the project folder:

```bash
source .venv/bin/activate
python hand_tracking.py
```

Show one hand to the webcam.

### Configure OBS

In OBS:

1. Capture the window called `Renderer - OBS Capture`.
2. Capture the computer audio output.
3. Go to `Settings -> Stream`.
4. Set service to `Custom`.
5. Set server to:

```text
rtmp://localhost/handmusic
```

6. Leave the stream key empty.
7. Start streaming.

### Open Browser Playback

Open:

```text
http://localhost:8889/handmusic
```

If that does not work, try:

```text
http://localhost:8888/handmusic
```

## 5. OSC Messages

`hand_tracking.py` sends these messages to `renderer.py`.

```text
/hand/position
payload: x, y
example: /hand/position 0.25 0.70
meaning: hand position
```

```text
/hand/openness
payload: openness
example: /hand/openness 0.90
meaning: how open the hand is
```

All values are between `0` and `1`.

## 6. Troubleshooting

### Webcam Not Detected

- Close other apps using the webcam.
- Check camera permission.
- Try changing `CAMERA_INDEX = 0` to `CAMERA_INDEX = 1` in `hand_tracking.py`.

### No Audio

- Start `renderer.py` first.
- Check the system output volume.
- Make sure OBS captures the correct audio output.

### OSC Not Received

- Both scripts must use port `9000`.
- Start both scripts on the same computer.
- Check that the terminal prints changing hand values.

### Stream Not Visible

- Start MediaMTX before OBS streaming.
- Check the OBS server URL: `rtmp://localhost/handmusic`.
- Open the browser page after OBS starts streaming.

## 7. Delivery Note

Upload only:

- source code
- `README.md`
- `requirements.txt`
- technical report

Do not upload:

- `.venv` or `venv`
- cache folders
- large media files
- unnecessary assets
