import socket
import pygame
import threading
import cv2
import os
import numpy as np
import datetime
import time
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog

# Global Variables
base_folder = ""
gunshot_sound_path = ""
session_folder = ""
output_folder = ""
reference_path = ""
summary_image_path = ""
student_name = ""
student_sessions_folder = ""
camera_port = 0  # Will be set by user

trigger_event = threading.Event()
stop_event = threading.Event()

listener_thread = None
laser_thread = None

# --- Function to get user input ---
def initialize_user_settings():
    global base_folder, gunshot_sound_path

    messagebox.showinfo("Instruction", "Please select the folder named 'gun_demo' that contains boom1.mp3")

    base_folder = filedialog.askdirectory(title="Select gun_demo Folder")
    if not base_folder:
        messagebox.showerror("Missing Folder", "You must select the gun_demo folder.")
        root.destroy()
        return False

    gunshot_sound_path = os.path.join(base_folder, "boom1.mp3")
    if not os.path.exists(gunshot_sound_path):
        messagebox.showerror("Missing File", "boom1.mp3 not found in selected folder.")
        root.destroy()
        return False

    return True

def setup_student_session():
    global student_name, session_folder, output_folder, reference_path, summary_image_path, student_sessions_folder, camera_port

    student_name = simpledialog.askstring("Student Name", "Enter student name for this session:")
    if not student_name:
        messagebox.showerror("Missing Info", "Student name is required.")
        return False

    try:
        camera_port = int(simpledialog.askstring("Camera Port", "Enter the camera port number (e.g., 0 or 1):"))
    except (TypeError, ValueError):
        messagebox.showerror("Invalid Input", "Camera port must be a number.")
        return False

    student_sessions_folder = os.path.join(base_folder, "student_sessions", student_name)
    os.makedirs(student_sessions_folder, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_folder = os.path.join(student_sessions_folder, f"session_{timestamp}")
    output_folder = os.path.join(session_folder, "green_dot_frames")
    reference_path = os.path.join(session_folder, "reference.jpg")
    summary_image_path = os.path.join(session_folder, "laser_summary.jpg")

    os.makedirs(output_folder, exist_ok=True)

    return True

# --- Core Detection and Summary Function ---
def detect_laser_and_summarize():
    cap = cv2.VideoCapture(camera_port)
    frame_count = 0
    saved_count = 0
    laser_active = False
    laser_coords = []

    pygame.init()
    gunshot_sound = pygame.mixer.Sound(gunshot_sound_path)

    lower_green = (40, 100, 100)
    upper_green = (80, 255, 255)

    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print(" Frame grab failed.")
                time.sleep(0.1)
                continue

            if frame_count == 0:
                cv2.imwrite(reference_path, frame)

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, lower_green, upper_green)
            green_pixel_count = cv2.countNonZero(mask)

            if green_pixel_count > 50:
                if not laser_active:
                    filename = os.path.join(output_folder, f"frame_{frame_count}.jpg")
                    cv2.imwrite(filename, frame)
                    saved_count += 1
                    laser_active = True
                    print(f" Saved: {filename}")
                    trigger_event.clear()
            else:
                laser_active = False

            frame_count += 1

            cv2.imshow("Live Feed", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                stop_event.set()
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    image_files = sorted([
        os.path.join(output_folder, f)
        for f in os.listdir(output_folder)
        if f.lower().endswith(".jpg")
    ])

    if len(image_files) == 0:
        print("No laser shots detected.")
        return

    for path in image_files:
        image = cv2.imread(path)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_green, upper_green)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest = max(contours, key=cv2.contourArea)
            (x, y), radius = cv2.minEnclosingCircle(largest)
            laser_coords.append((int(x), int(y)))
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, _, _, maxLoc = cv2.minMaxLoc(gray)
            laser_coords.append(maxLoc)

    reference_image = cv2.imread(reference_path)
    output_image = reference_image.copy()

    for i, (x, y) in enumerate(laser_coords):
        cv2.circle(output_image, (x, y), 8, (0, 0, 255), 2)
        cv2.putText(output_image, f"Shot {i+1}", (x+10, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)

    session_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(output_image, f"Student: {student_name}", (20, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.putText(output_image, f"Date: {session_date}", (20, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imwrite(summary_image_path, output_image)
    print(f"Summary image saved at: {summary_image_path}")

    plt.imshow(cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB))
    plt.title(f"Laser Dots for {student_name}")
    plt.axis('off')
    plt.show()

# --- Trigger listener with port reuse fix ---
def listen_for_trigger():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(1.0)
    sock.bind(("0.0.0.0", 424))
    print(" Waiting for trigger...")

    pygame.init()
    pygame.mixer.init()
    if not os.path.exists(gunshot_sound_path):
        print("Gunshot sound file not found!")
        return
    gunshot_sound = pygame.mixer.Sound(gunshot_sound_path)

    try:
        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode().strip()
                print(f"Received from {addr}: {message}")

                if "TRIGGER" in message.upper():
                    gunshot_sound.play()
                    trigger_event.set()
            except socket.timeout:
                continue
    except Exception as e:
        print(f"Trigger error: {e}")
    finally:
        sock.close()

# --- GUI Button Functions ---
def start_session():
    global listener_thread, laser_thread

    if not setup_student_session():
        return

    stop_event.clear()
    trigger_event.clear()

    listener_thread = threading.Thread(target=listen_for_trigger, daemon=True)
    laser_thread = threading.Thread(target=detect_laser_and_summarize, daemon=True)

    listener_thread.start()
    laser_thread.start()

    messagebox.showinfo("Started", f"Training session started for {student_name}.")

def stop_session():
    stop_event.set()

    if listener_thread and listener_thread.is_alive():
        listener_thread.join(timeout=1)

    if laser_thread and laser_thread.is_alive():
        laser_thread.join(timeout=1)

    pygame.quit()

    messagebox.showinfo("Stopped", f"Session stopped for {student_name}.")

def view_frames():
    if os.path.exists(output_folder):
        os.startfile(output_folder)
    else:
        messagebox.showerror("Missing", "No frames found yet!")

def view_summary():
    if os.path.exists(summary_image_path):
        os.startfile(summary_image_path)
    else:
        messagebox.showerror("Missing", "No summary image found yet!")

def view_student_sessions():
    if not student_name:
        messagebox.showerror("Error", "No student selected yet!")
        return

    sessions_path = os.path.join(base_folder, "student_sessions", student_name)
    if os.path.exists(sessions_path):
        os.startfile(sessions_path)
    else:
        messagebox.showerror("Missing", f"No sessions found for {student_name}!")

# --- Start GUI ---
root = tk.Tk()
root.title("Laser Shooting System")
root.geometry("400x350")

tk.Label(root, text="Laser Shooting Trainer", font=("Arial", 16)).pack(pady=10)

if initialize_user_settings():
    tk.Button(root, text=" Start Session", width=30, command=start_session).pack(pady=5)
    tk.Button(root, text=" Stop Session", width=30, command=stop_session).pack(pady=5)
    tk.Button(root, text=" View Laser Frames", width=30, command=view_frames).pack(pady=5)
    tk.Button(root, text="View Summary Image", width=30, command=view_summary).pack(pady=5)
    tk.Button(root, text="View All Student Sessions", width=30, command=view_student_sessions).pack(pady=5)
    tk.Button(root, text=" Exit", width=30, command=root.destroy).pack(pady=10)

root.mainloop()