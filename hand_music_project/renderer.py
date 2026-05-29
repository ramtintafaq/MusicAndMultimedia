"""
Entity 2: audio renderer.

This script receives OSC data from hand_tracking.py and turns it into sound.

OSC input on 127.0.0.1:9000:
    /hand/position  x y
    /hand/openness  openness

Mapping:
    x        -> stereo pan
    y        -> pitch
    openness -> volume
"""

import math
import threading
import time

import cv2
import numpy as np
import sounddevice as sd
from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher


OSC_IP = "127.0.0.1"
OSC_PORT = 9000

SAMPLE_RATE = 44100
BLOCK_SIZE = 512


# These values are updated when OSC messages arrive.
x = 0.5
y = 0.5
openness = 0.0

pitch = 440.0
volume = 0.0
pan = 0.0

phase = 0.0
last_osc_time = 0.0


def clamp(value):
    return max(0.0, min(1.0, float(value)))


def update_audio_values():
    """Convert hand values in [0, 1] into audio parameters."""
    global pitch, volume, pan

    pitch = 220.0 + y * 660.0
    volume = openness
    pan = x * 2.0 - 1.0


def receive_position(address, received_x, received_y):
    """OSC message: /hand/position x y"""
    global x, y, last_osc_time

    x = clamp(received_x)
    y = clamp(received_y)
    last_osc_time = time.time()
    update_audio_values()


def receive_openness(address, received_openness):
    """OSC message: /hand/openness openness"""
    global openness, last_osc_time

    openness = clamp(received_openness)
    last_osc_time = time.time()
    update_audio_values()


def audio_callback(outdata, frames, time_info, status):
    """This function is called continuously by sounddevice."""
    global phase

    if status:
        print(status)

    current_volume = volume

    # If the hand tracker stops sending data, fade to silence.
    if time.time() - last_osc_time > 1.0:
        current_volume = 0.0

    t = (np.arange(frames) + phase) / SAMPLE_RATE
    wave = np.sin(2.0 * math.pi * pitch * t) * current_volume * 0.25

    # Convert pan from [-1, 1] to simple left/right gains.
    right_gain = (pan + 1.0) / 2.0
    left_gain = 1.0 - right_gain

    outdata[:, 0] = wave * left_gain
    outdata[:, 1] = wave * right_gain

    phase += frames
    phase = phase % SAMPLE_RATE


def start_osc_server():
    dispatcher = Dispatcher()
    dispatcher.map("/hand/position", receive_position)
    dispatcher.map("/hand/openness", receive_openness)

    server = osc_server.ThreadingOSCUDPServer((OSC_IP, OSC_PORT), dispatcher)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def draw_bar(image, label, value, top, color):
    value = clamp(value)
    x0 = 150
    y0 = top
    width = 360
    height = 24

    cv2.putText(image, label, (30, top + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1)
    cv2.rectangle(image, (x0, y0), (x0 + width, y0 + height), (80, 80, 80), 1)
    cv2.rectangle(image, (x0, y0), (x0 + int(width * value), y0 + height), color, -1)


def draw_window():
    """Small visual window for OBS capture."""
    image = np.zeros((360, 560, 3), dtype=np.uint8)
    image[:] = (25, 25, 25)

    cv2.putText(image, "Hand Music Renderer", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2)

    draw_bar(image, f"Pitch: {pitch:.0f} Hz", (pitch - 220.0) / 660.0, 95, (255, 170, 40))
    draw_bar(image, f"Volume: {volume:.2f}", volume, 145, (80, 220, 120))
    draw_bar(image, f"Pan: {pan:.2f}", (pan + 1.0) / 2.0, 195, (120, 180, 255))

    hand_x = int(150 + x * 360)
    hand_y = int(320 - y * 80)
    cv2.rectangle(image, (150, 240), (510, 320), (90, 90, 90), 1)
    cv2.circle(image, (hand_x, hand_y), 8, (0, 255, 255), -1)
    cv2.putText(image, "Hand position", (30, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1)

    cv2.imshow("Renderer - OBS Capture", image)
    return cv2.waitKey(16) & 0xFF != ord("q")


def main():
    server = start_osc_server()

    print(f"Renderer listening for OSC on {OSC_IP}:{OSC_PORT}")
    print("Press q in the visual window to quit.")

    try:
        with sd.OutputStream(
            channels=2,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            callback=audio_callback,
        ):
            while draw_window():
                pass
    finally:
        server.shutdown()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
