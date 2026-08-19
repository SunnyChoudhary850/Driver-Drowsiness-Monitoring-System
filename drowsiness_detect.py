"""
Real-time driver drowsiness detection using Haar cascades (face + eyes).

Fixes applied vs. the original version:
- No longer confuses "no face in frame" with "eyes closed" (was a false-alarm bug).
- Alarm sound is now non-blocking (SND_ASYNC) so the video feed no longer freezes
  while the alert plays.
- winsound import is guarded so the script doesn't crash on import on non-Windows
  systems (it will print a warning and skip audio instead).
- Cascade files default to OpenCV's bundled haarcascades (cv2.data.haarcascades)
  instead of a relative "haarcascades/" folder that may not exist.
- Webcam and windows are released/closed in a try/finally so a crash mid-loop
  doesn't leave the camera locked.
- "EYES CLOSED!" text is drawn every frame while the alarm is active, not just
  on the single frame the threshold was crossed.
- Now sends an email alert (via email_alert.py) the moment the alarm triggers,
  running in a background thread so it never blocks or slows down the video feed.
- Eye search is now restricted to the upper-face region only, with stricter
  detection settings (minNeighbors=8). Previously the eye cascade searched the
  WHOLE face, which caused false-positive "eyes detected" hits on eyebrows,
  nostrils, or mouth creases even while the eyes were genuinely closed -
  meaning the alarm sometimes never triggered at all.

Further accuracy tuning:
- Histogram equalization (cv2.equalizeHist) applied before detection - improves
  Haar cascade accuracy significantly under uneven or dim lighting.
- Face detection now requires a minimum size, filtering out tiny false-positive
  "face" detections in the background.
- Debounced eyes-open detection: a SINGLE frame where the eye cascade misfires
  and reports "eyes detected" no longer resets the closed-eye timer back to
  zero. It now takes CONSECUTIVE_OPEN_FRAMES_TO_RESET (default 3) consecutive
  "eyes open" frames in a row to reset the timer, filtering out single-frame
  detection noise that was previously preventing the alarm from accumulating
  enough time to trigger.

Second (more aggressive) accuracy pass:
- Switched from plain histogram equalization to CLAHE (adaptive local contrast),
  which handles shadow/lighting noise around the eyes better.
- Eye search is now split into separate LEFT and RIGHT zones (instead of one
  wide band), avoiding the nose bridge/glasses-frame area and roughly halving
  the search area per eye.
- Detections are filtered by expected eye width relative to face width
  (13%-38%), discarding false positives that are the wrong size to be a real
  eye (eyebrows, nostrils, skin folds).
- minNeighbors raised to 15 (from 8) - requires far more overlapping matches
  before something counts as a detected eye.
- BOTH left and right zones must register a hit for "eyes detected" to be
  true - a single-zone hit is treated as noise, not a real open eye.

UI / alerting update:
- Removed the on-screen debug text and "EYES CLOSED!" warning text - the
  video feed is now clean with just the face/eye tracking boxes.
- Added an on-screen alarm trigger counter (top-left corner).
- Email alerts are now only sent once the trigger count exceeds 3 - the sound
  alarm still plays every time for immediate feedback, but email is reserved
  for repeated/escalating drowsiness episodes rather than firing on every
  single trigger.

Requires email_alert.py (in the same folder) to be configured - see .env.example.
If email isn't configured, this script still works fine; it just skips the email
and logs a one-time warning instead.
"""

import time
import os
import sys
import threading

import cv2

# --- Guard winsound import (Windows-only stdlib module) -------------------
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False
    print("[WARNING] 'winsound' is not available on this OS (Windows-only). "
          "Audio alerts will be disabled; a console message will be printed instead.")

# --- Email alert integration ------------------------------------------------
try:
    from email_alert import send_email_alert, EMAIL_SENDER, EMAIL_APP_PASSWORD, EMAIL_RECIPIENT
    EMAIL_CONFIGURED = bool(EMAIL_SENDER and EMAIL_APP_PASSWORD and EMAIL_RECIPIENT)
    if not EMAIL_CONFIGURED:
        print("[WARNING] Email not configured (missing EMAIL_SENDER / EMAIL_APP_PASSWORD / "
              "EMAIL_RECIPIENT in your .env). Alarm will trigger sound only, no email.")
except ImportError:
    EMAIL_CONFIGURED = False
    print("[WARNING] email_alert.py not found next to this script. "
          "Alarm will trigger sound only, no email.")

