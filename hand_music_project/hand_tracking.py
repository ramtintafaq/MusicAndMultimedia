"""
Entity 1: real-time hand tracking and OSC sender.

OSC messages sent to 127.0.0.1:9000:
    /hand/position  x y
    /hand/openness  openness
    /hand/features  x y openness   (optional, disabled by default)

All values are normalized to the range [0, 1].
For y, 0 means bottom of the camera image and 1 means top, so moving the
hand upward can directly increase pitch in the renderer.
"""

import time

import cv2
import mediapipe as mp
from pythonosc.udp_client import SimpleUDPClient


OSC_IP = "127.0.0.1"
OSC_PORT = 9000
CAMERA_INDEX = 0
TARGET_FPS = 30

# The required messages are /hand/position and /hand/openness.
# Keep this False to avoid sending redundant OSC messages during the demo.
SEND_FEATURES_MESSAGE = False


mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


def clamp(value, minimum=0.0, maximum=1.0):
    """Keep a numeric value inside a fixed range."""
    return max(minimum, min(maximum, value))


def landmark_distance(a, b):
    """2D distance between two MediaPipe landmarks."""
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def estimate_openness(landmarks):
    """
    Estimate how open the hand is from fingertip distance to the wrist.

    This is intentionally simple and explainable: an open hand has fingertips
    farther from the wrist than a closed hand. The value is normalized using
    palm size so it works reasonably across different camera distances.
    """
    wrist = landmarks[0]
    middle_mcp = landmarks[9]
    palm_size = max(landmark_distance(wrist, middle_mcp), 0.01)

    fingertip_ids = [4, 8, 12, 16, 20]
    average_tip_distance = sum(
        landmark_distance(wrist, landmarks[finger_id])
        for finger_id in fingertip_ids
    ) / len(fingertip_ids)

    openness_raw = average_tip_distance / palm_size
    return clamp((openness_raw - 1.4) / 1.1)


def extract_features(hand_landmarks):
    """Return normalized x, y, and openness values for one detected hand."""
    landmarks = hand_landmarks.landmark
    palm_center = landmarks[9]

    x = clamp(palm_center.x)
    y = clamp(1.0 - palm_center.y)
    openness = estimate_openness(landmarks)

    return x, y, openness


def draw_overlay(frame, hand_landmarks, x, y, openness):
    """Draw landmarks and current values for debugging and live demo setup."""
    height, width, _ = frame.shape
    screen_x = int(x * width)
    screen_y = int((1.0 - y) * height)

    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
    cv2.circle(frame, (screen_x, screen_y), 12, (0, 255, 0), cv2.FILLED)

    text = f"x: {x:.2f}  y(up): {y:.2f}  openness: {openness:.2f}"
    cv2.putText(
        frame,
        text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 255, 0),
        2,
    )


def main():
    client = SimpleUDPClient(OSC_IP, OSC_PORT)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

    if not cap.isOpened():
        print("Webcam not detected. Check the camera index and permissions.")
        return

    print(f"Sending OSC to {OSC_IP}:{OSC_PORT}")
    print("Press q in the camera window to quit.")

    last_print_time = 0.0

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    ) as hands:
        while True:
            success, frame = cap.read()
            if not success:
                print("Camera frame could not be read.")
                break

            # Mirror the image so movement feels natural during the demo.
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb_frame)

            if result.multi_hand_landmarks:
                hand_landmarks = result.multi_hand_landmarks[0]
                x, y, openness = extract_features(hand_landmarks)

                client.send_message("/hand/position", [x, y])
                client.send_message("/hand/openness", openness)
                if SEND_FEATURES_MESSAGE:
                    client.send_message("/hand/features", [x, y, openness])

                draw_overlay(frame, hand_landmarks, x, y, openness)

                now = time.monotonic()
                if now - last_print_time >= 1.0:
                    print(f"x={x:.2f}, y={y:.2f}, openness={openness:.2f}")
                    last_print_time = now
            else:
                cv2.putText(
                    frame,
                    "No hand detected",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 0, 255),
                    2,
                )

            cv2.imshow("Hand Tracking - OSC Sender", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
