import os
import json
import time
import requests
import matplotlib.pyplot as plt
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

def send_telegram_photo(image_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(image_path, 'rb') as photo:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, files={"photo": photo})

def generate_custom_dashboard_image(accounts_data, total_files, total_videos, recently_added, recently_deleted, folder_summary):
    # 1. Matplotlib తో Graph తయారు చేసి సేవ్ చేయడం
    names = [acc["name"] for acc in accounts_data]
    counts = [acc["videos"] for acc in accounts_data]
    
    fig, ax = plt.subplots(figsize=(6, 3), dpi=150)
    fig.patch.set_facecolor('#0f172a')
    ax.set_facecolor('#0f172a')
    
    bars = ax.bar(names, counts, color=['#00f2fe', '#e11d73', '#ff9a00'][:len(names)], width=0.4)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#a0aec0')
    ax.spines['bottom'].set_color('#a0aec0')
    ax.tick_params(colors='white', labelsize=8)
    
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f'{yval}', ha='center', va='bottom', color='white', fontweight='bold', fontsize=9)
        
    plt.tight_layout()
    chart_path = "temp_chart.png"
    plt.savefig(chart_path, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

    # 2. Pillow తో HD Dashboard Banner తయారు చేయడం
    width, height = 900, 650
    img = Image.new('RGB', (width, height), color='#0f172a')
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 26)
        font_main = ImageFont.truetype("arial.ttf", 16)
        font_sub = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font_title = font_main = font_sub = ImageFont.load_default()

    # Title Banner
    draw.rectangle([(0, 0), (width, 60)], fill='#1e293b')
    draw.text((20, 15), "MEGA CLOUD LIVE DASHBOARD", fill='#ffffff', font=font_title)

    # Key Stats Boxes
    draw.rectangle([(20, 80), (220, 150)], fill='#1e293b', outline='#00f2fe', width=2)
    draw.text((30, 90), "Total Files", fill='#a0aec0', font=font_sub)
    draw.text((30, 115), str(total_files), fill='#ffffff', font=font_main)

    draw.rectangle([(240, 80), (440, 150)], fill='#1e293b', outline='#e11d73', width=2)
    draw.text((250, 90), "Total Videos", fill='#a0aec0', font=font_sub)
    draw.text((250, 115), str(total_videos), fill='#ffffff', font=font_main)

    draw.rectangle([(460, 80), (660, 150)], fill='#1e293b', outline='#22c55e', width=2)
    draw.text((470, 90), "Recently Added", fill='#a0aec0', font=font_sub)
    draw.text((470, 115), f"+{recently_added}", fill='#22c55e', font=font_main)

    draw.rectangle([(680, 80), (880, 150)], fill='#1e293b', outline='#ef4444', width=2)
    draw.text((690, 90), "Recently Deleted", fill='#a0aec0', font=font_sub)
    draw.text((690, 115), str(recently_deleted), fill='#ef4444', font=font_main)

    # Folders Breakdown Text Section
    draw.rectangle([(20, 170), (880, 310)], fill='#1e293b')
    draw.text((35, 180), "FOLDERS BREAKDOWN:", fill='#38bdf8', font=font_main)
    
    y_off = 210
    for f_name, stats in folder_summary.items():
        if y_off < 290:
            txt = f"• {f_name}: {stats['videos']} Videos  ({stats['files']} Total Files)"
            draw.text((35, y_off), txt, fill='#ffffff', font=font_sub)
            y_off += 25

    # Graph ని Dashboard కి జత చేయడం
    chart_img = Image.open(chart_path)
    img.paste(chart_img, (20, 320))

    final_path = "final_dashboard.png"
    img.save(final_path)
    return final_path

def scan_mega_account(email, password):
    mega = Mega()
    m = None
    for attempt in range(3):
        try:
            time.sleep(12)
            m = mega.login(email, password)
            if m: break
        except Exception as e:
            if attempt == 2: raise e
            time.sleep(15)
    
    trash_id = getattr(m, 'trash_id', None) or getattr(m, 'trash_folder', None)
    files_data = m.get_files()
    account_files, folder_map = {}, {}
    video_count, total_files, deleted_bin_count = 0, 0, 0

    if isinstance(files_data, dict):
        for node_id, node_info in files_data.items():
            if isinstance(node_info, dict) and node_info.get('t') == 1:
                attr = node_info.get('a', {})
                if isinstance(attr, dict):
                    folder_map[node_id] = attr.get('n', 'Main Root')

        for file_id, file_info in files_data.items():
            if isinstance(file_info, dict) and file_info.get('t') == 0:
                attr = file_info.get('a', {})
                file_name = attr.get('n', 'Unknown') if isinstance(attr, dict) else 'Unknown'
                parent_id = file_info.get('p', '')

                if trash_id and parent_id == trash_id:
                    deleted_bin_count += 1
                else:
                    total_files += 1
                    folder_name = folder_map.get(parent_id, "Main Root")
                    is_vid = str(file_name).lower().endswith(video_extensions)
                    unique_key = f"{email}_{file_id}"
                    account_files[unique_key] = {
                        "name": file_name, "folder": folder_name, "is_video": is_vid
                    }
                    if is_vid: video_count += 1

    return account_files, total_files, video_count, deleted_bin_count

if __name__ == "__main__":
    try:
        mega_accounts = get_all_mega_credentials()
        if not mega_accounts: exit()

        prev_state = load_state()
        prev_files = prev_state.get("files", {})

        combined_files = {}
        total_files, total_videos, total_deleted_bin = 0, 0, 0
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
            f_name = v.get("folder", "Main Root")
            if f_name not in folder_summary:
                folder_summary[f_name] = {"files": 0, "videos": 0}
            folder_summary[f_name]["files"] += 1
            if v.get("is_video"):
                folder_summary[f_name]["videos"] += 1

        # PIL ద్వారా ఇమేజ్ జనరేట్ చేయడం
        final_image = generate_custom_dashboard_image(
            accounts_chart_data, 
            total_files, 
            total_videos, 
            recently_added, 
            recently_deleted + total_deleted_bin,
            folder_summary
        )

        send_telegram_photo(final_image)

        save_state({
            "files": combined_files,
            "max_video_count": total_videos,
            "total_files": total_files
        })
    except Exception:
        pass
                  
