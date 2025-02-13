import asyncio
import os
import re
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import math
from youtubesearchpython import VideosSearch
import pkg_resources
import sys

# Code Owner: Amitred11
# Refactored by: Seuriin

# Constants & Initialization
YTDLP_PATH = shutil.which("yt-dlp")
if not YTDLP_PATH:
    messagebox.showerror("Error", "yt-dlp not installed (pip install yt-dlp)")
    exit()

OUTPUT_FOLDER = os.path.join(os.path.expanduser('~'), 'Downloads', 'YouTube Downloads')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

SELECTED_VIDEO_URL, SELECTED_VIDEO_TITLE = None, None
SCHEDULED_SEARCH = None
SEARCH_AFTER_MS = 500  # Debounce delay in milliseconds --> search delay
DOWNLOADING = False
ANGLE = 0

# --- Utility Functions ---

def is_ffmpeg_installed():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except FileNotFoundError:
        return False

def search_videos(query):
    try:
        videosSearch = VideosSearch(query, limit=7)
        return videosSearch.result().get('result', [])  # Handle missing 'result' key
    except Exception as e:
        print(f"Error searching videos: {e}")
        return []


def check_httpx_version():
    try:
        httpx_version = pkg_resources.get_distribution("httpx").version
        if pkg_resources.parse_version(httpx_version) > pkg_resources.parse_version("0.27.2"):
            return True, httpx_version
        else:
            return False, httpx_version
    except pkg_resources.DistributionNotFound:
        return False, None

def downgrade_httpx():
    try:
        subprocess.check_call(["pip", "install", "httpx==0.27.2"])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downgrading httpx: {e}")
        return False

def restart_application():
    try:
        # I'm not sure if this works
        python = sys.executable
        os.execl(python, python, *sys.argv)  # Replace current process -- important asf

    except OSError as e:
        print(f"Error restarting application: {e}")
        messagebox.showerror("Error", f"Failed to restart application: {e}")


# --- UI Functions ---

def update_status(text):
    status_label.config(text=text)

def on_video_select(video_url, video_title):
    global SELECTED_VIDEO_URL, SELECTED_VIDEO_TITLE
    SELECTED_VIDEO_URL, SELECTED_VIDEO_TITLE = video_url, video_title
    selected_label.config(text=f"Selected: {video_title}")

def download_and_convert(video_url, video_title, output_path, format_choice):
    global DOWNLOADING
    DOWNLOADING = True
    start_loading_animation()

    safe_title = "".join(c for c in video_title if c.isalnum() or c in " -_")
    update_status(f"Downloading: {safe_title}...")

    output_file = os.path.join(output_path, f'{safe_title}.{"mp4" if format_choice == "1" else "mp3"}')

    command = [YTDLP_PATH, "-o", output_file, "--no-progress"]
    if format_choice == "2":
        command.extend(["-x", "--audio-format", "mp3", video_url]) # dl only the best audio and converts to mp3
    else:
        command.extend(["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4", video_url])  # dl best quality video and audio

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        output = ""
        for line in process.stdout:
            print(line)
            output += line

        process.wait()
        return_code = process.returncode

        if "Postprocessing: ffprobe and ffmpeg not found" in output:
            update_status(f"Download Completed: {safe_title} (saved as .webm)")
            messagebox.showinfo("Download Complete", "Download successful, but saved as .webm because FFmpeg is not installed.")

        elif return_code == 0:
            update_status(f"Download Completed: {safe_title}")
        else:
            error_message = f"Download failed with return code: {return_code}\n\nFull output:\n{output}"
            update_status("Download failed!")
            messagebox.showerror("Error", error_message)


    except Exception as e:  # Catch any exceptions that might occur -- standard procd
        update_status("Download failed!")
        messagebox.showerror("Error", f"Download failed: {e}")

    finally:
        stop_loading_animation()


def on_download_button_click():
    if not SELECTED_VIDEO_URL:
        messagebox.showerror("Error", "Please select a video.")
        return

    update_status("Starting download...")
    threading.Thread(target=lambda: download_and_convert(SELECTED_VIDEO_URL, SELECTED_VIDEO_TITLE, OUTPUT_FOLDER, format_var.get()), daemon=True).start()


def perform_search(query):
    def search_and_update():
        results = search_videos(query)
        if not results:
            window.after(0, lambda: messagebox.showinfo("Info", "No results found."))
            return

        # Clear previous results
        for item in results_tree.get_children():
            results_tree.delete(item)

        # Insert to the treeview
        for result in results:
            window.after(0, lambda: results_tree.insert("", tk.END, values=(result['title'],result['link'])))

    threading.Thread(target=search_and_update, daemon=True).start()


def debounce_search(query):
    global SCHEDULED_SEARCH

    if SCHEDULED_SEARCH:
        window.after_cancel(SCHEDULED_SEARCH)

    SCHEDULED_SEARCH = window.after(SEARCH_AFTER_MS, lambda: perform_search(query))

def on_entry_change(event):
    debounce_search(url_entry.get())

