# Hand Music OSC System

## 1. Project Description

This project is a real-time interactive audio system controlled by one hand in front of a webcam.

The webcam is processed in Python with MediaPipe and OpenCV. The hand tracking script extracts three simple gesture features:

- horizontal hand position
- vertical hand position
- hand openness

These gesture features are sent through OSC to a separate Python renderer. The renderer maps the gestures to audio parameters:

- hand openness controls volume
- horizontal movement controls stereo panning
- vertical movement controls pitch

OBS captures the renderer audio and visualizer window, streams it to a local MediaMTX server, and MediaMTX serves the live stream to a browser page. No external streaming services are used.

## 2. Architecture Diagram

```text
Webcam
  |
  v
Entity 1: hand_tracking.py
  - MediaPipe hand landmarks
  - x, y, openness extraction
  - OSC sender
  |
  | OSC on localhost UDP port 9000
  | /hand/position, /hand/openness
  v
Entity 2: renderer.py
  - OSC receiver
  - x -> pan
  - y -> pitch
  - openness -> volume
  - real-time stereo audio output
  - minimal visualizer window
  |
  v
OBS
  - captures renderer audio
  - captures visualizer window
  - streams with RTMP to MediaMTX
  |
  v
MediaMTX
  - self-hosted local media server
  - receives rtmp://localhost/live/handmusic
  |
  v
Browser
  - opens http://localhost:8889/live/handmusic
```

The two Python entities exchange structural gesture data only through OSC. They do not use shared files, databases, REST APIs, or direct function calls.

## 3. Requirements Installation

Use a normal Python virtual environment if desired, but do not include the virtual environment in the final upload.

```bash
pip install -r requirements.txt
```

If MediaPipe installation fails, use a Python version supported by MediaPipe, such as Python 3.10, 3.11, or 3.12.

## 4. How To Run

### 1. Start MediaMTX

Install or download MediaMTX, then start it with its default configuration.

On macOS with Homebrew:

```bash
brew install mediamtx
mediamtx
```

No custom `mediamtx.yml` is required for this project.

### 2. Start the Renderer

In a terminal inside this project folder:

```bash
python renderer.py
```

The renderer listens for OSC messages on:

```text
127.0.0.1:9000
```

It produces the audio output and opens a small visualizer window called `Renderer - OBS Capture`.

### 3. Start Hand Tracking

Open a second terminal inside this project folder:

```bash
python hand_tracking.py
```

Show one hand to the webcam. Press `q` in the camera window to quit.

### 4. Configure OBS

In OBS:

1. Add a window capture source for `Renderer - OBS Capture`.
2. Add or enable the audio output source that contains the renderer sound.
3. Go to `Settings -> Stream`.
4. Set `Service` to `Custom`.
5. Set `Server` to:

```text
rtmp://localhost/live/handmusic
```

6. Leave the stream key empty.
7. Click `Start Streaming`.

### 5. Open the Browser Stream Page

After OBS starts streaming, open this URL in a browser:

```text
http://localhost:8889/live/handmusic
```

This is the MediaMTX WebRTC playback page.

If WebRTC playback has problems, try the HLS page instead:

```text
http://localhost:8888/live/handmusic
```

## 5. OSC Message Documentation

All OSC messages are sent from `hand_tracking.py` to `renderer.py` on localhost UDP port `9000`.

```text
/hand/position
payload: x, y
range: x in [0, 1], y in [0, 1]
meaning: x is left-to-right position, y is bottom-to-top position
mapping: x controls stereo pan, y controls pitch
```

```text
/hand/openness
payload: openness
range: openness in [0, 1]
meaning: 0 is closed hand, 1 is open hand
mapping: openness controls volume
```

```text
/hand/features
payload: x, y, openness
range: all values in [0, 1]
meaning: optional combined message for the same three features
status: supported by renderer.py, disabled by default in hand_tracking.py
```

## 6. Troubleshooting

### Webcam Not Detected

- Check that no other application is using the webcam.
- Check camera permissions in the operating system.
- If needed, change `CAMERA_INDEX = 0` in `hand_tracking.py` to `1`.

### No Audio

- Start `renderer.py` before `hand_tracking.py`.
- Check the system audio output device.
- Make sure OBS is capturing the same audio output device.
- If the hand is not visible, the renderer fades the volume to zero after a short timeout.

### OSC Not Received

- Make sure both scripts use the same port: `9000`.
- Start both scripts on the same computer.
- Check that `hand_tracking.py` prints changing `x`, `y`, and `openness` values.
- Check that `renderer.py` prints changing pitch, volume, and pan values.

### OBS Stream Not Visible

- Make sure MediaMTX is running before starting OBS streaming.
- In OBS, use `Custom` service and `rtmp://localhost/live/handmusic`.
- Make sure the browser URL is `http://localhost:8889/live/handmusic`.
- If WebRTC does not open, try `http://localhost:8888/live/handmusic`.

## 7. Delivery Note

For the project delivery, upload only the source code, this `README.md`, the technical report, and `requirements.txt`.

Do not upload:

- Python virtual environments
- cache folders
- `.DS_Store`
- IDE folders
- large media files
- unnecessary assets
