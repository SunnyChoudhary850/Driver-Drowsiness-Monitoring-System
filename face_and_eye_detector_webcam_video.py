import time
import os
import threading
import math
import sys
import tkinter as tk
from tkinter import messagebox

import cv2 as cv
from PIL import Image, ImageTk, ImageDraw
import customtkinter as ctk

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

try:
    from email_alert import send_email_alert, EMAIL_SENDER, EMAIL_APP_PASSWORD, EMAIL_RECIPIENT
    EMAIL_CONFIGURED = bool(EMAIL_SENDER and EMAIL_APP_PASSWORD and EMAIL_RECIPIENT)
except ImportError:
    EMAIL_CONFIGURED = False

# --- Configuration -----------------
FACE_CASCADE_PATH = cv.data.haarcascades + "haarcascade_frontalface_default.xml"
EYE_CASCADE_PATH = cv.data.haarcascades + "haarcascade_eye.xml"
ALARM_AUDIO_PATH = os.environ.get("DDDS_AUDIO_PATH", os.path.join("audio", "alert.wav"))
BACKGROUND_IMAGE_PATH = os.environ.get("DDDS_BG_IMAGE_PATH", os.path.join("images", "car_image.png"))

EYE_CLOSED_THRESHOLD = 3  
MARGIN = 30  

EYE_MIN_NEIGHBORS = 11
EYE_ZONES_REQUIRED = 1
EYE_MIN_WIDTH_RATIO = 0.11
EYE_MAX_WIDTH_RATIO = 0.42
CONSECUTIVE_OPEN_FRAMES_TO_RESET = 3
ALARM_COUNT_EMAIL_THRESHOLD = 3

ctk.set_appearance_mode("dark")

def check_required_files():
    problems = []
    if not os.path.exists(FACE_CASCADE_PATH):
        problems.append(f"Face cascade not found: {FACE_CASCADE_PATH}")
    if not os.path.exists(EYE_CASCADE_PATH):
        problems.append(f"Eye cascade not found: {EYE_CASCADE_PATH}")
    return problems


