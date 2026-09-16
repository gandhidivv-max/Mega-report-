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

def draw_combined_folders(draw, x_start, y_start, width, height, all_folders, title_color, font_sub, font_regular):
    draw.rectangle([(x_start, y_start), (x_start + width, y_start + height)], fill='#151d30', outline=title_color, width=1)
    draw.text((x_start + 15, y_start + 15), "ALL ACCOUNT FOLDERS SUMMARY", fill=title_color, font=font_sub)
    
    if not all_folders:
        draw.text((x_start + 15, y_start + 55), "No folders found", fill='#94a3b8', font=font_regular)
        return

    folder_items = list(all_folders.items())
    col_width = 160  
    max_cols = (width - 30) // col_width  # గరిష్టంగా పడే కాలమ్‌ల సంఖ్య
    
    # ఫోల్డర్‌ల మొత్తం సంఖ్యను బట్టి కాలమ్‌కి ఎన్ని పడాలో డైనమిక్‌గా లెక్కిస్తుంది
    total_folders = len(folder_items)
    items_per_col = max(50, (total_folders + max_cols - 1) // max_cols)

    for idx, (f_name, stats) in enumerate(folder_items):
        col_index = idx // items_per_col
        row_index = idx % items_per_col
        
        curr_x = x_start + 15 + (col_index * col_width)
        curr_y = y_start + 55 + (row_index * 24)
        
        # ఇమేజ్ బాక్స్ దాటిపోకుండా సేఫ్‌గా సరిపోయేలా చెకింగ్
        if curr_x + col_width <= x_start + width and curr_y + 24 <= y_start + height:
            line = f"• {f_name[:12]} - {stats['videos']}"
            draw.text((curr_x, curr_y), line, fill='#ffffff', font=font_regular)

def generate_pillow_dashboard(accounts_data, total_files, total_videos, added_names, deleted_names, folder_summary_by_acc):
    width, height = 1080, 2400
    img = Image.new('RGB', (width, height), color='#0b0f19')
    draw = ImageDraw.Draw(img)

    font_title = get_hd_font(28)
    font_sub = get_hd_font(20)
    font_bold = get_hd_font(22)
    font_regular = get_hd_font(16)

    # Header
    draw.rectangle([(0, 0), (width, 80)], fill='#1e293b')
    draw.text((30, 24), "MEGA CLOUD LIVE DASHBOARD", fill='#00f2fe', font=font_title)

    # 4 Stat Cards Grid
    cards = [
        ("TOTAL FILES", str(total_files), "#00f2fe", 30, 100),
        ("TOTAL VIDEOS", str(total_videos), "#e11d73", 550, 100),
        ("ADDED FILES", str(len(added_names)), "#22c55e", 30, 210),
        ("DELETED FILES", str(len(deleted_names)), "#ef4444", 550, 210),
    ]

    for label, val, color, x, y in cards:
        draw.rectangle([(x, y), (x + 500, y + 95)], fill='#1e293b', outline=color, width=2)
        draw.text((x + 20, y + 15), label, fill='#94a3b8', font=font_sub)
        draw.text((x + 20, y + 48), val, fill=color, font=font_bold)

    # Combine Account 1 & Account 2 Folders
    combined_folders = {}
    for acc_name, folders in folder_summary_by_acc.items():
        for f_name, stats in folders.items():
            if f_name not in combined_folders:
                combined_folders[f_name] = {"files": 0, "videos": 0}
            combined_folders[f_name]["files"] += stats["files"]
            combined_folders[f_name]["videos"] += stats["videos"]

    # Dynamic Combined Box
    draw.text((30, 330), "FOLDERS BREAKDOWN (COMBINED)", fill='#38bdf8', font=font_sub)
    draw_combined_folders(draw, 30, 365, 1020, 1600, combined_folders, '#00f2fe', font_sub, font_regular)

    # Recent File Logs Section
    draw.text((30, 1990), "RECENT FILE LOGS", fill='#38bdf8', font=font_sub)
    
    # Added Box
    draw.rectangle([(30, 2025), (520, 2350)], fill='#151d30', outline='#22c55e', width=2)
    draw.text((45, 2040), "ADDED FILES", fill='#22c55e', font=font_sub)
    y_add = 2080
    if added_names:
        for name in added_names[:10]:
            draw.text((45, y_add), f"+ {name[:32]}", fill='#ffffff', font=font_regular)
            y_add += 24
    else:
        draw.text((45, 2080), "No new files added", fill='#94a3b8', font=font_regular)

    # Deleted Box
    draw.rectangle([(550, 2025), (1050, 2350)], fill='#151d30', outline='#ef4444', width=2)
    draw.text((565, 2040), "DELETED FILES", fill='#ef4444', font=font_sub)
    y_del = 2080
    if deleted_names:
        for name in deleted_names[:10]:
            draw.text((565, y_del), f"- {name[:32]}", fill='#ffffff', font=font_regular)
            y_del += 24
    else:
        draw.text((565, 2080), "No files deleted", fill='#94a3b8', font=font_regular)

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
    
