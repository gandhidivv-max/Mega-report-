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
    return {"files": {}, "max_video_count": 0, "total_files": 0, "missing_videos": {}, "last_ping_time": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials missing in script execution!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    res = requests.post(url, json=payload)
    print(f"Telegram Message Status: {res.status_code}, Response: {res.text}")

def send_telegram_photo(photo_url, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials missing in script execution!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    res = requests.post(url, json=payload)
    print(f"Telegram Photo Status: {res.status_code}, Response: {res.text}")
    if res.status_code != 200:
        send_telegram_message(caption)

def generate_cinematic_dashboard_image(accounts_data, total_files, total_videos, target_count, total_bin):
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
                "borderRadius": 8,
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
                "title": {
                    "display": True,
                    "text": "MEGA CLOUD LIVE DASHBOARD",
                    "color": "#ffffff",
                    "font": {"size": 20, "weight": "bold"}
                },
                "subtitle": {
                    "display": True,
                    "text": f"Files: {total_files}  |  Videos: {total_videos}/{target_count}  |  Trash: {total_bin}",
                    "color": "#38bdf8",
                    "font": {"size": 15, "weight": "bold"},
                    "padding": {"bottom": 20}
                },
                "legend": {"display": False},
                "datalabels": {"display": True}
            },
            "scales": {
                "x": {
                    "ticks": {"color": "#a0aec0", "font": {"size": 14, "weight": "bold"}},
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
    image_url = f"https://quickchart.io/chart?c={encoded_chart}&bkg=%230f172a&w=800&h=450&devicePixelRatio=2"
    return image_url

def scan_mega_account(email, password, do_ping):
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
    trash_files = {}
    video_count = 0
    total_files = 0
    deleted_bin_count = 0

    if isinstance(files_data, dict):
        for file_id, file_info in files_data.items():
            if isinstance(file_info, dict) and file_info.get('t') == 0:
                attr = file_info.get('a', {})
                file_name = 'Unknown'
                if isinstance(attr, dict):
                    file_name = attr.get('n', 'Unknown')
                
                parent_id = file_info.get('p', '')

                if trash_id and parent_id == trash_id:
                    deleted_bin_count += 1
                    trash_files[file_id] = file_name
                else:
                    total_files += 1
                    unique_key = f"{email}_{file_id}"
                    account_files[unique_key] = {
                        "name": file_name,
                        "email": email,
                        "file_id": file_id,
                        "is_video": str(file_name).lower().endswith(video_extensions)
                    }
                    if str(file_name).lower().endswith(video_extensions):
                        video_count += 1

    return account_files, trash_files, total_files, video_count, deleted_bin_count, False

if __name__ == "__main__":
    try:
        mega_accounts = get_all_mega_credentials()
        if not mega_accounts:
            send_telegram_message("❌ *Error:* GitHub Secrets లో MEGA_EMAIL, MEGA_PASSWORD దొరకలేదు!")
            exit()

        prev_state = load_state()
        target_video_count = prev_state.get("max_video_count", 0)
        stored_missing_videos = prev_state.get("missing_videos", {})
        last_ping_time = prev_state.get("last_ping_time", 0)

        current_time = time.time()
        do_ping = (current_time - last_ping_time) >= (15 * 24 * 60 * 60)

        combined_files = {}
        all_trash_files = {}
        total_files = 0
        total_videos = 0
        total_deleted_bin = 0
        accounts_chart_data = []

        for acc in mega_accounts:
            try:
                files, trash, t_files, v_count, d_bin, _ = scan_mega_account(acc["email"], acc["pass"], do_ping)
                combined_files.update(files)
                all_trash_files.update(trash)
                total_files += t_files
                total_videos += v_count
                total_deleted_bin += d_bin
                
                accounts_chart_data.append({"name": acc["name"], "videos": v_count, "files": t_files})
            except Exception as e:
                send_telegram_message(f"⚠️ *{acc['name']} Login Failed:* `{str(e)}`")
                accounts_chart_data.append({"name": acc["name"], "videos": 0, "files": 0})

        if total_videos > target_video_count:
            target_video_count = total_videos

        chart_image_url = generate_cinematic_dashboard_image(
            accounts_chart_data, 
            total_files, 
            total_videos, 
            target_video_count, 
            total_deleted_bin
        )

        caption = (
            "🌌 *MEGA CLOUD LIVE DASHBOARD*\n\n"
            f"📁 *Total Files:* `{total_files}`\n"
            f"🎬 *Total Videos:* `{total_videos}` / `{target_video_count}`\n"
            f"🗑️ *Rubbish Bin:* `{total_deleted_bin}`\n\n"
            "🟢 *Status:* Sync Completed"
        )

        send_telegram_photo(chart_image_url, caption)

        new_state = {
            "files": combined_files,
            "max_video_count": target_video_count,
            "total_files": total_files,
            "missing_videos": stored_missing_videos,
            "last_ping_time": current_time
        }
        save_state(new_state)

    except Exception as e:
        send_telegram_message(f"❌ *Script Error:* `{str(e)}`")
    
