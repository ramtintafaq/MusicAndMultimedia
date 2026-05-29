"""
Entity 1: hand tracking.

This script uses the webcam to detect one hand and sends simple gesture data
to renderer.py using OSC.

OSC output to 127.0.0.1:9000:
    /hand/position  x y
    /hand/openness  openness

All values are normalized between 0 and 1.
"""

import cv2
import mediapipe as mp
from pythonosc.udp_client import SimpleUDPClient


OSC_IP = "127.0.0.1"
OSC_PORT = 9000
CAMERA_INDEX = 0


mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


def clamp(value):
    return max(0.0, min(1.0, value))


def distance(point_a, point_b):
    return ((point_a.x - point_b.x) ** 2 + (point_a.y - point_b.y) ** 2) ** 0.5


def get_openness(landmarks):
    """
    Very simple open/close estimation.
    If fingertips are far from the wrist, the hand is more open.
    """
    wrist = landmarks[0]
    palm = landmarks[9]
    palm_size = max(distance(wrist, palm), 0.01)

    fingertips = [4, 8, 12, 16, 20]
    total = 0.0

    for finger_id in fingertips:
        total += distance(wrist, landmarks[finger_id])

    average_distance = total / len(fingertips)
    openness = (average_distance / palm_size - 1.4) / 1.1

    return clamp(openness)


def main():
    osc_client = SimpleUDPClient(OSC_IP, OSC_PORT)
    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        print("Webcam not detected.")
        return

    print(f"Sending OSC to {OSC_IP}:{OSC_PORT}")
    print("Press q to quit.")

    with mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    ) as hands:
        while True:
            success, frame = camera.read()

            if not success:
                print("Could not read from webcam.")
                break

            # Mirror the webcam image so left/right movement feels natural.
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb_frame)

            if result.multi_hand_landmarks:
                hand = result.multi_hand_landmarks[0]
                landmarks = hand.landmark

                # Landmark 9 is near the center of the hand.
                x = clamp(landmarks[9].x)
                y = clamp(1.0 - landmarks[9].y)
                openness = get_openness(landmarks)

                # Required OSC messages.
                osc_client.send_message("/hand/position", [x, y])
                osc_client.send_message("/hand/openness", openness)

                mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

                text = f"x: {x:.2f}  y: {y:.2f}  open: {openness:.2f}"
                cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                print(text)
            else:
                cv2.putText(frame, "No hand detected", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

            cv2.imshow("Hand Tracking", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
