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
    return {"files": {}, "max_video_count": 0, "total_files": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_telegram_photo_url(photo_url):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url
    }
    requests.post(url, json=payload)

def generate_svg_dashboard_url(accounts_data, total_files, total_videos, recently_added, recently_deleted, folder_summary):
    # ఫోల్డర్ వివరాలు
    folder_text_list = []
    for f_name, stats in list(folder_summary.items())[:3]:
        folder_text_list.append(f"{f_name}: {stats['videos']} Vids")
    folder_str = "  |  ".join(folder_text_list) if folder_text_list else "None"

    # SVG గ్రాఫ్ బార్లు క్రియేట్ చేయడం
    max_vids = max([acc["videos"] for acc in accounts_data] + [1])
    bars_svg = ""
    colors = ["#00f2fe", "#e11d73", "#ff9a00"]
    
    x_pos = 70
    for i, acc in enumerate(accounts_data):
        height = int((acc["videos"] / max_vids) * 140)
        y_pos = 420 - height
        bar_color = colors[i % len(colors)]
        
        bars_svg += f'''
        <rect x="{x_pos}" y="{y_pos}" width="65" height="{height}" rx="6" fill="{bar_color}" />
        <text x="{x_pos + 32}" y="{y_pos - 10}" fill="#ffffff" font-size="16" font-weight="bold" text-anchor="middle">{acc['videos']}</text>
        <text x="{x_pos + 32}" y="445" fill="#94a3b8" font-size="14" font-weight="bold" text-anchor="middle">{acc['name']}</text>
        '''
        x_pos += 220

    # పూర్తి SVG Canvas టెంప్లేట్ (Dashboard Card)
    svg_code = f'''<svg xmlns="http://www.w3.org/2000/svg" width="750" height="480" viewBox="0 0 750 480">
        <rect width="100%" height="100%" fill="#0f172a"/>
        
        <!-- Header Banner -->
        <rect x="0" y="0" width="750" height="55" fill="#1e293b"/>
        <text x="25" y="36" fill="#00f2fe" font-size="20" font-family="Arial" font-weight="bold">MEGA CLOUD LIVE DASHBOARD</text>
        
        <!-- Stat Cards -->
        <!-- Total Files -->
        <rect x="25" y="75" width="160" height="75" rx="8" fill="#1e293b" stroke="#00f2fe" stroke-width="2"/>
        <text x="40" y="98" fill="#94a3b8" font-size="11" font-family="Arial" font-weight="bold">TOTAL FILES</text>
        <text x="40" y="132" fill="#ffffff" font-size="22" font-family="Arial" font-weight="bold">{total_files}</text>
        
        <!-- Total Videos -->
        <rect x="200" y="75" width="160" height="75" rx="8" fill="#1e293b" stroke="#e11d73" stroke-width="2"/>
        <text x="215" y="98" fill="#94a3b8" font-size="11" font-family="Arial" font-weight="bold">TOTAL VIDEOS</text>
        <text x="215" y="132" fill="#ffffff" font-size="22" font-family="Arial" font-weight="bold">{total_videos}</text>
        
        <!-- Added -->
        <rect x="375" y="75" width="160" height="75" rx="8" fill="#1e293b" stroke="#22c55e" stroke-width="2"/>
        <text x="390" y="98" fill="#94a3b8" font-size="11" font-family="Arial" font-weight="bold">RECENTLY ADDED</text>
        <text x="390" y="132" fill="#22c55e" font-size="22" font-family="Arial" font-weight="bold">+{recently_added}</text>
        
        <!-- Deleted -->
        <rect x="550" y="75" width="160" height="75" rx="8" fill="#1e293b" stroke="#ef4444" stroke-width="2"/>
        <text x="565" y="98" fill="#94a3b8" font-size="11" font-family="Arial" font-weight="bold">DELETED</text>
        <text x="565" y="132" fill="#ef4444" font-size="22" font-family="Arial" font-weight="bold">{recently_deleted}</text>

        <!-- Folders Section -->
        <rect x="25" y="165" width="685" height="45" rx="6" fill="#1e293b"/>
        <text x="40" y="192" fill="#38bdf8" font-size="13" font-family="Arial" font-weight="bold">FOLDERS: <tspan fill="#ffffff">{folder_str}</tspan></text>

        <!-- Graph Container -->
        <text x="25" y="240" fill="#38bdf8" font-size="13" font-family="Arial" font-weight="bold">VIDEOS PER ACCOUNT</text>
        <rect x="25" y="255" width="685" height="200" rx="8" fill="#0b1120"/>
        
        <!-- Horizontal Grid Lines -->
        <line x1="45" y1="420" x2="690" y2="420" stroke="#334155" stroke-width="1"/>
        <line x1="45" y1="350" x2="690" y2="350" stroke="#1e293b" stroke-width="1"/>
        <line x1="45" y1="280" x2="690" y2="280" stroke="#1e293b" stroke-width="1"/>
        
        <!-- Bars -->
        {bars_svg}
    </svg>'''

    # SVG ని Direct Chart Image URL గా మార్చడం
    encoded_svg = urllib.parse.quote(svg_code)
    return f"https://quickchart.io/chart?req={encoded_svg}"

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

        chart_url = generate_svg_dashboard_url(
            accounts_chart_data, 
            total_files, 
            total_videos, 
            recently_added, 
            recently_deleted + total_deleted_bin,
            folder_summary
        )

        send_telegram_photo_url(chart_url)

        save_state({
            "files": combined_files,
            "max_video_count": total_videos,
            "total_files": total_files
        })
    except Exception:
        pass
        
