import psutil
import time
import os
import sys
import winreg as reg
import threading
import tkinter as tk
from tkinter import ttk
import hashlib
import pystray
import webbrowser
from PIL import Image, ImageDraw

tray_icon = None

def is_minecraft_running():
    """Check if javaw.exe (Minecraft) is running."""
    for process in psutil.process_iter(['name']):
        if process.info['name'] == 'javaw.exe':
            return True
    return False

def calculate_checksum(data):
    """Calculate a checksum for the given data."""
    return hashlib.sha256(data.encode()).hexdigest()

def get_playtime_file_path():
    """Get the path to the playtime file in the AppData directory."""
    appdata_dir = os.getenv('APPDATA')
    playtime_dir = os.path.join(appdata_dir, 'MineTimer')
    if not os.path.exists(playtime_dir):
        os.makedirs(playtime_dir)
    return os.path.join(playtime_dir, 'minecraft_playtime.txt')

def write_playtime(file_path, playtime):
    """Write the playtime and checksum to the file."""
    data = str(playtime)
    checksum = calculate_checksum(data)
    with open(file_path, 'w') as file:
        file.write(f"{data}\n{checksum}")

def read_playtime(file_path):
    """Read the playtime from the file and verify the checksum."""
    if not os.path.exists(file_path):
        write_playtime(file_path, 0)
        return 0

    with open(file_path, 'r') as file:
        lines = file.readlines()
        if len(lines) != 2:
            write_playtime(file_path, 0)
            return 0

        data, checksum = lines
        data = data.strip()
        checksum = checksum.strip()

        if calculate_checksum(data) != checksum:
            write_playtime(file_path, 0)
            return 0

        return int(data)

def record_playtime(file_path, interval=1):
    """Record the playtime of Minecraft."""
    playtime_lock = threading.Lock()
    playtime = read_playtime(file_path)

    try:
        while True:
            if is_minecraft_running():
                with playtime_lock:
                    playtime += interval
                    write_playtime(file_path, playtime)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Stopped recording playtime.")

def format_playtime(seconds):
    """Format playtime in seconds to hours, minutes, and seconds."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours}h {minutes}m {seconds}s"

def update_status_label(root, status_label, interval=1):
    """Update the status label in the GUI."""
    if is_minecraft_running():
        status_label.config(text="Minecraft: Open", foreground="green")
    else:
        status_label.config(text="Minecraft: Closed", foreground="red")
    root.after(interval * 1000, update_status_label, root, status_label, interval)

def update_playtime_label(root, file_path, label, interval=1):
    """Update the playtime label in the GUI."""
    playtime = read_playtime(file_path)
    formatted_playtime = format_playtime(playtime)
    label.config(text=f"Playtime: {formatted_playtime}")
    root.after(interval * 1000, update_playtime_label, root, file_path, label, interval)

def start_recording(file_path, interval, playtime_label, status_label):
    """Start the recording and updating in the main thread."""
    playtime_thread = threading.Thread(target=record_playtime, args=(file_path, interval))
    playtime_thread.daemon = True
    playtime_thread.start()

    update_status_label(root, status_label, interval)
    update_playtime_label(root, file_path, playtime_label, interval)

def get_startup_config_path():
    """Get the path to the startup configuration file in the AppData directory."""
    appdata_dir = os.getenv('APPDATA')
    config_dir = os.path.join(appdata_dir, 'MineTimer')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return os.path.join(config_dir, 'startup-config.txt')

def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    """Create a rounded rectangle on the canvas."""
    points = [
        x1 + radius, y1,
        x1 + radius, y1,
        x2 - radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, **kwargs, smooth=True)

def create_image():
    """Create an image for the system tray icon."""
    script_dir = get_script_directory()
    icon_path = os.path.join(script_dir, "icon.ico")
    return Image.open(icon_path)

def on_quit(icon, item):
    """Quit the application."""
    icon.stop()
    os._exit(0)

def show_window(icon, item):
    """Show the main window."""
    root.deiconify()

def run_tray_icon():
    """Run the system tray icon."""
    global tray_icon
    if tray_icon is None:
        image = create_image()
        menu = pystray.Menu(
            pystray.MenuItem('View playtime', show_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Website', open_website),
            pystray.MenuItem('GitHub', open_github),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit', on_quit)
        )
        tray_icon = pystray.Icon("MineTimer", image, "MineTimer", menu)
        tray_icon.run()

def hide_window():
    """Hide the main window and run the system tray icon."""
    root.withdraw()

def open_website():
    webbrowser.open("https://www.goofert.org/")

def open_github():
    webbrowser.open("https://github.com/Goofert42/MineTimer")
    
def add_to_startup():
    """Add the application to Windows startup."""
    try:
        if getattr(sys, 'frozen', False):
            path = os.path.dirname(sys.executable)
        else:
            path = os.path.dirname(os.path.realpath(__file__))
        
        s_name = "mine-timer.exe"
        address = os.path.join(path, s_name)
        
        address_with_args = f'"{address}" --startup'
        
        key = reg.HKEY_CURRENT_USER
        key_value = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        
        with reg.OpenKey(key, key_value, 0, reg.KEY_ALL_ACCESS) as open_key:
            reg.SetValueEx(open_key, "MineTimer", 0, reg.REG_SZ, address_with_args)
        
        print("MineTimer added to startup successfully.")
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except PermissionError as e:
        print(f"Permission denied: {e}")
    except Exception as e:
        print(f"Failed to add to startup: {e}")

def get_script_directory():
    """Get the directory of the running script or executable."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)

def create_gui(startup=False):
    """Create the GUI to display playtime."""
    global root
    root = tk.Tk()
    root.resizable(width=False, height=False)
    root.title("MineTimer")

    script_dir = get_script_directory()
    icon_path = os.path.join(script_dir, "icon.ico")
    root.iconbitmap(icon_path)

    style = ttk.Style()
    style.configure("TFrame", background="#2e2e2e")
    style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=("Helvetica", 16))
    style.configure("TButton", background="#2e2e2e", foreground="#ffffff", font=("Helvetica", 12))

    mainframe = ttk.Frame(root, padding="20 20 20 20", style="TFrame")
    mainframe.grid(column=0, row=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    status_canvas = tk.Canvas(mainframe, width=300, height=60, bg="#2e2e2e", highlightthickness=0)
    status_canvas.grid(column=0, row=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

    create_rounded_rectangle(status_canvas, 10, 10, 290, 50, radius=20, fill="#1e1e1e", outline="")

    status_label = ttk.Label(status_canvas, text="Minecraft: Closed", style="TLabel", foreground="red")
    status_label.place(x=150, y=30, anchor="center")

    playtime_canvas = tk.Canvas(mainframe, width=300, height=100, bg="#2e2e2e", highlightthickness=0)
    playtime_canvas.grid(column=0, row=1, sticky=(tk.W, tk.E, tk.N, tk.S))

    create_rounded_rectangle(playtime_canvas, 10, 10, 290, 90, radius=20, fill="#1e1e1e", outline="")

    playtime_label = ttk.Label(playtime_canvas, text="Playtime: 0h 0m 0s", style="TLabel")
    playtime_label.place(x=150, y=50, anchor="center")
    
    playtime_file = get_playtime_file_path()
    start_recording(playtime_file, 1, playtime_label, status_label)

    root.protocol("WM_DELETE_WINDOW", hide_window)

    if startup:
        hide_window()

    root.mainloop()

if __name__ == "__main__":
    add_to_startup()
    startup = "--startup" in sys.argv
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()
    create_gui(startup)