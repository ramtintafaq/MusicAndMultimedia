"""
Entity 2: OSC receiver, real-time audio renderer, and minimal visualizer.

OSC messages received on 127.0.0.1:9000:
    /hand/position  x y
    /hand/openness  openness
    /hand/features  x y openness

Mappings:
    x in [0, 1]         -> pan in [-1, 1]
    y in [0, 1]         -> frequency in [220, 880] Hz
    openness in [0, 1]  -> volume in [0, 1]
"""

import math
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np
import sounddevice as sd
from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher


OSC_IP = "127.0.0.1"
OSC_PORT = 9000

SAMPLE_RATE = 44100
BLOCK_SIZE = 512
MIN_FREQUENCY = 220.0
MAX_FREQUENCY = 880.0
MAX_AMPLITUDE = 0.25
SMOOTHING = 0.08
OSC_TIMEOUT_SECONDS = 1.0


@dataclass
class GestureState:
    x: float = 0.5
    y: float = 0.5
    openness: float = 0.0
    frequency: float = 440.0
    volume: float = 0.0
    pan: float = 0.0
    last_message_time: float = 0.0


state = GestureState()
state_lock = threading.Lock()

current_frequency = 440.0
current_volume = 0.0
current_pan = 0.0
phase = 0.0
last_print_time = 0.0


def clamp(value, minimum=0.0, maximum=1.0):
    """Keep a numeric value inside a fixed range."""
    return max(minimum, min(maximum, value))


def map_value(value, in_min, in_max, out_min, out_max):
    """Linearly map one range to another range."""
    normalized = (value - in_min) / (in_max - in_min)
    return out_min + normalized * (out_max - out_min)


def update_from_gesture(x=None, y=None, openness=None):
    """Update gesture values and recompute the audio parameters."""
    global last_print_time

    with state_lock:
        if x is not None:
            state.x = clamp(float(x))
        if y is not None:
            state.y = clamp(float(y))
        if openness is not None:
            state.openness = clamp(float(openness))

        state.pan = map_value(state.x, 0.0, 1.0, -1.0, 1.0)
        state.frequency = map_value(
            state.y,
            0.0,
            1.0,
            MIN_FREQUENCY,
            MAX_FREQUENCY,
        )
        state.volume = state.openness
        state.last_message_time = time.monotonic()

        now = state.last_message_time
        if now - last_print_time >= 1.0:
            print(
                f"pitch={state.frequency:.1f} Hz, "
                f"volume={state.volume:.2f}, "
                f"pan={state.pan:.2f}"
            )
            last_print_time = now


def handle_position(address, *args):
    """Handle /hand/position with payload: x, y."""
    if len(args) >= 2:
        update_from_gesture(x=args[0], y=args[1])


def handle_openness(address, *args):
    """Handle /hand/openness with payload: openness."""
    if len(args) >= 1:
        update_from_gesture(openness=args[0])


def handle_features(address, *args):
    """Handle /hand/features with payload: x, y, openness."""
    if len(args) >= 3:
        update_from_gesture(x=args[0], y=args[1], openness=args[2])


def audio_callback(outdata, frames, time_info, status):
    """Generate a stereo sine wave from the latest OSC-controlled values."""
    global current_frequency, current_volume, current_pan, phase

    if status:
        print(status)

    with state_lock:
        target_frequency = state.frequency
        target_pan = state.pan
        target_volume = state.volume
        last_message_age = time.monotonic() - state.last_message_time

    # If OSC stops arriving, fade out instead of leaving a stuck tone.
    if last_message_age > OSC_TIMEOUT_SECONDS:
        target_volume = 0.0

    current_frequency += (target_frequency - current_frequency) * SMOOTHING
    current_volume += (target_volume - current_volume) * SMOOTHING
    current_pan += (target_pan - current_pan) * SMOOTHING

    sample_index = np.arange(frames)
    phase_increment = current_frequency / SAMPLE_RATE
    phases = (phase + sample_index * phase_increment) % 1.0
    wave = np.sin(2.0 * np.pi * phases) * current_volume * MAX_AMPLITUDE
    phase = (phase + frames * phase_increment) % 1.0

    # Constant-power pan: -1 is left, 0 is center, 1 is right.
    pan_angle = (current_pan + 1.0) * math.pi / 4.0
    left_gain = math.cos(pan_angle)
    right_gain = math.sin(pan_angle)

    outdata[:, 0] = wave * left_gain
    outdata[:, 1] = wave * right_gain


def draw_bar(image, label, value, top, color):
    """Draw one horizontal value bar in the visualizer."""
    left = 170
    width = 390
    height = 22

    cv2.putText(
        image,
        label,
        (40, top + 17),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (230, 230, 230),
        1,
    )
    cv2.rectangle(image, (left, top), (left + width, top + height), (70, 70, 70), 1)
    cv2.rectangle(
        image,
        (left, top),
        (left + int(width * clamp(value)), top + height),
        color,
        cv2.FILLED,
    )


def draw_visualizer():
    """Create a simple window that OBS can capture."""
    with state_lock:
        snapshot = GestureState(**state.__dict__)

    image = np.zeros((420, 640, 3), dtype=np.uint8)
    image[:] = (18, 18, 18)

    active = time.monotonic() - snapshot.last_message_time <= OSC_TIMEOUT_SECONDS
    status_text = "OSC active" if active else "Waiting for OSC"
    status_color = (0, 220, 120) if active else (0, 180, 255)

    cv2.putText(
        image,
        "Hand Music Renderer",
        (40, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (245, 245, 245),
        2,
    )
    cv2.putText(
        image,
        status_text,
        (430, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        status_color,
        1,
    )

    frequency_norm = map_value(
        snapshot.frequency,
        MIN_FREQUENCY,
        MAX_FREQUENCY,
        0.0,
        1.0,
    )
    pan_norm = (snapshot.pan + 1.0) / 2.0

    draw_bar(image, f"Pitch {snapshot.frequency:5.1f} Hz", frequency_norm, 95, (255, 170, 40))
    draw_bar(image, f"Volume {snapshot.volume:4.2f}", snapshot.volume, 145, (80, 220, 120))
    draw_bar(image, f"Pan {snapshot.pan:5.2f}", pan_norm, 195, (120, 180, 255))

    cv2.rectangle(image, (170, 255), (560, 385), (95, 95, 95), 1)
    hand_x = int(170 + snapshot.x * 390)
    hand_y = int(385 - snapshot.y * 130)
    cv2.circle(image, (hand_x, hand_y), 9, (0, 255, 255), cv2.FILLED)
    cv2.putText(
        image,
        f"hand x={snapshot.x:.2f}, y={snapshot.y:.2f}",
        (40, 325),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (230, 230, 230),
        1,
    )

    cv2.imshow("Renderer - OBS Capture", image)
    return cv2.waitKey(16) & 0xFF != ord("q")


def start_osc_server():
    dispatcher = Dispatcher()
    dispatcher.map("/hand/position", handle_position)
    dispatcher.map("/hand/openness", handle_openness)
    dispatcher.map("/hand/features", handle_features)

    server = osc_server.ThreadingOSCUDPServer((OSC_IP, OSC_PORT), dispatcher)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main():
    server = start_osc_server()
    print(f"Listening for OSC on {OSC_IP}:{OSC_PORT}")
    print("Press q in the visualizer window to quit.")

    try:
        with sd.OutputStream(
            channels=2,
            callback=audio_callback,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
        ):
            while draw_visualizer():
                pass
    finally:
        server.shutdown()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
