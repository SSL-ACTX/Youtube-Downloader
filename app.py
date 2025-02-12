import os
import subprocess
import shutil
import tkinter as tk
from tkinter import messagebox, ttk
import threading
import re
import math
from googleapiclient.discovery import build

# Set up YouTube API client
API_KEY = 'YOUR_API_KEY' # Replace with your actual API key
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Find yt-dlp executable
YTDLP_PATH = shutil.which("yt-dlp")
if not YTDLP_PATH:
    messagebox.showerror("Error", "yt-dlp is not installed. Please install it using 'pip install yt-dlp'")
    exit()

# Get system Downloads folder
def get_download_folder():
    output_folder = os.path.join(os.path.expanduser('~'), 'Downloads', 'YouTube Downloads')
    os.makedirs(output_folder, exist_ok=True)
    return output_folder

# Function to fetch video details from the YouTube API
def get_video_details(video_url):
    video_id = video_url.split('v=')[-1]
    request = youtube.videos().list(part='snippet', id=video_id)
    response = request.execute()
    
    if 'items' in response and response['items']:
        return response['items'][0]['snippet']['title']
    else:
        return None

# Circular loading animation
def start_loading_animation():
    global angle
    angle = 0
    loading_circle.pack(pady=10)
    animate_loading()

def animate_loading():
    global angle
    loading_circle.delete("all")
    x, y, r = 30, 30, 20  # Center and radius of the circle

    # Create spinning effect
    for i in range(12):  # 12 dots in a circular pattern
        angle_rad = math.radians(angle + (i * 30))
        dot_x = x + r * math.cos(angle_rad)
        dot_y = y + r * math.sin(angle_rad)
        color = "white" if i < 8 else "gray"  # Bright dots for effect
        loading_circle.create_oval(dot_x - 3, dot_y - 3, dot_x + 3, dot_y + 3, fill=color, outline=color)

    angle = (angle + 10) % 360
    if downloading:
        window.after(100, animate_loading)  # Continue animation

def stop_loading_animation():
    global downloading
    downloading = False
    loading_circle.pack_forget()

# Function to ask if user wants to open file
def ask_open_file(file_path):
    answer = messagebox.askyesno("Open File", "Download completed! Do you want to open the file?")
    if answer:
        os.startfile(file_path)  # Open file with default media player

# Function to download video/audio
def download_and_convert(url, output_path, format_choice, status_label):
    global downloading
    downloading = True
    start_loading_animation()  # Start circular loading animation

    video_title = get_video_details(url)
    if not video_title:
        stop_loading_animation()
        messagebox.showerror("Error", "Invalid URL or video not found.")
        return
    
    safe_title = "".join(c for c in video_title if c.isalnum() or c in " -_")
    status_label.config(text=f"Downloading: {safe_title}...")
    
    output_file = os.path.join(output_path, f'{safe_title}.mp4' if format_choice == "1" else f'{safe_title}.mp3')
    
    command = [
        YTDLP_PATH,
        "-o", output_file,
        "-f", "bestaudio" if format_choice == "2" else "best",
        "--no-progress"  # Hides yt-dlp console progress
    ]
    
    if format_choice == "2":
        command.extend(["--extract-audio", "--audio-format", "mp3"])
    
    command.append(url)
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    for line in process.stdout:
        pass  # No progress updates, only animation is visible

    process.wait()

    stop_loading_animation()  # Stop animation

    if process.returncode == 0:
        status_label.config(text=f"Download Completed: {safe_title}")
        ask_open_file(output_file)  # Ask if user wants to open file
    else:
        status_label.config(text="Download failed!")
        messagebox.showerror("Error", "Download failed. Please check the URL and try again.")

# Download button action
def on_download_button_click():
    url = url_entry.get()
    choice = format_var.get()
    output_folder = get_download_folder()
    os.makedirs(output_folder, exist_ok=True)
    
    if not url:
        messagebox.showerror("Error", "Please enter a YouTube URL.")
        return
    
    status_label.config(text="Starting download...")
    
    threading.Thread(target=download_and_convert, args=(url, output_folder, choice, status_label), daemon=True).start()

# GUI Setup
window = tk.Tk()
window.title("YouTube Downloader")
window.geometry("500x400")
window.resizable(False, False)
window.configure(bg="black")

# Title
tk.Label(window, text="YouTube Downloader", font=("Arial", 16, "bold"), fg="white", bg="black").pack(pady=10)

# URL Entry
tk.Label(window, text="Enter YouTube URL:", font=("Arial", 12), fg="white", bg="black").pack(pady=5)
url_entry = tk.Entry(window, width=50, font=("Arial", 12))
url_entry.pack(pady=5)

# Format Selection
tk.Label(window, text="Choose format:", font=("Arial", 12), fg="white", bg="black").pack(pady=5)
format_var = tk.StringVar(value="1")
radio1 = tk.Radiobutton(window, text="MP4 Video", variable=format_var, value="1", font=("Arial", 12), bg="black", fg="white", selectcolor="gray")
radio1.pack()
radio2 = tk.Radiobutton(window, text="MP3 Audio", variable=format_var, value="2", font=("Arial", 12), bg="black", fg="white", selectcolor="gray")
radio2.pack()

# Circular Loading Canvas
loading_circle = tk.Canvas(window, width=60, height=60, bg="black", highlightthickness=0)
loading_circle.pack_forget()  # Initially hidden

# Status Label
status_label = tk.Label(window, text="", font=("Arial", 12), fg="white", bg="black")
status_label.pack(pady=5)

# Download Button
def on_enter(e):
    download_button.config(bg="#444")

def on_leave(e):
    download_button.config(bg="#222")

download_button = tk.Button(window, text="Download & Convert", command=on_download_button_click, font=("Arial", 12), bg="#222", fg="white", relief=tk.FLAT)
download_button.bind("<Enter>", on_enter)
download_button.bind("<Leave>", on_leave)
download_button.pack(pady=20)

# Run application
window.mainloop()
