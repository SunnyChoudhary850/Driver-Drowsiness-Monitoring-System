# 🚗 Driver Drowsiness Monitoring System (Futuristic HUD)

An intelligent, real-time driver fatigue and drowsiness detection system engineered with **Python**, **OpenCV**, and **CustomTkinter**. The application processes live video feeds using adaptive contrast enhancement (CLAHE), facial feature tracking, multi-zone eye monitoring, and asynchronous multithreaded alert mechanisms.

---

## 📸 Overview & Key Features

* **Real-Time Facial & Eye Tracking:** High-FPS webcam stream processing using spatial filtering and facial feature detection.
* **Low-Light Adaptive Preprocessing:** Implements CLAHE (Contrast Limited Adaptive Histogram Equalization) to maintain high accuracy under uneven or dark driving conditions.
* **Dual-Zone Detection & Debouncing:** Multi-frame debouncing logic eliminates false positives caused by natural eye blinks, facial expressions, or eyeglasses.
* **Multithreaded Alert Engine:** Non-blocking async threads trigger real-time audio alarms and automated email notifications without dropping frame rates or locking the UI.
* **Futuristic HUD Dashboard:** Modern dark-mode interface built with CustomTkinter featuring real-time risk progress gauges, diagnostic indicator dots, and session telemetry timers.
* **Research-Backed Pipeline:** Includes research documentation (`SIESD-Research_paper.pdf`) detailing system architecture and evaluation metrics.

---

## 🛠️ Tech Stack

* **Language:** Python 3.10+
* **Computer Vision:** OpenCV, Pillow
* **GUI Framework:** CustomTkinter, Tkinter
* **Concurrency:** Python `threading`
* **Alert System:** SMTP (`email_alert.py`), Native Audio (`winsound`)

---

## 📁 Repository Structure

```text
├── audio/                                # Audio files for alert sounds
├── haarcascades/                         # Haar Cascade XML classifiers
├── images/                               # UI assets and background graphics
├── .gitignore                            # Git ignore configuration
├── SIESD-Research_paper.pdf              # System architecture research paper
├── drowsiness_detect.py                  # Core detection logic module
├── email_alert.py                        # SMTP email dispatch engine
├── face_and_eye_detector_single_image.py # Static image testing script
├── face_and_eye_detector_webcam_video.py # Main entry point (CustomTkinter HUD)
└── requirements.txt                      # Project dependencies

---

**🚀 Getting Started**
Prerequisites
Python 3.10 or higher

A connected webcam (built-in or USB)

**Installation**
## 1. Clone the repository:
git clone [https://github.com/SunnyChoudhary850/Driver-Drowsiness-Monitoring-System.git](https://github.com/SunnyChoudhary850/Driver-Drowsiness-Monitoring-System.git)
cd Driver-Drowsiness-Monitoring-System
## 2. Install required dependencies:
pip install -r requirements.txt
## 3. python face_and_eye_detector_webcam_video.py
python face_and_eye_detector_webcam_video.py
