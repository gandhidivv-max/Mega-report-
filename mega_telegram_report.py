import os
import json
import time
import re
import requests
from mega import Mega

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STATE_FILE = "mega_state.json"
video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm', '.3gp', '.m4v')
image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')

def get_all_mega_credentials():
    accounts = []
    i = 1
    while True:
        e = os.environ.get(f"MEGA_EMAIL_{i}") or (os.environ.get("MEGA_EMAIL") if i == 1 else None)
        p = os.environ.get(f"MEGA_PASSWORD_{i}") or (os.environ.get("MEGA_PASSWORD") if i == 1 else None)
        if e and p:
            accounts.append({"email": e.strip(), "pass": p.strip(), "name": f"Account {i}"})
            i += 1
        else:
            if i > 10:
                break
            i += 1
    return accounts

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")
    return {"files": {}}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Error saving state: {e}")

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Credentials Missing!")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    MAX_LEN = 3800
    
    lines = text.split("\n")
    chunks = []
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > MAX_LEN:
            chunks.append(current_chunk)
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    if current_chunk:
        chunks.append(current_chunk)

    for idx, chunk in enumerate(chunks):
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': chunk,
            'parse_mode': 'HTML'
        }
        res = requests.post(url, data=payload)
        time.sleep(1)

def scan_mega_account(account_info):
    email = account_info["email"]
    password = account_info["pass"]
    acc_name = account_info["name"]

    mega = Mega()
    m = None
    
    for attempt in range(1, 4):
        try:
            time.sleep(5)
            m = mega.login(email, password)
            if m:
                break
        except Exception as e:
            if attempt == 3:
                return {}, {}
            time.sleep(10)
    
    try:
        files_data = m.get_files()
    except Exception as e:
        return {}, {}

    account_files = {}
    folder_map = {}
    acc_folders = {}

    if isinstance(files_data, dict):
        for node_id, node_info in files_data.items():
            if isinstance(node_info, dict) and node_info.get('t') == 1:
                attr = node_info.get('a', {})
                if isinstance(attr, dict):
                    folder_map[node_id] = attr.get('n', 'Root / Main')

        for file_id, file_info in files_data.items():
            if isinstance(file_info, dict) and file_info.get('t') == 0:
                attr = file_info.get('a', {})
                file_name = attr.get('n', 'Unknown') if isinstance(attr, dict) else 'Unknown'
                parent_id = file_info.get('p', '')
                folder_name = folder_map.get(parent_id, "Root / Main")
                
                name_lower = str(file_name).lower()
                is_vid = name_lower.endswith(video_extensions)
                is_img = name_lower.endswith(image_extensions)
                
                unique_key = f"{email}_{file_id}"
                
                account_files[unique_key] = {
                    "name": file_name,
                    "folder": folder_name,
                    "account": acc_name
                }
                
                if folder_name not in acc_folders:
                    acc_folders[folder_name] = {"videos": 0, "images": 0, "total": 0}
                
                acc_folders[folder_name]["total"] += 1
                if is_vid:
                    acc_folders[folder_name]["videos"] += 1
                elif is_img:
                    acc_folders[folder_name]["images"] += 1

    return account_files, acc_folders

if __name__ == "__main__":
    mega_accounts = get_all_mega_credentials()
    if not mega_accounts:
        exit(1)

    prev_state = load_state()
    prev_files = prev_state.get("files", {})

    combined_files = {}
    combined_folders = {}

    for acc in mega_accounts:
        try:
            files, acc_folders = scan_mega_account(acc)
            if files:
                combined_files.update(files)
                for f_name, stats in acc_folders.items():
                    if f_name not in combined_folders:
                        combined_folders[f_name] = {"videos": 0, "images": 0, "total": 0}
                    combined_folders[f_name]["videos"] += stats["videos"]
                    combined_folders[f_name]["images"] += stats["images"]
                    combined_folders[f_name]["total"] += stats["total"]
        except Exception as e:
            print(f"Error scanning {acc['name']}: {e}")

    added_files = [v["name"] for k, v in combined_files.items() if k not in prev_files]
    deleted_files = [v["name"] for k, v in prev_files.items() if k not in combined_files]

    net_variance = len(added_files) - len(deleted_files)
    variance_str = f"+{net_variance}" if net_variance >= 0 else f"{net_variance}"

    # Build Response Text
    report_lines = [
        "📊 <b>DRIVE MONITOR REPORT</b>\n",
        "<pre>",
        "---------------------------------------------",
        "FOLDER NAME           | VD | IM | TL |",
        "---------------------------------------------"
    ]

    def sort_key(name):
        if name == "Root / Main":
            return (0, 0, name)
        numbers = re.findall(r'\d+', name)
        if numbers:
            return (1, int(numbers[0]), name)
        return (2, 0, name)

    sorted_folders = sorted(combined_folders.keys(), key=sort_key)

    for f_name in sorted_folders:
        stats = combined_folders[f_name]
        f_display = (f_name[:21]).ljust(21)
        vd_str = f"{stats['videos']:02d}".rjust(2)
        im_str = f"{stats['images']:03d}".rjust(3)
        tl_str = f"{stats['total']:03d}".rjust(3)
        report_lines.append(f"{f_display} | {vd_str} | {im_str} | {tl_str}")

    report_lines.extend([
        "---------------------------------------------",
        "VD: Videos | IM: Images | TL: Total",
        "</pre>\n",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📋 <b>CHANGE REPORT</b>",
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    ])

    # Emergency Alert & File Names Section
    if deleted_files:
        report_lines.append("🚨 <b>EMERGENCY: MISSING/DELETED FILES FOUND!</b>")
        report_lines.append("➖ <b>DELETED FILES LIST:</b>")
        for d_name in deleted_files[:20]:
            report_lines.append(f"• <code>{d_name}</code>")
        if len(deleted_files) > 20:
            report_lines.append(f"<i>...and {len(deleted_files) - 20} more deleted.</i>")
        report_lines.append("")
    
    if added_files:
        report_lines.append("➕ <b>NEWLY ADDED FILES LIST:</b>")
        for a_name in added_files[:20]:
            report_lines.append(f"• <code>{a_name}</code>")
        if len(added_files) > 20:
            report_lines.append(f"<i>...and {len(added_files) - 20} more added.</i>")
        report_lines.append("")

    if not deleted_files and not added_files:
        report_lines.append("Looking Good (No missing files found)\n")

    scan_time = time.strftime("%d-%b-%Y %I:%M %p")

    report_lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📊 <b>SUMMARY</b>",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
        f"➕ Added (New)   : {len(added_files)} Files",
        f"➖ Missing (🚨)  : {len(deleted_files)} Files",
        f"📈 Net Variance  : {variance_str} File(s)\n",
        f"🕒 Last Scan : {scan_time}"
    ])

    final_report = "\n".join(report_lines)

    send_telegram_message(final_report)

    save_state({"files": combined_files})
    
