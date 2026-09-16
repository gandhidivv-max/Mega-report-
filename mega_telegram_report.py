import os
import json
import time
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from mega import Mega

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STATE_FILE = "mega_state.json"
video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm', '.3gp', '.m4v')

def get_all_mega_credentials():
    accounts = []
    e1 = os.environ.get("MEGA_EMAIL_1") or os.environ.get("MEGA_EMAIL")
    p1 = os.environ.get("MEGA_PASSWORD_1") or os.environ.get("MEGA_PASSWORD")
    if e1 and p1:
        accounts.append({"email": e1, "pass": p1, "name": "Account 1"})

    e2 = os.environ.get("MEGA_EMAIL_2")
    p2 = os.environ.get("MEGA_PASSWORD_2")
    if e2 and p2:
        accounts.append({"email": e2, "pass": p2, "name": "Account 2"})

    e3 = os.environ.get("MEGA_EMAIL_3")
    p3 = os.environ.get("MEGA_PASSWORD_3")
    if e3 and p3:
        accounts.append({"email": e3, "pass": p3, "name": "Account 3"})

    return accounts

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"files": {}, "max_video_count": 0, "total_files": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_telegram_photo_bytes(image_bytes):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Credentials Missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {'photo': ('dashboard.png', image_bytes, 'image/png')}
    payload = {'chat_id': TELEGRAM_CHAT_ID}
    res = requests.post(url, data=payload, files=files)
    print("Telegram Response:", res.text)

def get_hd_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def generate_pillow_dashboard(accounts_data, total_files, total_videos, added_names, deleted_names, folder_summary):
    # Ultra-HD Canvas Dimensions (1600x1400)
    width, height = 1600, 1400
    img = Image.new('RGB', (width, height), color='#0b0f19')
    draw = ImageDraw.Draw(img)

    font_title = get_hd_font(34)
    font_sub = get_hd_font(24)
    font_bold = get_hd_font(28)
    font_regular = get_hd_font(22)

    # Top Header
    draw.rectangle([(0, 0), (width, 100)], fill='#1e293b')
    draw.text((40, 32), "MEGA CLOUD LIVE DASHBOARD (FULL REPORT)", fill='#00f2fe', font=font_title)

    # 4 Stat Cards
    cards = [
        ("TOTAL FILES", str(total_files), "#00f2fe", 40),
        ("TOTAL VIDEOS", str(total_videos), "#e11d73", 420),
        ("ADDED FILES", str(len(added_names)), "#22c55e", 800),
        ("DELETED FILES", str(len(deleted_names)), "#ef4444", 1180),
    ]

    for label, val, color, x in cards:
        draw.rectangle([(x, 140), (x + 360, 260)], fill='#1e293b', outline=color, width=3)
        draw.text((x + 24, 160), label, fill='#94a3b8', font=font_sub)
        draw.text((x + 24, 200), val, fill=color, font=font_bold)

    # Folders Breakdown Section (Account-wise Granular Split)
    draw.text((40, 300), "ALL FOLDERS BREAKDOWN (BY ACCOUNT)", fill='#38bdf8', font=font_sub)
    draw.rectangle([(40, 340), (1560, 680)], fill='#151d30')

    y_folder = 360
    if folder_summary:
        for f_name, stats in list(folder_summary.items())[:11]:
            line = f"> {f_name[:55]}: {stats['videos']} Videos ({stats['files']} Files)"
            draw.text((70, y_folder), line, fill='#ffffff', font=font_regular)
            y_folder += 28
    else:
        draw.text((70, 360), "No folders found", fill='#ffffff', font=font_regular)

    # File Updates: Added & Deleted Names Log
    draw.text((40, 720), "RECENT FILE LOGS", fill='#38bdf8', font=font_sub)
    
    # Added Box
    draw.rectangle([(40, 760), (780, 1000)], fill='#151d30', outline='#22c55e', width=2)
    draw.text((60, 780), "RECENTLY ADDED FILES", fill='#22c55e', font=font_sub)
    y_add = 820
    if added_names:
        for name in added_names[:6]:
            draw.text((60, y_add), f"+ {name[:45]}", fill='#ffffff', font=font_regular)
            y_add += 28
    else:
        draw.text((60, 820), "No new files added recently", fill='#94a3b8', font=font_regular)

    # Deleted Box
    draw.rectangle([(820, 760), (1560, 1000)], fill='#151d30', outline='#ef4444', width=2)
    draw.text((840, 780), "RECENTLY DELETED FILES", fill='#ef4444', font=font_sub)
    y_del = 820
    if deleted_names:
        for name in deleted_names[:6]:
            draw.text((840, y_del), f"- {name[:45]}", fill='#ffffff', font=font_regular)
            y_del += 28
    else:
        draw.text((840, 820), "No files deleted recently", fill='#94a3b8', font=font_regular)

    # Bar Graph Box (Videos per account)
    draw.text((40, 1040), "VIDEOS PER ACCOUNT", fill='#38bdf8', font=font_sub)
    draw.rectangle([(40, 1080), (1560, 1340)], fill='#0b1120')
    draw.line([(80, 1280), (1520, 1280)], fill='#334155', width=2)

    max_vids = max([acc["videos"] for acc in accounts_data] + [1])
    colors = ["#00f2fe", "#e11d73", "#ff9a00"]
    x_pos = 200

    for i, acc in enumerate(accounts_data):
        bar_h = int((acc["videos"] / max_vids) * 150)
        y_pos = 1280 - bar_h
        bar_color = colors[i % len(colors)]

        draw.rectangle([(x_pos, y_pos), (x_pos + 140, 1280)], fill=bar_color)
        draw.text((x_pos + 45, max(y_pos - 35, 1100)), str(acc['videos']), fill='#ffffff', font=font_bold)
        draw.text((x_pos + 30, 1290), acc['name'], fill='#94a3b8', font=font_sub)
        
        x_pos += 450

    buffer = BytesIO()
    img.save(buffer, format='PNG', quality=100)
    buffer.seek(0)
    return buffer.getvalue()

