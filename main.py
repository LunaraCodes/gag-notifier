import requests
import time
import threading
from plyer import notification
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pystray
from PIL import Image, ImageDraw
import json
import os
import webbrowser
import sys

# Constants
SEEDS_URL = "https://gagapi.onrender.com/seeds"
GEAR_URL = "https://gagapi.onrender.com/gear"
CONFIG_FILE = "gag_notifier_config.json"
GITHUB_URL = "https://github.com/LunaraCodes/gag-notifier"

# Global variables
running = True
restock_history = {}
notification_history = []
seed_vars = {}
gear_vars = {}
tray_icon = None

# Default items
FULL_SEEDS = [
    {"name": "Carrot"}, {"name": "Strawberry"}, {"name": "Blueberry"},
    {"name": "Orange Tulip"}, {"name": "Tomato"}, {"name": "Corn"},
    {"name": "Daffodil"}, {"name": "Watermelon"}, {"name": "Pumpkin"},
    {"name": "Apple"}, {"name": "Bamboo"}, {"name": "Coconut"},
    {"name": "Cactus"}, {"name": "Dragon Fruit"}, {"name": "Mango"},
    {"name": "Grape"}, {"name": "Mushroom"}, {"name": "Pepper"},
    {"name": "Cacao"}, {"name": "Beanstalk"}, {"name": "Ember Lily"},
    {"name": "Sugar Apple"}, {"name": "Burning Bud"}, {"name": "Giant Pinecone"},
    {"name": "Elder Strawberry"}
]

FULL_GEAR = [
    {"name": "Watering Can"}, {"name": "Trowel"}, {"name": "Trading Ticket"},
    {"name": "Recall Wrench"}, {"name": "Basic Sprinkler"}, {"name": "Advanced Sprinkler"},
    {"name": "Medium Treat"}, {"name": "Medium Toy"}, {"name": "Godly Sprinkler"},
    {"name": "Magnifying Glass"}, {"name": "Master Sprinkler"}, {"name": "Cleaning Spray"},
    {"name": "Favourite Tool"}, {"name": "Harvest Tool"}, {"name": "Friendship Pot"},
    {"name": "Level Up Lolllipop"}, {"name": "Grandmaster sprinkler"}
]

# Utility functions
def log(message, is_restock=False):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    log_message = f"{timestamp} {message}"
    print(log_message)
    if is_restock:
        notification_history.append(log_message)

def show_notification(title, message):
    notification.notify(
        title=title,
        message=message,
        timeout=5
    )

