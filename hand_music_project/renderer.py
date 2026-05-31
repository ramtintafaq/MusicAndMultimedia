"""
Entity 2: audio renderer.

This script receives OSC outputs from Wekinator and turns them into sound.

OSC input from Wekinator:
    127.0.0.1:12000
    /wek/outputs  pan pitch volume

Mapping:
    output 1 -> stereo pan
    output 2 -> pitch
    output 3 -> volume
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
OSC_PORT = 12000

SAMPLE_RATE = 44100
BLOCK_SIZE = 512


# These values are updated when Wekinator sends OSC outputs.
pan_control = 0.5
pitch_control = 0.5
volume_control = 0.0

pitch = 440.0
volume = 0.0
pan = 0.0

phase = 0.0
last_osc_time = 0.0


def clamp(value):
    return max(0.0, min(1.0, float(value)))


def update_audio_values():
    """Convert Wekinator outputs in [0, 1] into audio parameters."""
    global pitch, volume, pan

    volume = volume_control
    pan = pan_control * 2.0 - 1.0
    pitch = 220.0 + pitch_control * 660.0


def receive_wekinator_outputs(address, *args):
    """OSC message: /wek/outputs pan pitch volume"""
    global volume_control, pan_control, pitch_control, last_osc_time

    if len(args) < 3:
        return

    pan_control = clamp(args[0])
    pitch_control = clamp(args[1])
    volume_control = clamp(args[2])
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
    dispatcher.map("/wek/outputs", receive_wekinator_outputs)

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

    draw_bar(image, f"Pitch: {pitch:.0f} Hz", pitch_control, 95, (255, 170, 40))
    draw_bar(image, f"Volume: {volume:.2f}", volume, 145, (80, 220, 120))
    draw_bar(image, f"Pan: {pan:.2f}", pan_control, 195, (120, 180, 255))

    hand_x = int(150 + pan_control * 360)
    hand_y = int(320 - pitch_control * 80)
    cv2.rectangle(image, (150, 240), (510, 320), (90, 90, 90), 1)
    cv2.circle(image, (hand_x, hand_y), 8, (0, 255, 255), -1)
    cv2.putText(image, "ML output", (30, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1)

    cv2.imshow("Renderer - OBS Capture", image)
    return cv2.waitKey(16) & 0xFF != ord("q")


def main():
    server = start_osc_server()

    print(f"Renderer listening for Wekinator OSC on {OSC_IP}:{OSC_PORT}")
    print("OSC message: /wek/outputs pan pitch volume")
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