def scan_mega_account(account_info):
    email = account_info["email"]
    password = account_info["pass"]
    acc_name = account_info["name"]

    mega = Mega()
    m = None
    for attempt in range(3):
        try:
            time.sleep(12)
            m = mega.login(email, password)
            if m:
                break
        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(15)
    
    files_data = m.get_files()
    account_files = {}
    folder_map = {}
    video_count = 0
    total_files = 0

    if isinstance(files_data, dict):
        for node_id, node_info in files_data.items():
            if isinstance(node_info, dict) and node_info.get('t') == 1:
                attr = node_info.get('a', {})
                if isinstance(attr, dict):
                    folder_map[node_id] = attr.get('n', 'Root')

        for file_id, file_info in files_data.items():
            if isinstance(file_info, dict) and file_info.get('t') == 0:
                total_files += 1
                attr = file_info.get('a', {})
                file_name = attr.get('n', 'Unknown') if isinstance(attr, dict) else 'Unknown'
                parent_id = file_info.get('p', '')
                folder_name = folder_map.get(parent_id, "Root")
                is_vid = str(file_name).lower().endswith(video_extensions)
                
                # Dynamic account tag prefix for multi-account folders
                full_folder_tag = f"[{acc_name}] {folder_name}"
                unique_key = f"{email}_{file_id}"
                
                account_files[unique_key] = {
                    "name": file_name,
                    "folder": full_folder_tag,
                    "is_video": is_vid
                }
                if is_vid:
                    video_count += 1

    return account_files, total_files, video_count

if __name__ == "__main__":
    mega_accounts = get_all_mega_credentials()
    if not mega_accounts:
        print("No Mega credentials provided!")
        exit()

    prev_state = load_state()
    prev_files = prev_state.get("files", {})

    combined_files = {}
    total_files = 0
    total_videos = 0
    accounts_chart_data = []

    for acc in mega_accounts:
        try:
            files, t_files, v_count = scan_mega_account(acc)
            combined_files.update(files)
            total_files += t_files
            total_videos += v_count
            accounts_chart_data.append({"name": acc["name"], "videos": v_count})
        except Exception as e:
            print(f"Error scanning {acc['name']}: {e}")
            accounts_chart_data.append({"name": acc["name"], "videos": 0})

    added_names = [v["name"] for k, v in combined_files.items() if k not in prev_files]
    deleted_names = [v["name"] for k, v in prev_files.items() if k not in combined_files]

    folder_summary = {}
    for k, v in combined_files.items():
        f_name = v.get("folder", "Root")
        if f_name not in folder_summary:
            folder_summary[f_name] = {"files": 0, "videos": 0}
        folder_summary[f_name]["files"] += 1
        if v.get("is_video"):
            folder_summary[f_name]["videos"] += 1

    img_bytes = generate_pillow_dashboard(
        accounts_chart_data, 
        total_files, 
        total_videos, 
        added_names, 
        deleted_names,
        folder_summary
    )

    send_telegram_photo_bytes(img_bytes)

    save_state({
        "files": combined_files,
        "max_video_count": total_videos,
        "total_files": total_files
    })
            
