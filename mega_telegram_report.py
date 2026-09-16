import os
import json
import time
import requests
import urllib.parse
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
    return {"files": {}, "max_video_count": 0, "total_files": 0, "last_ping_time": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_telegram_photo(photo_url, caption_text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption_text,
        "parse_mode": "Markdown"
    }
    res = requests.post(url, json=payload)
    # ఒకవేళ ఇమేజ్ క్యాప్షన్ పెద్దదై పోతే నేరుగా మెసేజ్ పంపుతుంది
    if res.status_code != 200:
        url_msg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url_msg, json={"chat_id": TELEGRAM_CHAT_ID, "text": caption_text, "parse_mode": "Markdown"})

def generate_clean_chart(accounts_data):
    labels = [acc["name"] for acc in accounts_data]
    video_counts = [acc["videos"] for acc in accounts_data]

    chart_config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Videos",
                "data": video_counts,
                "backgroundColor": ["rgba(0, 242, 254, 0.85)", "rgba(225, 29, 115, 0.85)", "rgba(255, 154, 0, 0.85)"],
                "borderColor": ["#00f2fe", "#e11d73", "#ff9a00"],
                "borderWidth": 2,
                "borderRadius": 6,
                "datalabels": {
                    "align": "top",
                    "anchor": "end",
                    "color": "#ffffff",
                    "font": {"size": 16, "weight": "bold"}
                }
            }]
        },
        "options": {
            "plugins": {
                "legend": {"display": False},
                "datalabels": {"display": True}
            },
            "scales": {
                "x": {
                    "ticks": {"color": "#ffffff", "font": {"size": 14, "weight": "bold"}},
                    "grid": {"display": False}
                },
                "y": {
                    "ticks": {"color": "#a0aec0", "font": {"size": 12}},
                    "grid": {"color": "rgba(255, 255, 255, 0.1)"},
                    "grace": "20%"
                }
            }
        }
    }

    encoded_chart = urllib.parse.quote(json.dumps(chart_config))
    return f"https://quickchart.io/chart?c={encoded_chart}&bkg=%230f172a&w=800&h=400&devicePixelRatio=2"

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
        # 1. ఫోల్డర్ పేర్ల మ్యాపింగ్
        for node_id, node_info in files_data.items():
            if isinstance(node_info, dict) and node_info.get('t') == 1:
                attr = node_info.get('a', {})
                if isinstance(attr, dict):
                    folder_map[node_id] = attr.get('n', 'Unknown Folder')

        # 2. ఫైళ్ల స్కాన్
        for file_id, file_info in files_data.items():
            if isinstance(file_info, dict) and file_info.get('t') == 0:
                attr = file_info.get('a', {})
                file_name = 'Unknown'
                if isinstance(attr, dict):
                    file_name = attr.get('n', 'Unknown')
                
                parent_id = file_info.get('p', '')

                if trash_id and parent_id == trash_id:
                    deleted_bin_count += 1
                else:
                    total_files += 1
                    folder_name = folder_map.get(parent_id, "Root / Main")
                    is_vid = str(file_name).lower().endswith(video_extensions)
                    
                    unique_key = f"{email}_{file_id}"
                    account_files[unique_key] = {
                        "name": file_name,
                        "email": email,
                        "file_id": file_id,
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
                accounts_chart_data.append({"name": acc["name"], "videos": v_count, "files": t_files})
            except Exception:
                accounts_chart_data.append({"name": acc["name"], "videos": 0, "files": 0})

        # Recently Added & Deleted Calculation
        recently_added = 0
        recently_added_names = []
        for k, v in combined_files.items():
            if k not in prev_files:
                if v.get("is_video"):
                    recently_added += 1
                    recently_added_names.append(v.get("name"))

        recently_deleted = 0
        for k, v in prev_files.items():
            if k not in combined_files:
                recently_deleted += 1

        # Separate Folders Wise Metrics
        folder_summary = {}
        for k, v in combined_files.items():
            f_name = v.get("folder", "Root")
            if f_name not in folder_summary:
                folder_summary[f_name] = {"files": 0, "videos": 0}
            folder_summary[f_name]["files"] += 1
            if v.get("is_video"):
                folder_summary[f_name]["videos"] += 1

        # Telegram Message Formatting
        caption = "🌌 *MEGA CLOUD FULL REPORT*\n\n"
        caption += f"📁 *Total Files:* `{total_files}`\n"
        caption += f"🎬 *Total Videos:* `{total_videos}`\n"
        caption += f"➕ *Recently Added:* `+{recently_added}`\n"
        caption += f"🗑️ *Recently Deleted / Trash:* `{recently_deleted + total_deleted_bin}`\n\n"

        caption += "📂 *FOLDERS BREAKDOWN:*\n"
        for f_name, stats in folder_summary.items():
            caption += f"• *{f_name}*: {stats['videos']} Videos ({stats['files']} Total Files)\n"

        chart_url = generate_clean_chart(accounts_chart_data)
        send_telegram_photo(chart_url, caption)

        new_state = {
            "files": combined_files,
            "max_video_count": total_videos,
            "total_files": total_files,
            "last_ping_time": time.time()
        }
        save_state(new_state)

    except Exception:
        pass
    
