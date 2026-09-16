import os
import json
import time
import requests
from mega import Mega

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STATE_FILE = "mega_state.json"
video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm', '.3gp', '.m4v')

def get_all_mega_credentials():
    accounts = []
    # Dynamic ga MEGA_EMAIL_1, MEGA_EMAIL_2... enni unna detect chestundi
    for key, value in os.environ.items():
        if key.startswith("MEGA_EMAIL") or key.startswith("EMAIL_"):
            suffix = key.replace("MEGA_EMAIL", "").replace("EMAIL_", "").replace("_", "")
            pass_key = f"MEGA_PASSWORD_{suffix}" if suffix else "MEGA_PASSWORD"
            password = os.environ.get(pass_key) or os.environ.get(f"PASS_{suffix}") or os.environ.get("PASS")
            
            if value and password:
                acc_num = suffix if suffix else "1"
                accounts.append({
                    "email": value.strip(),
                    "pass": password.strip(),
                    "name": f"Account {acc_num}"
                })
    
    # Sort accounts by name (Account 1, Account 2...)
    accounts = sorted(accounts, key=lambda x: x["name"])
    print(f"Total Accounts Detected: {len(accounts)}")
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

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Credentials Missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    res = requests.post(url, data=payload)
    print("Telegram Response:", res.text)

def scan_mega_account(account_info):
    email = account_info["email"]
    password = account_info["pass"]
    acc_name = account_info["name"]

    print(f"Scanning {acc_name} ({email})...")
    mega = Mega()
    m = None
    for attempt in range(3):
        try:
            time.sleep(5)
            m = mega.login(email, password)
            if m:
                break
        except Exception as e:
            print(f"Attempt {attempt+1} failed for {acc_name}: {e}")
            if attempt == 2:
                return {}, 0, 0, {}
            time.sleep(10)
    
    try:
        files_data = m.get_files()
    except Exception as e:
        print(f"Error fetching files for {acc_name}: {e}")
        return {}, 0, 0, {}

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
                    folder_map[node_id] = attr.get('n', 'Root / Main')

        for file_id, file_info in files_data.items():
            if isinstance(file_info, dict) and file_info.get('t') == 0:
                total_files += 1
                attr = file_info.get('a', {})
                file_name = attr.get('n', 'Unknown') if isinstance(attr, dict) else 'Unknown'
                parent_id = file_info.get('p', '')
                folder_name = folder_map.get(parent_id, "Root / Main")
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

    print(f"Done scanning {acc_name}: {total_files} files, {video_count} videos.")
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
    combined_folders = {}

    for acc in mega_accounts:
        try:
            files, t_files, v_count, acc_folders = scan_mega_account(acc)
            combined_files.update(files)
            total_files += t_files
            total_videos += v_count

            for f_name, stats in acc_folders.items():
                if f_name not in combined_folders:
                    combined_folders[f_name] = {"files": 0, "videos": 0}
                combined_folders[f_name]["files"] += stats["files"]
                combined_folders[f_name]["videos"] += stats["videos"]

        except Exception as e:
            print(f"Error scanning {acc['name']}: {e}")

    added_names = [v["name"] for k, v in combined_files.items() if k not in prev_files]
    deleted_names = [v["name"] for k, v in prev_files.items() if k not in combined_files]

    # Text Report Building
    report_lines = [
        "🌌 <b>MEGA CLOUD FULL REPORT</b>\n",
        f"📁 <b>Total Files:</b> {total_files}",
        f"🎬 <b>Total Videos:</b> {total_videos}",
        f"➕ <b>Recently Added:</b> +{len(added_names)}",
        f"🗑️ <b>Recently Deleted / Trash:</b> {len(deleted_names)}\n",
        "📂 <b>FOLDERS BREAKDOWN:</b>"
    ]

    # Root First, then Sorted Folders
    sorted_folders = sorted(combined_folders.keys(), key=lambda x: (x != "Root / Main", x))
    for f_name in sorted_folders:
        stats = combined_folders[f_name]
        report_lines.append(f"• {f_name}: {stats['videos']} Videos ({stats['files']} Total Files)")

    final_report = "\n".join(report_lines)

    # Send to Telegram
    send_telegram_message(final_report)

    # Save State
    save_state({
        "files": combined_files,
        "max_video_count": total_videos,
        "total_files": total_files
    })