def fetch_stock(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log(f"Failed to fetch from {url}: {e}", False)
        show_notification("❌ GAG Notifier Error", str(e))
        return None

def update_restock_history(item_name):
    now = datetime.now()
    if item_name not in restock_history:
        restock_history[item_name] = []
    restock_history[item_name].append(now)
    restock_history[item_name] = restock_history[item_name][-5:]

def get_restock_text(item_name):
    history = restock_history.get(item_name, [])
    if len(history) < 2:
        return "New item!"
    avg_seconds = (history[-1] - history[0]).total_seconds() / (len(history)-1)
    last_restock = (datetime.now() - history[-1]).seconds // 60
    return f"{last_restock}m ago (Avg: {round(avg_seconds/60)}m)"

def notify_items(category, current_stock):
    selected_items = []
    var_dict = seed_vars if category == "seeds" else gear_vars
    
    for item in current_stock:
        var = var_dict.get(item["name"])
        if var and var.get():
            selected_items.append(item)
            title = f"🌿 {category.capitalize()} Stock Update"
            message = f"{item['name']} is in stock!"
            show_notification(title, message)
            update_restock_history(item["name"])
            log(f"{item['name']} restocked!", True)
    
    if not selected_items:
        show_notification("ℹ️ GAG Notifier", f"No selected {category} items found in stock")

def check_all():
    categories = {"seeds": SEEDS_URL, "gear": GEAR_URL}
    for category, url in categories.items():
        stock = fetch_stock(url)
        if stock:
            notify_items(category, stock)

def seconds_until_next_5min():
    now = datetime.now()
    next_minute = (now.minute // 5 + 1) * 5
    next_time = now.replace(minute=next_minute % 60, second=0, microsecond=0)
    if next_minute >= 60:
        next_time = next_time.replace(hour=now.hour+1)
    delta = (next_time - now).total_seconds()
    return max(0, int(delta))

def countdown_loop():
    while running:
        secs_left = seconds_until_next_5min()
        if root.winfo_exists():  # Check if window still exists
            root.after(0, lambda s=secs_left: countdown_var.set(f"Next check in: {s}s"))
        time.sleep(1)

def polling_loop():
    while running:
        wait = seconds_until_next_5min()
        time.sleep(wait)
        if not running:
            break
        check_all()

def setup_tray_icon():
    global tray_icon
    
    def restore_from_tray(icon, item):
        icon.stop()
        root.after(0, root.deiconify)
    
    def on_quit(icon, item):
        global running
        running = False
        save_config()
        icon.stop()
        root.after(0, root.destroy)
    
    image = Image.new('RGB', (64, 64), (40, 90, 140))
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 16, 48, 48), fill=(255, 255, 255))
    
    menu = pystray.Menu(
        pystray.MenuItem('Show', restore_from_tray),
        pystray.MenuItem('Quit', on_quit)
    )
    
    tray_icon = pystray.Icon("GAG Notifier", image, "GAG Notifier", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

def on_minimize(event=None):
    root.withdraw()
    if tray_icon is None:
        setup_tray_icon()
    else:
        tray_icon.visible = True

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit GAG Notifier?"):
        global running
        running = False
        save_config()
        if tray_icon is not None:
            tray_icon.stop()
        root.destroy()

def build_checkbox_grid(parent, items, var_dict):
    container = ttk.Frame(parent)
    container.pack(fill="both", expand=True, padx=5, pady=5)
    
    num_columns = 3
    items_per_column = (len(items) + num_columns - 1) // num_columns
    
    for col in range(num_columns):
        column_frame = ttk.Frame(container)
        column_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        start_idx = col * items_per_column
        end_idx = min((col + 1) * items_per_column, len(items))
        
        for item in items[start_idx:end_idx]:
            frame = ttk.Frame(column_frame)
            frame.pack(fill="x", pady=2)
            
            var = tk.BooleanVar(value=True)
            var_dict[item["name"]] = var
            
            cb = ttk.Checkbutton(
                frame, 
                text=item["name"], 
                variable=var
            )
            cb.pack(side="left", anchor="w")
            
            time_label = ttk.Label(
                frame, 
                text="", 
                width=25,
                anchor="e"
            )
            time_label.pack(side="right")
            
            if item["name"] in restock_history:
                time_label.config(text=get_restock_text(item["name"]))

def apply_theme():
    style = ttk.Style()
    style.theme_use('clam')
    
    bg = "#f5f5f5"
    fg = "#333333"
    accent = "#2c5e8a"
    frame_bg = "#ffffff"
    text_bg = "#ffffff"
    tab_bg = "#e0e0e0"
    tab_active = "#2c5e8a"

    style.configure('.', 
        background=bg, 
        foreground=fg,
        font=('Segoe UI', 9)
    )
    style.configure('TFrame', background=bg)
    style.configure('TLabel', background=bg, foreground=fg)
    
    style.configure('TButton', 
        background=accent, 
        foreground="white",
        borderwidth=0,
        focusthickness=0,
        focuscolor='none',
        padding=6
    )
    style.map('TButton',
        background=[('active', accent), ('pressed', accent)],
        foreground=[('active', 'white'), ('pressed', 'white')]
    )
    
    style.configure('TNotebook', background=tab_bg)
    style.configure('TNotebook.Tab', 
        background=tab_bg, 
        foreground=fg, 
        padding=[10, 4],
        font=('Segoe UI', 9, 'bold')
    )
    style.map('TNotebook.Tab',
        background=[('selected', bg)],
        foreground=[('selected', accent)]
    )
    
    root.configure(background=bg)
    
    if hasattr(root, 'log_text'):
        root.log_text.config(
            background=text_bg,
            foreground=fg,
            insertbackground=fg,
            selectbackground=accent,
            selectforeground='white',
            relief='flat',
            borderwidth=0
        )

def save_config():
    config = {
        'selected_seeds': {name: var.get() for name, var in seed_vars.items()},
        'selected_gear': {name: var.get() for name, var in gear_vars.items()}
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            
            for name, selected in config.get('selected_seeds', {}).items():
                if name in seed_vars:
                    seed_vars[name].set(selected)
            
            for name, selected in config.get('selected_gear', {}).items():
                if name in gear_vars:
                    gear_vars[name].set(selected)
                    
    except Exception as e:
        log(f"Error loading config: {e}", False)

def open_github():
    webbrowser.open(GITHUB_URL)

def create_ui():
    global root, countdown_var, log_text

    root = tk.Tk()
    root.title("GAG Notifier v2.0")
    root.geometry("800x700")
    root.minsize(600, 600)

    # Setup minimize to tray
    root.protocol('WM_DELETE_WINDOW', on_closing)
    root.bind('<Unmap>', lambda e: on_minimize() if e.widget is root else None)

    main_frame = ttk.Frame(root)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    header_frame = ttk.Frame(main_frame)
    header_frame.pack(fill="x", pady=(0, 10))
    
    logo_frame = ttk.Frame(header_frame)
    logo_frame.pack(side="left", fill="x", expand=True)
    
    ttk.Label(logo_frame, 
             text="🌿 GAG Stock Notifier", 
             font=('Segoe UI', 14, 'bold')).pack(side="left")
    
    control_frame = ttk.Frame(header_frame)
    control_frame.pack(side="right")
    
    ttk.Button(control_frame, 
               text="GitHub", 
               command=open_github).pack(side="left", padx=3)

    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill="both", expand=True)

    seeds_tab = ttk.Frame(notebook)
    gear_tab = ttk.Frame(notebook)
    log_tab = ttk.Frame(notebook)

    notebook.add(seeds_tab, text="🌱 Seeds")
    notebook.add(gear_tab, text="⚙️ Gear")
    notebook.add(log_tab, text="📜 Log")

    build_checkbox_grid(seeds_tab, FULL_SEEDS, seed_vars)
    build_checkbox_grid(gear_tab, FULL_GEAR, gear_vars)

    log_frame = ttk.Frame(log_tab)
    log_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    log_text = scrolledtext.ScrolledText(
        log_frame, 
        wrap=tk.WORD, 
        font=('Consolas', 9),
        padx=5,
        pady=5
    )
    log_text.pack(fill="both", expand=True)
    root.log_text = log_text
    
    status_frame = ttk.Frame(main_frame)
    status_frame.pack(fill="x", pady=(10, 0))
    
    countdown_var = tk.StringVar(value="Next check in: --")
    ttk.Label(status_frame, 
              textvariable=countdown_var, 
              font=('Segoe UI', 9)).pack(side="left")
    
    ttk.Button(status_frame, 
               text="Check Now", 
               command=check_all).pack(side="right")

    load_config()
    apply_theme()

    def update_log_display():
        log_text.config(state='normal')
        log_text.delete(1.0, tk.END)
        log_text.insert(tk.END, "\n".join(notification_history[-50:]))
        log_text.config(state='disabled')
        log_text.see(tk.END)
        root.after(5000, update_log_display)

    update_log_display()

    threading.Thread(target=countdown_loop, daemon=True).start()
    threading.Thread(target=polling_loop, daemon=True).start()

    return root

if __name__ == "__main__":
    root = create_ui()
    root.mainloop()