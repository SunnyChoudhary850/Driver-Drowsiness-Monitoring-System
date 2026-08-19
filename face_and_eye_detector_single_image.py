"""
Detects faces and eyes in a single input image using OpenCV's Haar cascades.

Fixes applied vs. the original version:
- Checks that the image actually loaded before processing (previously a bad path
  caused a confusing cv2.error deep inside cvtColor instead of a clear message).
- Checks that both cascades loaded successfully.
- Uses OpenCV's bundled cascade files by default, with an optional local
  "haarcascades/" folder override, instead of a hardcoded relative path.
- Image path is now a command-line argument instead of hardcoded.
"""

import argparse
import os
import sys

import cv2 as cv


def get_cascade_path(filename: str) -> str:
    local_path = os.path.join("haarcascades", filename)
    if os.path.exists(local_path):
        return local_path
    return os.path.join(cv.data.haarcascades, filename)


def main():
    parser = argparse.ArgumentParser(description="Detect faces and eyes in an image.")
    parser.add_argument("image", nargs="?", default=os.path.join("images", "test.jpeg"),
                         help="Path to the input image (default: images/test.jpeg)")
    args = parser.parse_args()

    face_cascade_path = get_cascade_path("haarcascade_frontalface_default.xml")
    eye_cascade_path = get_cascade_path("haarcascade_eye.xml")

    face_cascade = cv.CascadeClassifier(face_cascade_path)
    eye_cascade = cv.CascadeClassifier(eye_cascade_path)
    if face_cascade.empty():
        raise IOError(f"[ERROR] Failed to load face cascade from {face_cascade_path}")
    if eye_cascade.empty():
        raise IOError(f"[ERROR] Failed to load eye cascade from {eye_cascade_path}")

    if not os.path.exists(args.image):
        raise FileNotFoundError(f"[ERROR] Image not found: {args.image}")

    img = cv.imread(args.image)
    if img is None:
        raise IOError(f"[ERROR] Could not read image (unsupported format or corrupt file): {args.image}")

    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        cv.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)

        roi_gray = gray[y:y + h, x:x + w]
        roi_color = img[y:y + h, x:x + w]

        eyes = eye_cascade.detectMultiScale(roi_gray)
        for (ex, ey, ew, eh) in eyes:
            cv.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

    print(f"[INFO] Detected {len(faces)} face(s).")
    cv.imshow("Image", img)
    cv.waitKey(0)
    cv.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        sys.exit(1)