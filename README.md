# 🚗 Driver Drowsiness Monitoring System (Futuristic HUD)

An intelligent, real-time driver fatigue and drowsiness detection system engineered with **Python**, **OpenCV**, and **CustomTkinter**. The application processes live video feeds using adaptive contrast enhancement (CLAHE), facial feature tracking, multi-zone eye monitoring, and asynchronous multithreaded alert mechanisms.

![Drowsiness Banner](<Drowsiness img.png>)

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
```

---

## 📐 System Architecture & Workflow

### 1. System Workflow
1. **Frame Preprocessing:** Video frames are captured, flipped, converted to grayscale, and normalized using CLAHE.
2. **ROI Extraction:** The system detects facial boundaries and isolates left/right eye regions using strict aspect-ratio constraints.
3. **Fatigue Evaluation:** If prolonged closure is detected (>3 seconds), the risk gauge fills and the status indicator transitions to an active alert.
4. **Asynchronous Dispatch:** Audio alarms sound immediately while an email notification dispatch thread executes in the background.

---

### 2. Process Flowchart
Logical decision pipeline from video frame ingestion to alarm trigger.

![Flow Diagram](<flow diagram.png>)

---

### 3. Data Flow Diagram (DFD)
High-level data transformations across system processes, buffers, and external outputs.

![Data Flow Diagram](<Screenshot 2025-05-19 183748.png>)

---

## 🧮 Mathematical Model

Eye aperture dynamics and distance thresholds are calculated frame-by-frame using the 2D Euclidean distance formula across keypoint coordinates:

$$d = \sqrt{(\Delta x)^2 + (\Delta y)^2} = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$

![Eye Geometry Formula](<mathematics to cal eye movement.png>)

---

## 📸 System In Action

### Single Image Pre-processing & Detection
Bounding box verification for facial structure and eye regions.

| Input Test | Detection Result |
| :---: | :---: |
| ![Camera Image Sample](<camp of img .png>) | ![Detection Result](result_face_detector_single_image.png) |

---

### Live Webcam Alert & Email Dispatch
When continuous eye closure exceeds **3 seconds**, the heads-up display triggers an alarm, and a detailed HTML report is emailed instantly.

| Real-Time HUD Overlay | Delivered Email Report |
| :---: | :---: |
| ![Alarm Overlay Triggered](<alarm triggered.jpg>) | ![Email Delivered Snapshot](<Got the mail.png>) |

---

## 🚀 Getting Started

### Prerequisites

* **Python:** Version 3.10 or higher
* **Hardware:** A connected webcam (built-in or USB)

### 1. Installation

```bash
git clone https://github.com/SunnyChoudhary850/Driver-Drowsiness-Monitoring-System.git
cd Driver-Drowsiness-Monitoring-System
pip install -r requirements.txt
```

### 2. Environment Configuration (`.env`)

Create a `.env` file in the root directory for automated email alerts:

```env
EMAIL_SENDER=your_email@gmail.com
EMAIL_APP_PASSWORD=your_app_password
EMAIL_RECIPIENT=recipient_email@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### 3. Execution

```bash
python face_and_eye_detector_webcam_video.py
```