class DrowsinessDetectorApp(ctk.CTk):
    # --- Futuristic neon-HUD palette ---
    COLOR_BG = "#03040a"          
    COLOR_PANEL = "#070b16"       
    COLOR_BORDER = "#0e7490"      
    COLOR_NEON = "#22d3ee"        
    COLOR_NEON_DIM = "#0891b2"    
    COLOR_TEXT = "#e0fbff"        
    COLOR_SUBTEXT = "#67e8f9"     
    COLOR_ALERT = "#fb7185"       
    COLOR_ALERT_DIM = "#9f1239"
    COLOR_OK = "#4ade80"          
    COLOR_OFF = "#1e293b"         

    DISPLAY_W, DISPLAY_H = 640, 480 

    def __init__(self):
        super().__init__()
        
        self.title("Drowsiness Detection HUD")
        self.geometry("1100x750")
        self.configure(fg_color=self.COLOR_BG)
        self.minsize(1000, 700)

        # Main Layout Grid
        self.grid_columnconfigure(0, weight=3) # Video side
        self.grid_columnconfigure(1, weight=1) # Sidebar
        self.grid_rowconfigure(1, weight=1)

        # --- Header Panel ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=80)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(self.header_frame, text="D R O W S I N E S S   D E T E C T I O N", 
                     font=ctk.CTkFont(family="Consolas", size=26, weight="bold"), text_color=self.COLOR_NEON).pack(pady=(10,0))
        ctk.CTkLabel(self.header_frame, text=">> monitoring driver alertness in real time", 
                     font=ctk.CTkFont(family="Consolas", size=12), text_color=self.COLOR_SUBTEXT).pack()

        # --- Left Panel (Video & Controls) ---
        self.left_frame = ctk.CTkFrame(self, fg_color=self.COLOR_PANEL, border_color=self.COLOR_BORDER, border_width=1, corner_radius=10)
        self.left_frame.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(0, weight=1)

        # Video Canvas (Retaining your exact targeting brackets)
        pad = 14
        canvas_w, canvas_h = self.DISPLAY_W + pad * 2, self.DISPLAY_H + pad * 2
        self.video_canvas = tk.Canvas(self.left_frame, width=canvas_w, height=canvas_h, 
                                      bg=self.COLOR_PANEL, highlightthickness=0)
        self.video_canvas.grid(row=0, column=0, pady=20)

        self.video_label = tk.Label(self.video_canvas, bg="#000000", bd=0)
        self.video_canvas.create_window(pad, pad, anchor="nw", window=self.video_label, width=self.DISPLAY_W, height=self.DISPLAY_H)
        self.bracket_ids = self._draw_corner_brackets(self.video_canvas, pad - 2, pad - 2, canvas_w - pad + 2, canvas_h - pad + 2, self.COLOR_NEON)

        # Status & Controls
        self.control_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.control_frame.grid(row=1, column=0, pady=(0, 20), sticky="ew")
        self.control_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.status_var = tk.StringVar(value="STANDBY :: press START to begin")
        ctk.CTkLabel(self.control_frame, textvariable=self.status_var, font=("Consolas", 16, "bold"), text_color=self.COLOR_NEON).grid(row=0, column=0, columnspan=3, pady=10)

        # Native CTk Buttons for the Neon Effect
        btn_kwargs = {"font": ("Consolas", 14, "bold"), "border_width": 2, "fg_color": "transparent", "width": 140, "height": 45}
        
        self.start_btn = ctk.CTkButton(self.control_frame, text="START", text_color=self.COLOR_OK, border_color=self.COLOR_OK, hover_color="#166534", command=self.start_detection, **btn_kwargs)
        self.start_btn.grid(row=1, column=0, padx=10)

        self.stop_btn = ctk.CTkButton(self.control_frame, text="STOP", text_color=self.COLOR_ALERT, border_color=self.COLOR_ALERT, hover_color="#881337", state="disabled", command=self.stop_detection, **btn_kwargs)
        self.stop_btn.grid(row=1, column=1, padx=10)

        self.quit_btn = ctk.CTkButton(self.control_frame, text="QUIT", text_color=self.COLOR_SUBTEXT, border_color=self.COLOR_SUBTEXT, hover_color="#164e63", command=self.quit_app, **btn_kwargs)
        self.quit_btn.grid(row=1, column=2, padx=10)

        # --- Right Panel (Dashboard) ---
        self.right_frame = ctk.CTkFrame(self, fg_color=self.COLOR_PANEL, border_color=self.COLOR_BORDER, border_width=1, corner_radius=10)
        self.right_frame.grid(row=1, column=1, padx=(10, 20), pady=10, sticky="nsew")
        
        # We use standard Canvas here to keep your exact custom HUD drawings
        self.sidebar_canvas = tk.Canvas(self.right_frame, bg=self.COLOR_PANEL, highlightthickness=0)
        self.sidebar_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        scx = 150 # Estimated center

        # Indicator Lights
        self.sidebar_canvas.create_text(scx, 30, text="SENSORS", font=("Consolas", 12, "bold"), fill=self.COLOR_SUBTEXT)
        self.indicator_ids = {}
        for i, label in enumerate(["FACE", "EYES", "ALARM"]):
            y_pos = 60 + (i * 35)
            dot_id = self.sidebar_canvas.create_oval(scx - 60, y_pos - 8, scx - 44, y_pos + 8, fill=self.COLOR_OFF, outline="")
            self.sidebar_canvas.create_text(scx - 20, y_pos, text=label, font=("Consolas", 12, "bold"), fill=self.COLOR_TEXT, anchor="w")
            self.indicator_ids[label] = dot_id

        self.sidebar_canvas.create_line(20, 180, 280, 180, fill=self.COLOR_BORDER, width=1)

        # Risk Gauge (Your exact math)
        self.gauge = self._create_gauge(self.sidebar_canvas, scx, 290, radius=70)
        self.sidebar_canvas.create_text(scx, 385, text="DROWSINESS RISK", font=("Consolas", 11, "bold"), fill=self.COLOR_SUBTEXT)

        self.sidebar_canvas.create_line(20, 420, 280, 420, fill=self.COLOR_BORDER, width=1)

        # Session Timer
        self.sidebar_canvas.create_text(scx, 460, text="SESSION TIME", font=("Consolas", 11, "bold"), fill=self.COLOR_SUBTEXT)
        self.session_text_id = self.sidebar_canvas.create_text(scx, 495, text="00:00", font=("Consolas", 26, "bold"), fill=self.COLOR_NEON)
        
        # Alerts Counter
        self.alert_count_var = tk.StringVar(value="ALERTS :: 0")
        self.alert_label = ctk.CTkLabel(self.right_frame, textvariable=self.alert_count_var, font=("Consolas", 18, "bold"), text_color=self.COLOR_ALERT)
        self.alert_label.pack(side="bottom", pady=20)

        # --- CV & State Init ---
        self.face_cascade = cv.CascadeClassifier(FACE_CASCADE_PATH)
        self.eye_cascade = cv.CascadeClassifier(EYE_CASCADE_PATH)
        self.clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        self.video_capture = None
        self.running = False
        self.closed_eye_start_time = None
        self.alarm_triggered = False
        self.alarm_thread = None
        self.consecutive_open_frames = 0
        self.alarm_trigger_count = 0
        self.session_start_time = None

    # --- Retained Canvas Drawing Logic ---
    def _draw_corner_brackets(self, canvas, x1, y1, x2, y2, color, length=26, width=3):
        ids = []
        corners = [(x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)]
        for cx, cy, hdir, vdir in corners:
            h_id = canvas.create_line(cx, cy, cx + hdir * length, cy, fill=color, width=width)
            v_id = canvas.create_line(cx, cy, cx, cy + vdir * length, fill=color, width=width)
            ids.extend([h_id, v_id])
        return ids

    def _set_bracket_color(self, color):
        for item_id in self.bracket_ids:
            self.video_canvas.itemconfig(item_id, fill=color)

    def _create_gauge(self, canvas, cx, cy, radius):
        angle_start, angle_end = 225, -45 
        canvas.create_arc(cx - radius, cy - radius, cx + radius, cy + radius, start=angle_end, extent=270, style="arc", outline=self.COLOR_OFF, width=10)
        danger_extent = 270 * 0.25
        canvas.create_arc(cx - radius, cy - radius, cx + radius, cy + radius, start=angle_end, extent=danger_extent, style="arc", outline=self.COLOR_ALERT_DIM, width=10)

        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            theta = math.radians(angle_start - frac * 270)
            x1 = cx + (radius - 14) * math.cos(theta)
            y1 = cy - (radius - 14) * math.sin(theta)
            x2 = cx + (radius + 2) * math.cos(theta)
            y2 = cy - (radius + 2) * math.sin(theta)
            canvas.create_line(x1, y1, x2, y2, fill=self.COLOR_SUBTEXT, width=2)

        needle_id = canvas.create_line(cx, cy, cx, cy - radius + 20, fill=self.COLOR_NEON, width=3)
        hub_id = canvas.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill=self.COLOR_NEON, outline="")
        percent_id = canvas.create_text(cx, cy + 40, text="0%", font=("Consolas", 14, "bold"), fill=self.COLOR_NEON)

        return {"canvas": canvas, "cx": cx, "cy": cy, "radius": radius, "angle_start": angle_start, "angle_end": angle_end, "needle_id": needle_id, "hub_id": hub_id, "percent_id": percent_id}

    def _update_gauge(self, fraction):
        g = self.gauge
        fraction = max(0.0, min(1.0, fraction))
        theta = math.radians(g["angle_start"] - fraction * 270)
        needle_len = g["radius"] - 20
        x2 = g["cx"] + needle_len * math.cos(theta)
        y2 = g["cy"] - needle_len * math.sin(theta)
        color = self.COLOR_ALERT if fraction >= 0.75 else self.COLOR_NEON
        g["canvas"].coords(g["needle_id"], g["cx"], g["cy"], x2, y2)
        g["canvas"].itemconfig(g["needle_id"], fill=color)
        g["canvas"].itemconfig(g["hub_id"], fill=color)
        g["canvas"].itemconfig(g["percent_id"], text=f"{int(fraction * 100)}%", fill=color)

    # --- System Control Logic ---
    def start_detection(self):
        if self.running: return
        self.video_capture = cv.VideoCapture(0)
        if not self.video_capture.isOpened():
            messagebox.showerror("Error", "Webcam not detected!")
            self.video_capture = None
            return

        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_var.set("ACTIVE :: monitoring...")
        self.closed_eye_start_time = None
        self.alarm_triggered = False
        self.consecutive_open_frames = 0
        self.alarm_trigger_count = 0
        self.alert_count_var.set("ALERTS :: 0")
        self.session_start_time = time.time()
        self._update_gauge(0.0)
        self.update_frame()

    def stop_detection(self):
        if not self.running: return
        self.running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_var.set("STANDBY :: detection stopped")
        self._set_bracket_color(self.COLOR_NEON)
        self._update_gauge(0.0)
        for label in ["FACE", "EYES", "ALARM"]:
            self.sidebar_canvas.itemconfig(self.indicator_ids[label], fill=self.COLOR_OFF)
        self.closed_eye_start_time = None
        self.session_start_time = None
        self.stop_alarm()
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
        self.video_label.config(image="")

    def quit_app(self):
        self.stop_detection()
        self.destroy()

    def play_alarm(self):
        while self.alarm_triggered:
            if HAS_WINSOUND and os.path.exists(ALARM_AUDIO_PATH):
                winsound.PlaySound(ALARM_AUDIO_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                print("[ALERT] Drowsiness detected!")
            time.sleep(2)

    def stop_alarm(self):
        if self.alarm_triggered:
            self.alarm_triggered = False
            self.status_var.set("Alarm stopped.")
            self._set_bracket_color(self.COLOR_NEON)

    def send_alarm_email(self):
        if not EMAIL_CONFIGURED: return
        def _send():
            send_email_alert(subject="⚠️ Drowsiness Alert", body="Drowsiness was detected! Please check on the driver.")
        threading.Thread(target=_send, daemon=True).start()

    # --- Processing Core (Logic Unchanged) ---
    def update_frame(self):
        if not self.running: return

        try:
            ret, frame = self.video_capture.read()
        except Exception as exc:
            self.status_var.set(f"Camera error: {exc}")
            self.stop_detection()
            return

        if not ret:
            self.status_var.set("Camera disconnected! Retrying...")
            self.after(1000, self.update_frame)
            return

        frame = cv.flip(frame, 1)
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        gray = self.clahe.apply(gray)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))

        eyes_found = False

        for (x, y, w, h) in faces:
            cv.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            roi_gray = gray[y:y + h, x:x + w]
            roi_color = frame[y:y + h, x:x + w]

            eye_region_top = int(h * 0.20)
            eye_region_bottom = int(h * 0.50)

            left_zone = roi_gray[eye_region_top:eye_region_bottom, int(w * 0.05):int(w * 0.48)]
            right_zone = roi_gray[eye_region_top:eye_region_bottom, int(w * 0.52):int(w * 0.95)]
            left_zone_color = roi_color[eye_region_top:eye_region_bottom, int(w * 0.05):int(w * 0.48)]
            right_zone_color = roi_color[eye_region_top:eye_region_bottom, int(w * 0.52):int(w * 0.95)]

            min_eye_w = int(w * EYE_MIN_WIDTH_RATIO)
            max_eye_w = int(w * EYE_MAX_WIDTH_RATIO)

            zones_found = 0
            for zone_gray, zone_color in [(left_zone, left_zone_color), (right_zone, right_zone_color)]:
                if zone_gray.size == 0: continue
                eyes = self.eye_cascade.detectMultiScale(
                    zone_gray, scaleFactor=1.05, minNeighbors=EYE_MIN_NEIGHBORS,
                    minSize=(min_eye_w, min_eye_w), maxSize=(max_eye_w, max_eye_w))
                if len(eyes) > 0:
                    zones_found += 1
                    ex, ey, ew, eh = eyes[0]
                    cv.rectangle(zone_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

            if zones_found >= EYE_ZONES_REQUIRED:
                eyes_found = True

        if len(faces) > 0 and not eyes_found:
            self.consecutive_open_frames = 0
            if self.closed_eye_start_time is None:
                self.closed_eye_start_time = time.time()
                self.status_var.set("WARNING :: eyes closed, timing...")
            else:
                elapsed = time.time() - self.closed_eye_start_time
                self.status_var.set(f"WARNING :: eyes closed {elapsed:.1f}s")
                if elapsed >= EYE_CLOSED_THRESHOLD and not self.alarm_triggered:
                    self.status_var.set("ALARM :: WAKE UP")
                    self.alarm_triggered = True
                    self.alarm_trigger_count += 1
                    self.alert_count_var.set(f"ALERTS :: {self.alarm_trigger_count}")
                    self._set_bracket_color(self.COLOR_ALERT)
                    self.alarm_thread = threading.Thread(target=self.play_alarm, daemon=True)
                    self.alarm_thread.start()
                    if self.alarm_trigger_count > ALARM_COUNT_EMAIL_THRESHOLD:
                        self.send_alarm_email()
        elif len(faces) > 0 and eyes_found:
            self.consecutive_open_frames += 1
            if self.consecutive_open_frames >= CONSECUTIVE_OPEN_FRAMES_TO_RESET:
                self.closed_eye_start_time = None
                if self.alarm_triggered:
                    self.status_var.set("ACTIVE :: monitoring...")
                    self.stop_alarm()
        else:
            self.consecutive_open_frames = 0
            self.closed_eye_start_time = None
            if self.alarm_triggered:
                self.status_var.set("ACTIVE :: monitoring...")
                self.stop_alarm()

        # Update Indicators & Timers
        self.sidebar_canvas.itemconfig(self.indicator_ids["FACE"], fill=self.COLOR_OK if len(faces) > 0 else self.COLOR_OFF)
        self.sidebar_canvas.itemconfig(self.indicator_ids["EYES"], fill=self.COLOR_OK if eyes_found else self.COLOR_OFF)
        self.sidebar_canvas.itemconfig(self.indicator_ids["ALARM"], fill=self.COLOR_ALERT if self.alarm_triggered else self.COLOR_OFF)

        risk_fraction = 0.0
        if self.closed_eye_start_time is not None:
            risk_fraction = (time.time() - self.closed_eye_start_time) / EYE_CLOSED_THRESHOLD
        self._update_gauge(risk_fraction)

        if self.session_start_time is not None:
            session_elapsed = int(time.time() - self.session_start_time)
            mins, secs = divmod(session_elapsed, 60)
            self.sidebar_canvas.itemconfig(self.session_text_id, text=f"{mins:02d}:{secs:02d}")

        # Render to Tkinter
        rgb_image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        self.after(10, self.update_frame)


if __name__ == "__main__":
    app = DrowsinessDetectorApp()
    app.mainloop()