# --- Configuration ----------------------------------------------------------
EYE_DETECTION_TIMEOUT = 5  # seconds of continuous "eyes not detected" before alarm

# How many CONSECUTIVE "eyes open" frames are needed before the closed-eye timer
# resets. Prevents a single misdetected frame from wiping out an otherwise-valid
# "eyes closed" streak.
CONSECUTIVE_OPEN_FRAMES_TO_RESET = 3

# --- Eye-detection sensitivity (tune these if it's too strict or too loose) --
# Lower minNeighbors = more sensitive (may false-positive on closed eyes).
# Higher minNeighbors = stricter (may miss genuinely open eyes).
# 8 was too loose (closed eyes registered as open). 15 was too strict (open
# eyes registered as closed). 11 is a middle ground - adjust up/down by 1-2
# if it's still not quite right for your lighting/camera.
EYE_MIN_NEIGHBORS = 11

# How many of the 2 eye zones (left/right) must register a hit to count as
# "eyes open". 2 = strict (both must agree, fewer false "open" positives but
# may miss real opens). 1 = loose (either eye is enough, more forgiving but
# more prone to false "open" positives). 1 is the middle-ground default.
EYE_ZONES_REQUIRED = 1

# Real eye width as a fraction of face width. Widened slightly from the
# previous strict pass (13%-38%) to avoid rejecting genuinely open eyes.
EYE_MIN_WIDTH_RATIO = 0.11
EYE_MAX_WIDTH_RATIO = 0.42

# How many times the alarm must trigger (in this run) before an email is sent.
# Sound still plays on every trigger; email is reserved for repeated episodes.
ALARM_COUNT_EMAIL_THRESHOLD = 3

# Allow overriding via environment variable; otherwise look for a local file.
AUDIO_FILE_PATH = os.environ.get("DDDS_AUDIO_PATH", os.path.join("audio", "alert.wav"))

# Use OpenCV's bundled cascade files by default (always present with opencv-python),
# but allow a custom "haarcascades/" folder to override them if present.
_local_cascade_dir = "haarcascades"
FACE_CASCADE_PATH = (
    os.path.join(_local_cascade_dir, "haarcascade_frontalface_default.xml")
    if os.path.exists(os.path.join(_local_cascade_dir, "haarcascade_frontalface_default.xml"))
    else os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
)
EYE_CASCADE_PATH = (
    os.path.join(_local_cascade_dir, "haarcascade_eye.xml")
    if os.path.exists(os.path.join(_local_cascade_dir, "haarcascade_eye.xml"))
    else os.path.join(cv2.data.haarcascades, "haarcascade_eye.xml")
)