def show_ffmpeg_message():
    def install_ffmpeg():
        os_name = os.name
        if os_name == 'nt':
            subprocess.Popen(['start', 'https://www.gyan.dev/ffmpeg/builds/'], shell=True)
        elif os_name == 'posix':
            subprocess.Popen(['open', 'https://ffmpeg.org/download.html'])
        d.destroy()

    def ignore_message():
        d.destroy()

    d = tk.Toplevel(window)
    d.title("FFmpeg Not Found")
    d.configure(bg="black")

    msg = tk.Label(d, text="FFmpeg missing! MP4/MP3 may not work.\nInstall FFmpeg?", padx=10, pady=10, bg="black", fg="white")
    msg.pack()

    install_btn = tk.Button(d, text="Install FFmpeg", command=install_ffmpeg, padx=10, pady=5, bg="#222", fg="white", relief=tk.FLAT)
    install_btn.pack(side=tk.LEFT, padx=5)

    ignore_btn = tk.Button(d, text="Ignore", command=ignore_message, padx=10, pady=5, bg="#222", fg="white", relief=tk.FLAT)
    ignore_btn.pack(side=tk.RIGHT, padx=5)

def on_tree_select(event):
    selected_item = results_tree.selection()
    if selected_item:
        item_data = results_tree.item(selected_item, 'values')
        on_video_select(item_data[1], item_data[0])  # URL, Title

# Loading Animation
def start_loading_animation():
    global ANGLE, DOWNLOADING
    DOWNLOADING = True
    ANGLE = 0
    loading_circle.pack(pady=5)  
    animate_loading()

def animate_loading():
    global ANGLE
    if not DOWNLOADING:
        return

    loading_circle.delete("all")
    x, y, r = 30, 30, 20

    for i in range(12):
        angle_rad = math.radians(ANGLE + (i * 30))
        dot_x = x + r * math.cos(angle_rad)
        dot_y = y + r * math.sin(angle_rad)
        color = "white" if i < 8 else "gray"
        loading_circle.create_oval(dot_x - 3, dot_y - 3, dot_x + 3, dot_y + 3, fill=color, outline=color)

    ANGLE = (ANGLE + 10) % 360
    window.after(100, animate_loading)

def stop_loading_animation():
    global DOWNLOADING
    DOWNLOADING = False
    loading_circle.pack_forget()

# --- GUI Setup ---
window = tk.Tk()
window.title("YouTube Downloader")
window.geometry("700x400") 
window.resizable(True, True)
window.configure(bg="black")

# Style
style = ttk.Style(window)
style.theme_use("default")
style.configure("Treeview", background="#333", foreground="white", fieldbackground="#333", bordercolor="#000000")
style.map("Treeview", background=[("selected", "#555")])

# --- UI Elements ---
input_frame = tk.Frame(window, bg="black")
input_frame.pack(pady=5, fill="x")  

tk.Label(input_frame, text="Search YouTube:", font=("Arial", 12), fg="white", bg="black").pack(side="left", padx=5)
url_entry = tk.Entry(input_frame, width=40, font=("Arial", 12), bg="#333", fg="white", insertbackground="white")
url_entry.pack(side="left", padx=5, fill="x", expand=True)
url_entry.bind("<KeyRelease>", on_entry_change)

results_tree_frame = tk.Frame(window, bg="black")
results_tree_frame.pack(pady=2, fill="both", expand=True)  

results_tree = ttk.Treeview(results_tree_frame, columns=("Title", "Link"), show="headings", style="Treeview", height=5) 
results_tree.heading("Title", text="Title")
results_tree.heading("Link", text="Link")

results_tree.column("Title", width=600)
results_tree.column("Link", width=1)
results_tree.pack(side="left", fill="both", expand=True)

tree_scroll = ttk.Scrollbar(results_tree_frame, orient="vertical", command=results_tree.yview)
tree_scroll.pack(side="right", fill="y")
results_tree.configure(yscrollcommand=tree_scroll.set)

results_tree.bind("<ButtonRelease-1>", on_tree_select)

selected_label = tk.Label(window, text="No video selected", font=("Arial", 12), fg="white", bg="black")
selected_label.pack(pady=2)  

format_frame = tk.Frame(window, bg="black")
format_frame.pack(pady=2)  

tk.Label(format_frame, text="Format:", font=("Arial", 12), fg="white", bg="black").pack(side="left", padx=5)
format_var = tk.StringVar(value="1")
tk.Radiobutton(format_frame, text="MP4 Video", variable=format_var, value="1", font=("Arial", 12), bg="black", fg="white", selectcolor="gray").pack(side="left")
tk.Radiobutton(format_frame, text="MP3 Audio", variable=format_var, value="2", font=("Arial", 12), bg="black", fg="white", selectcolor="gray").pack(side="left")

download_button = tk.Button(window, text="Download", command=on_download_button_click, font=("Arial", 12), bg="#222", fg="white", relief=tk.FLAT)
download_button.pack(pady=5) 

loading_circle = tk.Canvas(window, width=60, height=60, bg="black", highlightthickness=0)
loading_circle.pack_forget()

status_label = tk.Label(window, text="", font=("Arial", 12), fg="white", bg="black")
status_label.pack(pady=2) 

# --- Initialization ---

if not is_ffmpeg_installed():
    show_ffmpeg_message()


# Check httpx version and downgrade if necessary -- for the search function to work
is_higher, httpx_version = check_httpx_version()
if is_higher:
    result = messagebox.askyesno(
        "httpx Version Issue",
        f"Your httpx version ({httpx_version}) is higher than 0.27.2, the search function would NOT work.  Downgrading is recommended.\nDowngrade to version 0.27.2 now and restart the application?",
    )
    if result:
        if downgrade_httpx():
            messagebox.showinfo("Downgrade Successful", "httpx downgraded successfully.  The application will now restart.")
            window.after(200, restart_application)  # 200ms restart delay
        else:
            messagebox.showerror("Downgrade Failed", "Failed to downgrade httpx. The application may not work correctly.")



# --- Run Application ---
window.mainloop()
