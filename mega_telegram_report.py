def scan_mega_account(email, password, do_ping):
    mega = Mega()
    m = None
    
    for attempt in range(3):
        try:
            # MEGA బాట్ డిటెక్షన్ దాటవేయడానికి 12 సెకన్ల విరామం
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
    
