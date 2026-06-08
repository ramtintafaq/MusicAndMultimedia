"""
Entity 1: hand tracking.

This script uses the webcam to detect one hand and sends simple gesture data
using OSC.

OSC output to Wekinator:
    127.0.0.1:6448
    /wek/inputs  x y openness

All values are normalized between 0 and 1.
"""

import cv2
import mediapipe as mp
from pythonosc.udp_client import SimpleUDPClient


OSC_IP = "127.0.0.1"
WEKINATOR_PORT = 6448
CAMERA_INDEX = 0
FINGERTIP_LANDMARKS = [4, 8, 12, 16, 20]

# These two numbers calibrate the open/close gesture.
# If open hand is too low, decrease OPEN_HAND_RATIO.
# If closed hand is too high, increase CLOSED_HAND_RATIO.
CLOSED_HAND_RATIO = 1.10
OPEN_HAND_RATIO = 1.60


mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


# Keep a number between 0 and 1.
def clamp(value):
    return max(0.0, min(1.0, value))


# Calculate the distance between two MediaPipe points.
def distance(point_a, point_b):
    return ((point_a.x - point_b.x) ** 2 + (point_a.y - point_b.y) ** 2) ** 0.5


# Estimate how open or closed the detected hand is.
def get_openness(landmarks):
    """
    Very simple open/close estimation.
    If fingertips are far from the wrist, the hand is more open.
    """
    wrist = landmarks[0]
    palm = landmarks[9]
    palm_size = max(distance(wrist, palm), 0.01)

    total = 0.0

    for finger_id in FINGERTIP_LANDMARKS:
        total += distance(wrist, landmarks[finger_id])

    average_distance = total / len(FINGERTIP_LANDMARKS)
    hand_ratio = average_distance / palm_size
    openness = (hand_ratio - CLOSED_HAND_RATIO) / (OPEN_HAND_RATIO - CLOSED_HAND_RATIO)

    return clamp(openness)


# Open the webcam, track the hand, and send OSC data to Wekinator.
def main():
    wekinator_client = SimpleUDPClient(OSC_IP, WEKINATOR_PORT)
    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        print("Webcam not detected.")
        return

    print(f"Sending OSC inputs to Wekinator on {OSC_IP}:{WEKINATOR_PORT}")
    print("OSC message: /wek/inputs x y openness")
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

                #landmark 9 is the center of the hand
                x = clamp(landmarks[9].x)
                y = clamp(1.0 - landmarks[9].y)
                openness = get_openness(landmarks)

                # Wekinator receives these values for machine learning.
                wekinator_client.send_message("/wek/inputs", [x, y, openness])

                mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

                text = f"x: {x:.2f}  y: {y:.2f}  open: {openness:.2f}"
                cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "No hand detected", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

            cv2.imshow("Hand Tracking", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
