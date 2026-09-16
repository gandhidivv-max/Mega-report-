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
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {'photo': ('dashboard.png', image_bytes, 'image/png')}
    payload = {'chat_id': TELEGRAM_CHAT_ID}
    requests.post(url, data=payload, files=files)

def generate_pillow_dashboard(accounts_data, total_files, total_videos, recently_added, recently_deleted, folder_summary):
    width, height = 800, 520
    img = Image.new('RGB', (width, height), color='#0f172a')
    draw = ImageDraw.Draw(img)

    font_title = font_main = font_sub = ImageFont.load_default()

    # Header
    draw.rectangle([(0, 0), (width, 55)], fill='#1e293b')
    draw.text((25, 18), "MEGA CLOUD LIVE DASHBOARD", fill='#00f2fe', font=font_title)

    # 4 Stat Cards Box Dimensions
    cards = [
        ("TOTAL FILES", str(total_files), "#00f2fe", 25),
        ("TOTAL VIDEOS", str(total_videos), "#e11d73", 215),
        ("RECENTLY ADDED", f"+{recently_added}", "#22c55e", 405),
        ("DELETED", str(recently_deleted), "#ef4444", 595),
    ]

    for label, val, color, x in cards:
        draw.rectangle([(x, 75), (x + 180, 145)], fill='#1e293b', outline=color, width=2)
        draw.text((x + 12, 88), label, fill='#94a3b8', font=font_sub)
        draw.text((x + 12, 110), val, fill=color, font=font_main)

    # Folders Section Box
    draw.rectangle([(25, 165), (775, 230)], fill='#1e293b')
    draw.text((40, 175), "FOLDERS BREAKDOWN:", fill='#38bdf8', font=font_sub)
    
    y_folder = 198
    folder_items = list(folder_summary.items())[:3]
    if folder_items:
        f_text = "   |   ".join([f"{f_name}: {stats['videos']} Videos ({stats['files']} Files)" for f_name, stats in folder_items])
        draw.text((40, y_folder), f_text, fill='#ffffff', font=font_sub)
    else:
        draw.text((40, y_folder), "No folders found", fill='#ffffff', font=font_sub)

    # Bar Graph Container
    draw.text((25, 250), "VIDEOS PER ACCOUNT", fill='#38bdf8', font=font_sub)
    draw.rectangle([(25, 270), (775, 490)], fill='#0b1120')

    # Draw Graph Axes Lines
    draw.line([(45, 450), (755, 450)], fill='#334155', width=1)

    # Draw Bars
    max_vids = max([acc["videos"] for acc in accounts_data] + [1])
    colors = ["#00f2fe", "#e11d73", "#ff9a00"]
    x_pos = 100

    for i, acc in enumerate(accounts_data):
        bar_h = int((acc["videos"] / max_vids) * 140)
        y_pos = 450 - bar_h
        bar_color = colors[i % len(colors)]

        draw.rectangle([(x_pos, y_pos), (x_pos + 70, 450)], fill=bar_color)
        draw.text((x_pos + 25, y_pos - 18), str(acc['videos']), fill='#ffffff', font=font_main)
        draw.text((x_pos + 10, 460), acc['name'], fill='#94a3b8', font=font_sub)
        
        x_pos += 230

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()

def scan_mega_account(email, password):
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
    
    trash_id = getattr(m, 'trash_id', None) or getattr(m, 'trash_folder', None)
    files_data = m.get_files()
    account_files = {}
    folder_map = {}
    video_count = 0
    total_files = 0
    deleted_bin_count = 0

    if isinstance(files_data, dict):
        for node_id, node_info in files_data.items():
            if isinstance(node_info, dict) and node_info.get('t') == 1:
                attr = node_info.get('a', {})
                if isinstance(attr, dict):
                    folder_map[node_id] = attr.get('n', 'Root')

        for file_id, file_info in files_data.items():
            if isinstance(file_info, dict) and file_info.get('t') == 0:
                attr = file_info.get('a', {})
                file_name = attr.get('n', 'Unknown') if isinstance(attr, dict) else 'Unknown'
                parent_id = file_info.get('p', '')

                if trash_id and parent_id == trash_id:
                    deleted_bin_count += 1
                else:
                    total_files += 1
                    folder_name = folder_map.get(parent_id, "Root")
                    is_vid = str(file_name).lower().endswith(video_extensions)
                    unique_key = f"{email}_{file_id}"
                    account_files[unique_key] = {
                        "name": file_name,
                        "folder": folder_name,
                        "is_video": is_vid
                    }
                    if is_vid:
                        video_count += 1

    return account_files, total_files, video_count, deleted_bin_count

if __name__ == "__main__":
    try:
        mega_accounts = get_all_mega_credentials()
        if not mega_accounts:
            exit()

        prev_state = load_state()
        prev_files = prev_state.get("files", {})

        combined_files = {}
        total_files = 0
        total_videos = 0
        total_deleted_bin = 0
        accounts_chart_data = []

        for acc in mega_accounts:
            try:
                files, t_files, v_count, d_bin = scan_mega_account(acc["email"], acc["pass"])
                combined_files.update(files)
                total_files += t_files
                total_videos += v_count
                total_deleted_bin += d_bin
                accounts_chart_data.append({"name": acc["name"], "videos": v_count})
            except Exception:
                accounts_chart_data.append({"name": acc["name"], "videos": 0})

        recently_added = sum(1 for k, v in combined_files.items() if k not in prev_files and v.get("is_video"))
        recently_deleted = sum(1 for k in prev_files if k not in combined_files)

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
            recently_added, 
            recently_deleted + total_deleted_bin,
            folder_summary
        )

        send_telegram_photo_bytes(img_bytes)

        save_state({
            "files": combined_files,
            "max_video_count": total_videos,
            "total_files": total_files
        })
    except Exception:
        pass
    
