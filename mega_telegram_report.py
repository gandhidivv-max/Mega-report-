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

def send_telegram_photo(image_bytes):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {'photo': ('dashboard.png', image_bytes, 'image/png')}
    payload = {'chat_id': TELEGRAM_CHAT_ID}
    requests.post(url, data=payload, files=files)

def generate_html_dashboard_image(accounts_data, total_files, total_videos, recently_added, recently_deleted, folder_summary):
    # ఫోల్డర్ల వివరాల HTML
    folder_items_html = ""
    for f_name, stats in list(folder_summary.items())[:4]:
        folder_items_html += f"""
        <div style="background: #1e293b; padding: 8px 12px; border-radius: 6px; font-size: 13px; color: #cbd5e1;">
            📁 <strong style="color: #ffffff;">{f_name}</strong>: {stats['videos']} Videos <span style="color: #64748b;">({stats['files']} Files)</span>
        </div>
        """

    # అకౌంట్ బార్ చార్ట్ HTML
    max_vids = max([acc["videos"] for acc in accounts_data] + [1])
    bars_html = ""
    colors = ["#00f2fe", "#e11d73", "#ff9a00"]
    for i, acc in enumerate(accounts_data):
        height_pct = int((acc["videos"] / max_vids) * 100)
        bars_html += f"""
        <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
            <div style="color: #ffffff; font-weight: bold; margin-bottom: 5px; font-size: 14px;">{acc['videos']}</div>
            <div style="width: 45px; height: 120px; background: #1e293b; border-radius: 6px; display: flex; align-items: flex-end; overflow: hidden;">
                <div style="width: 100%; height: {height_pct}%; background: {colors[i % len(colors)]}; border-radius: 4px;"></div>
            </div>
            <div style="color: #94a3b8; margin-top: 8px; font-size: 12px; font-weight: bold;">{acc['name']}</div>
        </div>
        """

    # పూర్తి UI క్యాన్వాస్ Template
    html_template = f"""
    <div style="width: 650px; background: #0f172a; padding: 25px; font-family: Arial, sans-serif; color: white; border-radius: 12px;">
        <div style="font-size: 20px; font-weight: bold; margin-bottom: 20px; border-bottom: 2px solid #334155; padding-bottom: 10px; color: #00f2fe;">
            ⚡ MEGA CLOUD LIVE DASHBOARD
        </div>
        
        <!-- STATS CARDS -->
        <div style="display: flex; gap: 10px; margin-bottom: 20px;">
            <div style="flex: 1; background: #1e293b; padding: 12px; border-radius: 8px; border-left: 4px solid #00f2fe;">
                <div style="font-size: 11px; color: #94a3b8;">TOTAL FILES</div>
                <div style="font-size: 20px; font-weight: bold; margin-top: 4px;">{total_files}</div>
            </div>
            <div style="flex: 1; background: #1e293b; padding: 12px; border-radius: 8px; border-left: 4px solid #e11d73;">
                <div style="font-size: 11px; color: #94a3b8;">TOTAL VIDEOS</div>
                <div style="font-size: 20px; font-weight: bold; margin-top: 4px;">{total_videos}</div>
            </div>
            <div style="flex: 1; background: #1e293b; padding: 12px; border-radius: 8px; border-left: 4px solid #22c55e;">
                <div style="font-size: 11px; color: #94a3b8;">ADDED</div>
                <div style="font-size: 20px; font-weight: bold; color: #22c55e; margin-top: 4px;">+{recently_added}</div>
            </div>
            <div style="flex: 1; background: #1e293b; padding: 12px; border-radius: 8px; border-left: 4px solid #ef4444;">
                <div style="font-size: 11px; color: #94a3b8;">DELETED</div>
                <div style="font-size: 20px; font-weight: bold; color: #ef4444; margin-top: 4px;">{recently_deleted}</div>
            </div>
        </div>

        <!-- FOLDERS BREAKDOWN -->
        <div style="margin-bottom: 20px;">
            <div style="font-size: 12px; font-weight: bold; color: #38bdf8; margin-bottom: 8px;">FOLDERS BREAKDOWN</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                {folder_items_html}
            </div>
        </div>

        <!-- GRAPH SECTION -->
        <div>
            <div style="font-size: 12px; font-weight: bold; color: #38bdf8; margin-bottom: 12px;">VIDEOS PER ACCOUNT</div>
            <div style="display: flex; justify-content: space-around; background: #0b1120; padding: 15px; border-radius: 8px;">
                {bars_html}
            </div>
        </div>
    </div>
    """

    # HTML ని Image గా మార్చడానికి QuickChart Render API వాడటం
    render_url = "https://quickchart.io/render"
    payload = {
        "html": html_template,
        "width": 700,
        "height": 550,
        "devicePixelRatio": 2
    }
    
    response = requests.post(render_url, json=payload)
    if response.status_code == 200:
        return response.content
    return None

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

        img_bytes = generate_html_dashboard_image(
            accounts_chart_data, 
            total_files, 
            total_videos, 
            recently_added, 
            recently_deleted + total_deleted_bin,
            folder_summary
        )

        if img_bytes:
            send_telegram_photo(img_bytes)

        save_state({
            "files": combined_files,
            "max_video_count": total_videos,
            "total_files": total_files
        })
    except Exception:
        pass
        