def play_alarm():
    """Play the alert sound without blocking the main detection loop."""
    if HAS_WINSOUND and os.path.exists(AUDIO_FILE_PATH):
        winsound.PlaySound(AUDIO_FILE_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
    else:
        print("[ALERT] Drowsiness detected! (audio unavailable)")


def send_alarm_email():
    """Send the drowsiness email alert in a background thread so the video loop never waits on it."""
    if not EMAIL_CONFIGURED:
        return

    def _send():
        send_email_alert(
            subject="⚠️ Drowsiness Alert",
            body="Drowsiness was detected! The driver's eyes were closed for an extended period. "
                 "Please check on them immediately."
        )

    threading.Thread(target=_send, daemon=True).start()


def main():
    print("[INFO] drowsiness_detect.py - version: counter + threshold-email (no debug text)")

    if not os.path.exists(FACE_CASCADE_PATH):
        raise FileNotFoundError(f"[ERROR] Face cascade file not found: {FACE_CASCADE_PATH}")
    if not os.path.exists(EYE_CASCADE_PATH):
        raise FileNotFoundError(f"[ERROR] Eye cascade file not found: {EYE_CASCADE_PATH}")
    if not HAS_WINSOUND:
        print("[NOTE] Continuing without audio playback.")
    elif not os.path.exists(AUDIO_FILE_PATH):
        print(f"[WARNING] Audio file not found at '{AUDIO_FILE_PATH}'. "
              f"Set DDDS_AUDIO_PATH env var to point at a valid .wav file. "
              f"Continuing with console alerts only.")

    face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
    eye_cascade = cv2.CascadeClassifier(EYE_CASCADE_PATH)
    if face_cascade.empty():
        raise IOError(f"[ERROR] Failed to load face cascade from {FACE_CASCADE_PATH}")
    if eye_cascade.empty():
        raise IOError(f"[ERROR] Failed to load eye cascade from {EYE_CASCADE_PATH}")

    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        raise RuntimeError("[ERROR] Webcam not detected!")

    # CLAHE (adaptive local contrast) - more effective than plain equalizeHist
    # at suppressing shadow/eyelash noise that fools the eye cascade into
    # false-positive "eyes open" hits on closed eyelids.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    time.sleep(2)  # let the camera warm up
    closed_eye_start_time = None
    alarm_triggered = False
    consecutive_open_frames = 0
    alarm_trigger_count = 0

    try:
        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("[ERROR] Failed to grab frame!")
                break

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = clahe.apply(gray)

            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.3, minNeighbors=5, minSize=(120, 120))
            face_detected = len(faces) > 0
            eyes_detected = False
            zones_found = 0

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                roi_gray = gray[y:y + h, x:x + w]

                # Vertical band where eyes actually sit on a face.
                eye_region_top = int(h * 0.20)
                eye_region_bottom = int(h * 0.50)

                # Split into separate left-eye and right-eye search zones instead
                # of one wide band. This avoids the nose bridge / glasses-frame
                # area entirely and roughly halves the search area per eye,
                # which meaningfully cuts down false-positive detections.
                left_zone = roi_gray[eye_region_top:eye_region_bottom, int(w * 0.05):int(w * 0.48)]
                right_zone = roi_gray[eye_region_top:eye_region_bottom, int(w * 0.52):int(w * 0.95)]

                # A real eye is roughly EYE_MIN_WIDTH_RATIO-EYE_MAX_WIDTH_RATIO
                # of the face width. Anything detected outside that ratio is
                # likely an eyebrow, nostril, or skin-fold false positive.
                min_eye_w = int(w * EYE_MIN_WIDTH_RATIO)
                max_eye_w = int(w * EYE_MAX_WIDTH_RATIO)

                zones_found = 0
                for zone_gray, x_offset in [(left_zone, int(w * 0.05)), (right_zone, int(w * 0.52))]:
                    if zone_gray.size == 0:
                        continue
                    eyes = eye_cascade.detectMultiScale(
                        zone_gray, scaleFactor=1.05, minNeighbors=EYE_MIN_NEIGHBORS,
                        minSize=(min_eye_w, min_eye_w), maxSize=(max_eye_w, max_eye_w))
                    if len(eyes) > 0:
                        zones_found += 1
                        ex, ey, ew, eh = eyes[0]  # take the strongest match in this zone
                        cv2.rectangle(
                            frame,
                            (x + x_offset + ex, y + eye_region_top + ey),
                            (x + x_offset + ex + ew, y + eye_region_top + ey + eh),
                            (0, 255, 0), 2
                        )

                # Require EYE_ZONES_REQUIRED of the 2 eye zones to register a hit.
                if zones_found >= EYE_ZONES_REQUIRED:
                    eyes_detected = True

            # Only treat this as "eyes closed" if a face IS present but eyes are NOT.
            # (Previously: no face in frame was wrongly treated the same as eyes closed.)
            if face_detected and not eyes_detected:
                consecutive_open_frames = 0
                if closed_eye_start_time is None:
                    closed_eye_start_time = time.time()
                elapsed_time = time.time() - closed_eye_start_time

                if elapsed_time >= EYE_DETECTION_TIMEOUT:
                    if not alarm_triggered:
                        alarm_triggered = True
                        alarm_trigger_count += 1
                        play_alarm()
                        if alarm_trigger_count > ALARM_COUNT_EMAIL_THRESHOLD:
                            send_alarm_email()
            elif face_detected and eyes_detected:
                # Debounce: require several CONSECUTIVE "eyes open" frames before
                # fully resetting. A single misdetected frame (Haar cascade noise)
                # no longer wipes out an otherwise-valid closed-eye streak.
                consecutive_open_frames += 1
                if consecutive_open_frames >= CONSECUTIVE_OPEN_FRAMES_TO_RESET:
                    closed_eye_start_time = None
                    alarm_triggered = False
            else:
                # No face at all - reset immediately, nothing to debounce.
                consecutive_open_frames = 0
                closed_eye_start_time = None
                alarm_triggered = False

            # On-screen alarm trigger counter.
            counter_text = f"Alerts: {alarm_trigger_count}"
            cv2.putText(frame, counter_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            cv2.imshow("Eye Detection Alarm", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        video_capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        sys.exit(1)