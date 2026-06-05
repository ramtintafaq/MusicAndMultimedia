# Hand Music OSC Project

## 1. Project Description

This is a simple interactive audio project with machine learning.

A webcam tracks one hand. The Python hand tracking script extracts:

- hand x position
- hand y position
- hand openness

These three values are sent with OSC to both Wekinator and the renderer.

Wekinator is used as the machine learning part of the project. In this version, Wekinator controls the volume from the open/close gesture.

The renderer maps the hand position directly:

- x position controls stereo pan
- y position controls pitch as fixed piano notes in one octave
- Wekinator output controls volume

The renderer creates the sound in real time. OBS captures the renderer window and audio, then streams them to MediaMTX. MediaMTX serves the stream locally to a browser.

## 2. Architecture

```text
Webcam
  |
  v
hand_tracking.py

  -> OSC /hand/features x y openness, port 12000 -> renderer.py

  -> OSC /wek/inputs x y openness, port 6448 -> Wekinator
                                                    |
                                                    v
                         OSC /wek/outputs pan pitch volume, port 12000
                                                    |
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

All communication between the software parts uses OSC.

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

## 4. Wekinator Setup

Open Wekinator and create a new project.

Use these settings:

```text
Number of inputs: 3
Number of outputs: 3
Input port: 6448
Input message: /wek/inputs
Output host: 127.0.0.1
Output port: 12000
Output message: /wek/outputs
Output type: continuous
```

Meaning of Wekinator inputs:

```text
Input 1: x position
Input 2: y position
Input 3: openness
```

Meaning of Wekinator outputs:

```text
Output 1: not used by renderer
Output 2: not used by renderer
Output 3: volume
```

All inputs and outputs should stay between `0` and `1`.

The renderer uses x and y directly for pan and pitch. This keeps open/close gestures from accidentally changing the note.

## 5. Training Wekinator

Run `hand_tracking.py` first so Wekinator receives the live hand input.

In Wekinator, record simple examples like this:

```text
Closed hand:
Output 1 = 0.5
Output 2 = 0.5
Output 3 volume = 0.0

Open hand:
Output 1 = 0.5
Output 2 = 0.5
Output 3 volume = 1.0
```

Record examples with the hand in different positions, but only change Output 3 for open and closed hands. Keep Output 1 and Output 2 around `0.5` because the renderer ignores them.

Then click `Train`. After training, click `Run`.

When Wekinator is running, moving the hand should change the sound through the renderer.

## 6. How To Run

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

The renderer listens for hand tracking and Wekinator on:

```text
127.0.0.1:12000
```

### Start Hand Tracking

Open another terminal in the project folder:

```bash
source .venv/bin/activate
python hand_tracking.py
```

The hand tracker sends OSC to Wekinator and the renderer:

```text
Wekinator: 127.0.0.1:6448
Renderer:  127.0.0.1:12000
```

### Start Wekinator

Open your Wekinator project, make sure it is trained, then click:

```text
Run
```

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

If that does not work, use HLS:

```text
http://localhost:8888/handmusic
```

HLS can have a few seconds of delay. This is normal.

## 7. OSC Messages

`hand_tracking.py` sends this message to Wekinator:

```text
/wek/inputs
payload: x, y, openness
example: /wek/inputs 0.25 0.70 0.90
port: 6448
```

`hand_tracking.py` also sends this message to `renderer.py`:

```text
/hand/features
payload: x, y, openness
example: /hand/features 0.25 0.70 0.90
port: 12000
```

Wekinator sends this message to `renderer.py`:

```text
/wek/outputs
payload: pan, pitch, volume
example: /wek/outputs 0.25 0.70 0.80
port: 12000
```

Renderer mapping:

```text
hand x in [0, 1]           -> stereo pan from left to right
hand y in [0, 1]           -> one piano note from C4 to C5
Wekinator volume in [0, 1] -> audio volume
```

## 8. Troubleshooting

### Webcam Not Detected

- Close other apps using the webcam.
- Check camera permission.
- Try changing `CAMERA_INDEX = 0` to `CAMERA_INDEX = 1` in `hand_tracking.py`.

### Wekinator Does Not Receive Input

- Start `hand_tracking.py`.
- Check that Wekinator input port is `6448`.
- Check that the input message is `/wek/inputs`.

### Renderer Does Not Receive Output

- Start `renderer.py` before starting hand tracking and before clicking `Run` in Wekinator.
- Check that hand tracking sends `/hand/features` to port `12000`.
- Check that Wekinator output port is `12000`.
- Check that the output message is `/wek/outputs`.

### No Audio

- Make sure Wekinator is trained and running.
- Make sure Output 3 is not always `0`.
- Check the system output volume.
- Make sure OBS captures the correct audio output.

### Stream Not Visible

- Start MediaMTX before OBS streaming.
- Check the OBS server URL: `rtmp://localhost/handmusic`.
- Open the browser page after OBS starts streaming.

## 9. Delivery Note

Upload only:

- source code
- `README.md`
- `requirements.txt`
- `mediamtx.yml`
- Wekinator project file or Wekinator screenshots/settings, if required
- technical report

Do not upload:

- `.venv` or `venv`
- cache folders
- large media files
- unnecessary assets
