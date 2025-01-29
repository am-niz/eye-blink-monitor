import cv2
import dlib
import numpy as np
import time
from playsound import playsound
import os

def eye_aspect_ratio(eye):
    # Compute distances between vertical eye landmarks
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    # Compute distance between horizontal eye landmarks
    C = np.linalg.norm(eye[0] - eye[3])
    # Calculate eye aspect ratio
    ear = (A + B) / (2.0 * C)
    return ear

# Initialize dlib's face detector and facial landmark predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')

# Constants and variables
EAR_THRESHOLD = 0.25
FRAMES_TO_CONFIRM = 1
MIN_FRAMES_BETWEEN_BLINKS = 1
HEALTHY_BLINKS_PER_MINUTE = 15
CHECK_INTERVAL = 60

# Global variables
BLINK_COUNT = 0
PREVIOUS_EYE_STATE = "open"
EYE_CLOSED_FRAMES = 0
FRAMES_SINCE_LAST_BLINK = MIN_FRAMES_BETWEEN_BLINKS + 1
last_check_time = time.time()
last_alert_time = 0  # Add this to track when we last alerted
ALERT_SOUND_PATH = os.path.join(os.path.dirname(__file__), 'static', 'sounds', 'alert.mp3')

if not os.path.exists(ALERT_SOUND_PATH):
    print(f"Warning: Sound file not found at {ALERT_SOUND_PATH}")

def play_alert():
    try:
        os.system('play -v 0.5 sounds/alert.mp3 &>/dev/null &')  # Lower volume (0.5) and run in background
    except Exception as e:
        print(f"Error playing sound: {e}")

def process_frame(frame):
    global BLINK_COUNT, EYE_CLOSED_FRAMES, PREVIOUS_EYE_STATE, FRAMES_SINCE_LAST_BLINK, last_check_time, last_alert_time
    
    try:
        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = detector(gray)
        
        for face in faces:
            # Get facial landmarks
            landmarks = predictor(gray, face)
            landmarks = np.array([[p.x, p.y] for p in landmarks.parts()])
            
            # Extract eye coordinates
            left_eye = landmarks[42:48]
            right_eye = landmarks[36:42]
            
            # Calculate EAR for both eyes
            left_ear = eye_aspect_ratio(left_eye)
            right_ear = eye_aspect_ratio(right_eye)
            avg_ear = (left_ear + right_ear) / 2
            
            # Draw eye contours
            cv2.polylines(frame, [left_eye], True, (0, 255, 0), 1)
            cv2.polylines(frame, [right_eye], True, (0, 255, 0), 1)
            
            # Check for blink with improved logic
            if avg_ear < EAR_THRESHOLD:
                EYE_CLOSED_FRAMES += 1
                current_eye_state = "closed"
            else:
                current_eye_state = "open"
                if (PREVIOUS_EYE_STATE == "closed" and 
                    EYE_CLOSED_FRAMES >= FRAMES_TO_CONFIRM and 
                    FRAMES_SINCE_LAST_BLINK > MIN_FRAMES_BETWEEN_BLINKS):
                    BLINK_COUNT += 1
                    FRAMES_SINCE_LAST_BLINK = 0
                EYE_CLOSED_FRAMES = 0
                
            PREVIOUS_EYE_STATE = current_eye_state
            FRAMES_SINCE_LAST_BLINK += 1
            
            # Display blink count and EAR with state indication
            cv2.putText(frame, f"Blinks: {BLINK_COUNT}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"EAR: {avg_ear:.2f}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            
            # Display current threshold for debugging
            cv2.putText(frame, f"Threshold: {EAR_THRESHOLD}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Check blink rate every minute
            current_time = time.time()
            if current_time - last_check_time >= CHECK_INTERVAL:
                should_alert = BLINK_COUNT < HEALTHY_BLINKS_PER_MINUTE
                BLINK_COUNT = 0  # Reset counter
                last_check_time = current_time
                return frame, BLINK_COUNT, should_alert
        
        return frame, BLINK_COUNT, False
    except Exception as e:
        print(f"Error processing frame: {e}")
        return frame, BLINK_COUNT, False