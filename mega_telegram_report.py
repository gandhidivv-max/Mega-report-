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
    for key, value in os.environ.items():
        if key.startswith("MEGA_EMAIL_"):
            suffix = key.replace("MEGA_EMAIL_", "")
            pass_key = f"MEGA_PASSWORD_{suffix}"
            password = os.environ.get(pass_key)
            if value and password:
                accounts.append({
                    "email": value,
                    "pass": password,
                    "name": f"Account {suffix}"
                })
    if not accounts:
        single_email = os.environ.get("MEGA_EMAIL")
        single_pass = os.environ.get("MEGA_PASSWORD")
        if single_email and single_pass:
            accounts.append({"email": single_email, "pass": single_pass, "name": "Account 1"})
    return accounts

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"files": {}, "max_video_count": 0, "total_files": 0, "missing_videos": {}, "last_ping_time": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def perform_keep_alive(mega_instance, email):
    try:
        dummy_file = "keep_alive_ping.txt"
        with open(dummy_file, "w") as f:
            f.write(f"Account Keep Alive Ping at {time.ctime()}")
        
        uploaded_file = mega_instance.upload(dummy_file)
        time.sleep(2)
        mega_instance.delete(uploaded_file[0])
        
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
        return True
    except Exception as e:
        print(f"Ping failed for {email}: {e}")
        return False

def scan_mega_account(email, password, do_ping):
    mega = Mega()
    m = mega.login(email, password)
    
    ping_status = False
    if do_ping:
        ping_status = perform_keep_alive(m, email)

    files_data = m.get_files()
    account_files = {}
    trash_files = {}
    video_count = 0
    total_files = 0
    deleted_bin_count = 0

    for file_id, file_info in files_data.items():
        if file_info.get('t') == 0:
            file_name = file_info.get('a', {}).get('n', 'Unknown')
            parent_id = file_info.get('p', '')

            if parent_id == m.trash_id:
                deleted_bin_count += 1
                trash_files[file_id] = file_name
            else:
                total_files += 1
                unique_key = f"{email}_{file_id}"
                account_files[unique_key] = {
                    "name": file_name,
                    "email": email,
                    "file_id": file_id,
                    "is_video": file_name.lower().endswith(video_extensions)
                }
                if file_name.lower().endswith(video_extensions):
                    video_count += 1

    return account_files, trash_files, total_files, video_count, deleted_bin_count, ping_status

if __name__ == "__main__":
    try:
        mega_accounts = get_all_mega_credentials()
        if not mega_accounts:
            send_telegram_message("❌ *Error:* Credentials సరిగ్గా లేవు!")
            exit()

        prev_state = load_state()
        prev_files = prev_state.get("files", {})
        target_video_count = prev_state.get("max_video_count", 0)
        stored_missing_videos = prev_state.get("missing_videos", {})
        last_ping_time = prev_state.get("last_ping_time", 0)

        current_time = time.time()
        fifteen_days_sec = 15 * 24 * 60 * 60
        
        do_ping = (current_time - last_ping_time) >= fifteen_days_sec

        combined_files = {}
        all_trash_files = {}
        total_files = 0
        total_videos = 0
        total_deleted_bin = 0
        acc_summary = []
        pings_done = False

        for acc in mega_accounts:
            try:
                files, trash, t_files, v_count, d_bin, ping_ok = scan_mega_account(acc["email"], acc["pass"], do_ping)
                combined_files.update(files)
                all_trash_files.update(trash)
                total_files += t_files
                total_videos += v_count
                total_deleted_bin += d_bin
                
                ping_txt = " (🔄 15-Day Ping Done)" if ping_ok else ""
                acc_summary.append(f"• *{acc['name']}:* `{v_count}` Videos (`{t_files}` Files){ping_txt}")
                if ping_ok:
                    pings_done = True
            except Exception as e:
                acc_summary.append(f"• *{acc['name']}:* ❌ Error (`{str(e)}`)")

        if pings_done or last_ping_time == 0:
            last_ping_time = current_time

        if total_videos > target_video_count:
            target_video_count = total_videos

        deleted_keys = set(prev_files.keys()) - set(combined_files.keys())
        current_missing_videos = dict(stored_missing_videos)

        for key in deleted_keys:
            file_data = prev_files[key]
            if file_data.get("is_video"):
                file_id = file_data.get("file_id")
                if file_id in all_trash_files:
                    reason = "🗑️ Moved to Rubbish Bin (Manual Delete)"
                else:
                    reason = "⚠️ Permanently Removed / DMCA Takedown / Account Restriction"

                current_missing_videos[key] = {
                    "name": file_data.get("name"),
                    "account": file_data.get("email"),
                    "reason": reason
                }

        if total_videos >= target_video_count:
            current_missing_videos = {}

        if total_videos < target_video_count:
            missing_count = target_video_count - total_videos
            alert_msg = (
                "🚨🦺 *EMERGENCY ALERT! VIDEO DELETED!* 🦺🚨\n\n"
                f"📉 *ప్రస్తుత వీడియోలు:* `{total_videos}`\n"
                f"🎯 *Target కౌంట్:* `{target_video_count}`\n"
                f"❌ *తగ్గిన వీడియోల సంఖ్య:* `{missing_count}`\n\n"
                "📌 *డిలీట్ అయిన వీడియోల వివరాలు:*\n"
            )
            if current_missing_videos:
                for idx, (k, info) in enumerate(current_missing_videos.items(), 1):
                    alert_msg += (
                        f"\n*{idx}. ఫైల్ పేరు:* `{info['name']}`\n"
                        f"   📧 *అకౌంట్:* `{info['account']}`\n"
                        f"   ❓ *కారణం:* {info['reason']}\n"
                    )
            alert_msg += "\n❗ *గమనిక:* మళ్లీ కౌంట్ బ్యాలెన్స్ అయ్యే వరకు ఈ హెచ్చరిక ప్రతి రన్ లోనూ వస్తుంది!"
            send_telegram_message(alert_msg)

        report_text = (
            f"📊 *MEGA CLOUD LIVE REPORT ({len(mega_accounts)} ACCOUNTS)* 📊\n\n"
            f"📁 *All Files:* `{total_files}` | 🎬 *Videos:* `{total_videos}`\n"
            f"🎯 *Target Video Count:* `{target_video_count}`\n"
            f"🗑️ *Rubbish Bin:* `{total_deleted_bin}`\n\n"
            "👤 *అకౌంట్ల వివరాలు:*\n" + "\n".join(acc_summary)
        )
        send_telegram_message(report_text)

        new_state = {
            "files": combined_files,
            "max_video_count": target_video_count,
            "total_files": total_files,
            "missing_videos": current_missing_videos,
            "last_ping_time": last_ping_time
        }
        save_state(new_state)

    except Exception as e:
        send_telegram_message(f"❌ *Error Occurred:* `{str(e)}`")
  
