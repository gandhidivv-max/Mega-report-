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

def draw_account_folders(draw, x_start, y_start, width, height, acc_title, folders, title_color, font_sub, font_regular):
    draw.rectangle([(x_start, y_start), (x_start + width, y_start + height)], fill='#151d30', outline=title_color, width=1)
    draw.text((x_start + 20, y_start + 15), acc_title, fill=title_color, font=font_sub)
    
    if not folders:
        draw.text((x_start + 20, y_start + 60), "No folders found", fill='#94a3b8', font=font_regular)
        return

    folder_items = list(folders.items())
    col_width = 230
    items_per_col = 10
    
    for idx, (f_name, stats) in enumerate(folder_items):
        col_index = idx // items_per_col
        row_index = idx % items_per_col
        
        curr_x = x_start + 20 + (col_index * col_width)
        curr_y = y_start + 65 + (row_index * 28)
        
        if curr_x + col_width <= x_start + width:
            line = f"• {f_name[:15]} - {stats['videos']}"
            draw.text((curr_x, curr_y), line, fill='#ffffff', font=font_regular)

def generate_pillow_dashboard(accounts_data, total_files, total_videos, added_names, deleted_names, folder_summary_by_acc):
    width, height = 1600, 1150
    img = Image.new('RGB', (width, height), color='#0b0f19')
    draw = ImageDraw.Draw(img)

    font_title = get_hd_font(34)
    font_sub = get_hd_font(24)
    font_bold = get_hd_font(28)
    font_regular = get_hd_font(20)

    # Header
    draw.rectangle([(0, 0), (width, 100)], fill='#1e293b')
    draw.text((40, 32), "MEGA CLOUD LIVE DASHBOARD", fill='#00f2fe', font=font_title)

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

    # Multi-Column Folders Breakdown
    draw.text((40, 300), "FOLDERS BREAKDOWN", fill='#38bdf8', font=font_sub)

    # Account 1 Folders Box
    acc1_folders = folder_summary_by_acc.get("Account 1", {})
    draw_account_folders(draw, 40, 340, 740, 410, "ACCOUNT 1 FOLDERS", acc1_folders, '#00f2fe', font_sub, font_regular)

    # Account 2 Folders Box
    acc2_folders = folder_summary_by_acc.get("Account 2", {})
    draw_account_folders(draw, 820, 340, 740, 410, "ACCOUNT 2 FOLDERS", acc2_folders, '#e11d73', font_sub, font_regular)

    # File Logs Section
    draw.text((40, 780), "RECENT FILE LOGS", fill='#38bdf8', font=font_sub)
    
    # Added Box
    draw.rectangle([(40, 820), (780, 1080)], fill='#151d30', outline='#22c55e', width=2)
    draw.text((60, 840), "RECENTLY ADDED FILES", fill='#22c55e', font=font_sub)
    y_add = 880
    if added_names:
        for name in added_names[:6]:
            draw.text((60, y_add), f"+ {name[:45]}", fill='#ffffff', font=font_regular)
            y_add += 28
    else:
        draw.text((60, 880), "No new files added recently", fill='#94a3b8', font=font_regular)

    # Deleted Box
    draw.rectangle([(820, 820), (1560, 1080)], fill='#151d30', outline='#ef4444', width=2)
    draw.text((840, 840), "RECENTLY DELETED FILES", fill='#ef4444', font=font_sub)
    y_del = 880
    if deleted_names:
        for name in deleted_names[:6]:
            draw.text((840, y_del), f"- {name[:45]}", fill='#ffffff', font=font_regular)
            y_del += 28
    else:
        draw.text((840, 880), "No files deleted recently", fill='#94a3b8', font=font_regular)

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
    acc_folders = {}

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
                
                unique_key = f"{email}_{file_id}"
                
                account_files[unique_key] = {
                    "name": file_name,
                    "folder": folder_name,
                    "account": acc_name,
                    "is_video": is_vid
                }
                
                if folder_name not in acc_folders:
                    acc_folders[folder_name] = {"files": 0, "videos": 0}
                acc_folders[folder_name]["files"] += 1

                if is_vid:
                    video_count += 1
                    acc_folders[folder_name]["videos"] += 1

    return account_files, total_files, video_count, acc_folders

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
    folder_summary_by_acc = {}

    for acc in mega_accounts:
        try:
            files, t_files, v_count, acc_folders = scan_mega_account(acc)
            combined_files.update(files)
            total_files += t_files
            total_videos += v_count
            accounts_chart_data.append({"name": acc["name"], "videos": v_count})
            folder_summary_by_acc[acc["name"]] = acc_folders
        except Exception as e:
            print(f"Error scanning {acc['name']}: {e}")
            accounts_chart_data.append({"name": acc["name"], "videos": 0})

    added_names = [v["name"] for k, v in combined_files.items() if k not in prev_files]
    deleted_names = [v["name"] for k, v in prev_files.items() if k not in combined_files]

    img_bytes = generate_pillow_dashboard(
        accounts_chart_data, 
        total_files, 
        total_videos, 
        added_names, 
        deleted_names,
        folder_summary_by_acc
    )

    send_telegram_photo_bytes(img_bytes)

    save_state({
        "files": combined_files,
        "max_video_count": total_videos,
        "total_files": total_files
    })
              
