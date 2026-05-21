import subprocess
import json
import os
import sys
import re
import textwrap
import shutil
import zipfile
import time
import argparse
from datetime import datetime

try:
    import colorama
    colorama.init()
    USE_COLOR = True
except ImportError:
    USE_COLOR = False

COLOR_RESET = "\033[0m"
COLOR_CATBOX = "\033[94m"
COLOR_MEGA = "\033[91m"
COLOR_CUBARI = "\033[92m"
COLOR_MANGADEX = "\033[93m"
COLOR_PROMPT = "\033[1;32m"
COLOR_WORDPRESS = "\033[95m"
COLOR_MANGATARO = "\033[96m"
IMPORTANT_INFO = "\033[1;96m"

# --- CONFIGURATION ---
# Store your hashes/logins safely.
# These values have been moved to series_config.json under upload_credentials.

def run_cmd(cmd, cwd=None):
    """Utility to run commands and capture output."""
    try:
        # We capture stdout (the print output)
        result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}\n{e.stderr}")
        return None
        
def get_cubari_url(series_name, chapter_number, config):
    """
    Constructs the Cubari URL using the data from series_config.json
    """
    if series_name in config:
        # Access the 'cubari_base' key directly from the config
        base_url = config[series_name]["cubari_base"]
        ch_str = format_chapter(chapter_number)
        return f"{base_url}{ch_str}/1/"
    return None
    
def get_series_from_title(post_title, config):
    """
    Looks for the series name in the post title based on the keys 
    in series_config.json.
    """    
    # We sort keys by length (longest first) to prevent partial matching 
    # (e.g., matching "Fantasia" when the title is "Fantasia 2")
    sorted_series = sorted(config.keys(), key=len, reverse=True)
    
    for series in sorted_series:
        if series.lower() in post_title.lower():
            return series
    return None
    
def find_target_folder(base_folder, chapter, volume):
    """
    Finds a folder matching "V{volume} Ch{chapter}" or just "Ch{chapter}".
    """
    # Pad chapter to 3 digits (e.g., 36 -> 036)
    ch_str = format_chapter(chapter)
    
    # Construct regex:
    # Optional V##, then Ch###, then anything else
    if volume:
        vol_str = str(volume).zfill(2)
        pattern = re.compile(rf"V{vol_str} Ch{ch_str}.*", re.IGNORECASE)
    else:
        pattern = re.compile(rf".*Ch{ch_str}.*", re.IGNORECASE)
        
    for name in os.listdir(base_folder):
        if pattern.match(name) and os.path.isdir(os.path.join(base_folder, name)):
            return name
    return None
    
def get_folder_index(base_folder, target_folder_name):
    """
    Lists directories in base_folder, sorts them alphabetically, 
    and returns the 1-based index of the target folder.
    """
    # 1. Get all items in the directory
    all_items = os.listdir(base_folder)
    
    # 2. Filter for directories only (ignore files)
    dirs = [d for d in all_items if os.path.isdir(os.path.join(base_folder, d))]
    
    # 3. Sort alphabetically
    dirs.sort()
    
    # 4. Find the target index (1-based)
    if target_folder_name in dirs:
        return dirs.index(target_folder_name) + 1
    else:
        return None
        
def run_cmd_silent(cmd, cwd=None):
    """Utility to run commands and ignore all output/errors."""
    try:
        # stdout=subprocess.DEVNULL and stderr=subprocess.DEVNULL discard all output
        subprocess.run(cmd, cwd=cwd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        # We still return False so you know if it actually crashed
        return False

def color_text(text, color):
    if not USE_COLOR:
        return text
    return f"{color}{text}{COLOR_RESET}"

def format_chapter(chapter_str):
    """Pads chapter number for folder/URL matching. Handles decimals like 36.5 → 036.5"""
    parts = str(chapter_str).split(".")
    parts[0] = parts[0].zfill(3)
    return ".".join(parts)    

def wait_until_scheduled(scheduled_time_str):
    """
    Waits until the scheduled time, displaying a countdown with progress bar.
    scheduled_time_str format: "2026-05-19 11:00:00"
    """
    try:
        scheduled = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print(color_text(f"Error: Invalid schedule format. Use 'YYYY-MM-DD HH:MM:SS'", IMPORTANT_INFO))
        sys.exit(1)
    
    now = datetime.now()
    if scheduled <= now:
        print(color_text(f"Scheduled time {scheduled_time_str} is in the past.", IMPORTANT_INFO))
        return
    
    print(color_text("Waiting for scheduled time before proceeding with uploads.", COLOR_PROMPT))
    
    start_time = datetime.now()
    total_delta = scheduled - start_time
    total_seconds = total_delta.total_seconds()
    
    while True:
        now = datetime.now()
        if now >= scheduled:
            print(color_text("\n✅ Scheduled time reached! Starting uploads...", COLOR_PROMPT))
            break
        
        delta = scheduled - now
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        countdown = f"Time remaining: {days}d {hours:02d}h {minutes:02d}m {seconds:02d}s"
        
        # Calculate progress percentage
        elapsed = (now - start_time).total_seconds()
        percent = int((elapsed / total_seconds) * 100)
        percent = min(percent, 100)  # Cap at 100%
        
        # Create progress bar (20 characters wide)
        bar_width = 20
        filled = int((percent / 100) * bar_width)
        empty = bar_width - filled
        progress_bar = f"[{'█' * filled}{'░' * empty}] {percent}%"
        
        # Display on a single line, overwrite with \r
        output = f"{countdown}  {progress_bar}"
        print(color_text(output, COLOR_PROMPT), end="\r", flush=True)
        
        time.sleep(1)


def boxed_url(label, url, color):
    if not url:
        return color_text(f"[ ] {label}: <no URL returned>", color)
    clean_url = url.strip()
    content = f" {clean_url} "
    width = len(content)
    border = "+" + "=" * width + "+"
    label_text = f"✅ {label}"
    label_line = label_text.center(width + 2)
    return "\n".join([
        color_text(border, color),
        color_text(label_line, color),
        color_text(f"|{content}|", color),
        color_text(border, color)
    ])


def boxed_section(title, lines, color):
    if isinstance(lines, str):
        lines = lines.splitlines()
    title_text = f"-------- {title} --------"
    width = max(len(title_text), *(len(line) for line in lines))
    border = "+" + "-" * (width + 2) + "+"
    output = [color_text(border, color)]
    output.append(color_text(f"| {title_text.ljust(width)} |", color))
    output.append(color_text(border, color))
    for line in lines:
        output.append(color_text(f"| {line.ljust(width)} |", color))
    output.append(color_text(border, color))
    return "\n".join(output)


def run_cmd_capture(cmd, cwd=None, input_data=None, env=None, shell=True):
    """Run a command and capture stdout/stderr for debug output."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=shell,
        env=env,
        encoding='utf-8'
    )
    return result


def run_cmd_stream(cmd, cwd=None, input_data=None, env=None, shell=True, color=None):
    """Run a command and stream stdout/stderr in real time."""
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.PIPE if input_data is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=shell,
        env=env,
        encoding='utf-8'
    )
    output_lines = []
    if input_data is not None and process.stdin:
        process.stdin.write(input_data)
        process.stdin.close()
    if process.stdout:
        for line in process.stdout:
            line = line.rstrip("\n")
            if color:
                print(color_text(line, color), flush=True)
            else:
                print(line, flush=True)
            output_lines.append(line)
    process.wait()
    result = subprocess.CompletedProcess(
        args=cmd,
        returncode=process.returncode,
        stdout="\n".join(output_lines),
        stderr=""
    )
    return result
        
def save_release_links(links_dict):
    with open("release_links.txt", "w") as f:
        for platform, url in links_dict.items():
            f.write(f"{platform.upper()}={url}\n")
            
def extract_url(raw: str) -> str:
    match = re.search(r'https?://\S+', raw)
    return match.group(0).strip() if match else raw.strip()
    
def normalize_url(raw: str) -> str:
    url = extract_url(raw or "")
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return ""
    
def extract_title(folder_name):
    # Pattern explanation:
    # (V\d+\s+)?      -> Optional: 'V' followed by digits and space
    # (Ch|CH)\d+\s+   -> Mandatory: 'Ch' or 'CH' followed by digits and space
    # (.*)            -> Capture group: the actual title
    pattern = r"(?:V\d+\s+)?(?:Ch|CH)\d+\s+(.*)"
    
    match = re.search(pattern, folder_name)
    if match:
        return match.group(1).strip()
    return None # Return None if no pattern matches

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Release updater with optional scheduled uploads")
    parser.add_argument("--schedule", type=str, help="Schedule uploads for a specific time (format: YYYY-MM-DD HH:MM:SS)")
    parser.add_argument(
        "--skip",
        nargs="+",
        type=str.lower,
        choices=["catbox", "mega", "cubari", "mangadex", "mangataro"],
        help="Upload targets to skip"
    )
    args = parser.parse_args()
    skip_targets = set(args.skip or [])
    
    # 1. Inputs
    post_title = input(color_text("Enter WordPress Post Title: ", COLOR_PROMPT)).strip()
    file_path = input(color_text("Enter Full Path to Zip: ", COLOR_PROMPT))
    chapter = input(color_text("Enter Chapter Number: ", COLOR_PROMPT))
    volume = input(color_text("Enter Volume Number (optional): ", COLOR_PROMPT))
    chapter_name = input(color_text("Enter Chapter Name (leave blank to auto-fetch): ", COLOR_PROMPT)).strip()

    # 2. Setup Configuration
    with open('series_config.json', 'r') as f:
        config = json.load(f)
        
    ssh_cfg = config["ssh_settings"]
    uploader_locations = config["uploader_locations"]
    upload_creds = config.get("upload_credentials", {})
    CATBOX_USERHASH = upload_creds.get("catbox_userhash")
    MEGA_LOGIN = upload_creds.get("mega_login")
    MEGA_PASS = upload_creds.get("mega_pass")
    if not CATBOX_USERHASH or not MEGA_LOGIN or not MEGA_PASS:
        print(color_text("Missing upload_credentials in series_config.json.", IMPORTANT_INFO))
        sys.exit(1)
        
    series = get_series_from_title(post_title, config) # Detect name
    if not series:
        print(color_text("Could not detect series from title! Please check your series_config.json.", IMPORTANT_INFO))
        sys.exit(1)
        
    series_data = config[series]
    base_path = series_data["kaguya_folder"]
    toml_file = series_data["toml"]
    downloads_page = series_data.get("downloads_page", "")
    
    print(color_text(f"Detected series: {series}", IMPORTANT_INFO))
    
    # 3. Find folder dynamically
    target_folder = find_target_folder(base_path, chapter, volume)
    if not target_folder:
        print(color_text(f"Error: Could not find a folder matching that chapter/volume.", IMPORTANT_INFO))
        sys.exit(1)
    print(color_text(f"Found folder: {target_folder}", IMPORTANT_INFO))
    
    target_path = os.path.join(base_path, target_folder)
    print(color_text(f"Cleaning and updating folder: {target_path}", IMPORTANT_INFO))
    
    if not chapter_name:
        chapter_name = extract_title(target_folder) or ""
        if chapter_name:
            print(color_text(f"Extracted chapter title: {chapter_name}", IMPORTANT_INFO))
        else:
            print(color_text("Chapter title could not be extracted.", IMPORTANT_INFO))
        
    # Delete existing contents
    for item in os.listdir(target_path):
        item_path = os.path.join(target_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
    print(color_text(f"Old Kaguya folder contents deleted successfully.", IMPORTANT_INFO))
            
    # Extract zip directly into target_path
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        # This iterates through files and extracts them to the root of target_path
        for member in zip_ref.namelist():
            # Get the filename only (stripping existing sub-folders in the zip)
            filename = os.path.basename(member)
            if filename: # Ignore directory entries in the zip
                source = zip_ref.open(member)
                target = open(os.path.join(target_path, filename), "wb")
                with source, target:
                    shutil.copyfileobj(source, target)
    print(color_text(f"Kaguya folder contents updated successfully.", IMPORTANT_INFO))
    
    # 4. Get index
    folder_idx = get_folder_index(base_path, target_folder)
    print(color_text(f"Detected Kaguya folder index: {folder_idx}", IMPORTANT_INFO))
    
    # 4.5. Check for scheduled upload
    if args.schedule:
        wait_until_scheduled(args.schedule)
        
    # 5. CATBOX
    if "catbox" not in skip_targets:
        print(color_text("Uploading to Catbox...", COLOR_CATBOX))
        catbox_result = run_cmd_stream(
            f'catbox "{file_path}" --userhash {CATBOX_USERHASH}',
            env=os.environ.copy(),
            shell=True,
            color=COLOR_CATBOX
        )
        if catbox_result.returncode != 0:
            print(color_text("⚠️ Catbox upload failed (non-zero exit code). URL will be empty.", COLOR_CATBOX))
        catbox_url = normalize_url(catbox_result.stdout)
        if not catbox_url:
            print(color_text("⚠️ Catbox upload returned no valid URL.", COLOR_CATBOX))
    else:
        print(color_text("Skipping Catbox upload.", COLOR_CATBOX))
        catbox_url = ""
    print(boxed_url("Catbox", catbox_url, COLOR_CATBOX))

    # 6. MEGA
    if "mega" not in skip_targets:
        print(color_text("Uploading to Mega...", COLOR_MEGA))
        filename = os.path.basename(file_path)
        check_login = run_cmd_capture("mega-ls")
        print(color_text("Checking login to Mega...", COLOR_MEGA))
        if check_login.returncode != 0:
            print(color_text("Not logged in. Logging in...", COLOR_MEGA))
            login_result = run_cmd_capture(f'mega-login {MEGA_LOGIN} {MEGA_PASS}')
            print(color_text("Mega login stdout:", COLOR_MEGA))
            print(color_text(login_result.stdout.strip(), COLOR_MEGA))
            if login_result.stderr:
                print(color_text("Mega login stderr:", COLOR_MEGA))
                print(color_text(login_result.stderr.strip(), COLOR_MEGA))
        print(color_text("Logged in.", COLOR_MEGA))
        print(color_text("Removing old MEGA file...", COLOR_MEGA))
        rm_result = run_cmd_capture(f'mega-rm -f "{filename}"')
        if rm_result.stdout.strip() or rm_result.stderr.strip():
            print(color_text("Mega remove output:", COLOR_MEGA))
            print(color_text(rm_result.stdout.strip(), COLOR_MEGA))
            if rm_result.stderr:
                print(color_text(rm_result.stderr.strip(), COLOR_MEGA))
        print(color_text("Mega put output:", COLOR_MEGA))
        put_result = run_cmd_stream(
            f'mega-put "{file_path}"',
            env=os.environ.copy(),
            shell=True,
            color=COLOR_MEGA
        )
        if put_result.returncode != 0:
            print(color_text("Warning: Mega put failed.", COLOR_MEGA))
        print(color_text("Mega export output:", COLOR_MEGA))
        mega_export = run_cmd_stream(
            f'mega-export -a "{filename}"',
            env=os.environ.copy(),
            shell=True,
            color=COLOR_MEGA
        )
        if mega_export.returncode != 0:
            print(color_text("Warning: Mega export failed.", COLOR_MEGA))
        mega_url = normalize_url(mega_export.stdout)
    else:
        print(color_text("Skipping Mega upload.", COLOR_MEGA))
        mega_url = ""
    print(boxed_url("Mega", mega_url, COLOR_MEGA))

    # 7. CUBARI
    if "cubari" not in skip_targets:
        print(color_text("Running Cubari Auto-Kaguya...", COLOR_CUBARI))
        if folder_idx:
            print(color_text(f"Detected folder index: {folder_idx}", COLOR_CUBARI))
            cmd = f'python auto_kaguya.py --base_folder "{base_path}" --number {folder_idx}'
            cubari_env = os.environ.copy()
            cubari_env['PYTHONIOENCODING'] = 'utf-8'
            cubari_env['PYTHONUTF8'] = '1'
            print(color_text("Auto-Kaguya output:", COLOR_CUBARI))
            cubari_result = run_cmd_stream(
                cmd,
                cwd=uploader_locations['auto_kaguya'],
                env=cubari_env,
                shell=True,
                color=COLOR_CUBARI
            )
            if cubari_result.returncode != 0:
                print(color_text("Warning: Kaguya tool encountered an issue.", COLOR_CUBARI))
        else:
            print(color_text("Folder not found in directory!", COLOR_CUBARI))
        cubari_url = get_cubari_url(series, chapter, config)
    else:
        print(color_text("Skipping Cubari auto-upload.", COLOR_CUBARI))
        cubari_url = ""
    print(boxed_url("Cubari", cubari_url, COLOR_CUBARI))

    # 8. MANGADEX
    if "mangadex" not in skip_targets:
        print(color_text("Uploading to Mangadex...", COLOR_MANGADEX))
        mangadex_cmd = f'py -u mangadex_uploader.py --series {toml_file} --zip "{file_path}" --chapter {chapter} --title "{chapter_name}"'
        if volume:
            mangadex_cmd += f' --volume {volume}'
        print(color_text(mangadex_cmd, COLOR_MANGADEX))
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = run_cmd_stream(
            mangadex_cmd,
            cwd=uploader_locations["mangadex_uploader"],
            input_data="y\n",
            env=env,
            shell=True,
            color=COLOR_MANGADEX
        )

        print(color_text(f"MangaDex: Return Code: {result.returncode}", COLOR_MANGADEX))

        # Extract the URL
        md_url = ""
        for line in result.stdout.splitlines():
            if line.startswith("FINAL_URL:"):
                md_url = normalize_url(line.split("FINAL_URL:")[1].strip())
                break
    else:
        print(color_text("Skipping MangaDex upload.", COLOR_MANGADEX))
        md_url = ""
    print(boxed_url("MangaDex", md_url, COLOR_MANGADEX))
    
    # 9. MANGATARO
    if "mangataro" not in skip_targets:
        print(color_text("Uploading to Mangataro...", COLOR_MANGATARO))
        # Use f-strings to insert the dynamic series variable
        mt_cmd = f'python -u mangataro_uploader.py "{series}" {chapter} "{chapter_name}" "{file_path}"'
        mt_result = run_cmd_stream(
            mt_cmd,
            cwd=uploader_locations['mangataro_uploader'],
            env=os.environ.copy(),
            shell=True,
            color=COLOR_MANGATARO
        )

        # Detect HTML error responses (e.g. Cloudflare 524 timeout pages)
        stdout_stripped = mt_result.stdout.strip() if mt_result.stdout else ""
        if stdout_stripped.startswith("<!DOCTYPE") or stdout_stripped.startswith("<html"):
            status_match = re.search(r'Error code (\d+)', stdout_stripped)
            status_hint = f" (HTTP {status_match.group(1)})" if status_match else ""
            print(color_text(f"❌ Mangataro returned an HTML error page{status_hint} — the server timed out or is down. Skipping.", COLOR_MANGATARO))
            mt_url = ""
        elif mt_result.returncode != 0:
            print(color_text("Warning: Mangataro upload failed.", COLOR_MANGATARO))
            mt_url = ""
        elif "View here: " in stdout_stripped:
            mt_url = normalize_url(stdout_stripped.split("View here: ")[1].strip())
        else:
            mt_url = ""
    else:
        print(color_text("Skipping Mangataro upload.", COLOR_MANGATARO))
        mt_url = ""

    print(boxed_section(
        "ALL LINKS",
        [
            f"Catbox: {catbox_url}",
            f"Mega: {mega_url}",
            f"Cubari: {cubari_url}",
            f"MangaDex: {md_url}",
            f"MangaTaro: {mt_url}"
        ],
        COLOR_CATBOX
    ))
    
    # Save the links to your local file
    links = {
        "CATBOX": catbox_url,
        "MEGA": mega_url,
        "CUBARI": cubari_url,
        "MANGADEX": md_url,
        "MANGATARO": mt_url
    }
    save_release_links(links)
    print(color_text("Saved release links to release_links.txt", COLOR_PROMPT))
    
    if not post_title:
        print(color_text("WordPress post title is blank; skipping WordPress post/page update.", COLOR_WORDPRESS))
        return
    
    print(color_text("Updating WordPress post...", COLOR_WORDPRESS))
    
    # You need to setup an SSH key and config for passwordless access to the server for this to work.
    # Note this updates all URLs in the post content that match the platforms. Also this applies to drafts as well as published posts.
    # 1. Prepare the remote script as a simple string
    remote_script = f"""
      cd public_html
      
      # Set variables on the remote side
      CATBOX="{catbox_url}"
      MEGA="{mega_url}"
      CUBARI="{cubari_url}"
      MANGADEX="{md_url}"
      MANGATARO="{mt_url}"
      
      POST_TITLE="{post_title}"
      PAGE_SLUG="{downloads_page}"
      CHAPTER="{chapter}"
      POST_ID=$(wp post list --title="$POST_TITLE" --format=ids)
      PAGE_ID=$(wp post list --post_type=page --name="$PAGE_SLUG" --format=ids)
      
      if [ -z "$POST_ID" ]; then
        echo "Error: Could not find post with title '$POST_TITLE'"
        exit 1
      fi
      
      content_cmd="wp post get $POST_ID --field=content"
      if [ -n "$CATBOX" ]; then
        content_cmd="$content_cmd | sed -E 's|https?://([^.]+\\.)*catbox\\.moe[^\\"[:space:]]*|'"$CATBOX"'|g'"
      fi
      if [ -n "$MEGA" ]; then
        content_cmd="$content_cmd | sed -E 's|https?://([^.]+\\.)?mega\\.nz[^\\"[:space:]]*|'"$MEGA"'|g'"
      fi
      if [ -n "$CUBARI" ]; then
        content_cmd="$content_cmd | sed -E 's|https?://([^.]+\\.)?cubari\\.moe[^\\"[:space:]]*|'"$CUBARI"'|g'"
      fi
      if [ -n "$MANGADEX" ]; then
        content_cmd="$content_cmd | sed -E 's|https?://([^.]+\\.)?mangadex\\.org[^\\"[:space:]]*|'"$MANGADEX"'|g'"
      fi
      if [ -n "$MANGATARO" ]; then
        content_cmd="$content_cmd | sed -E 's|https?://([^.]+\\.)?mangataro\\.org[^\\"[:space:]]*|'"$MANGATARO"'|g'"
      fi
      eval "$content_cmd | wp post update $POST_ID -"
      echo "REMOTE_POST_UPDATED"

      if [ -n "$PAGE_ID" ] && [ -n "$MEGA" ]; then
        wp post get $PAGE_ID --field=content | sed -E "s|<a href=\\\"[^\\\"]*\\\">Chapter[[:space:]]*$CHAPTER</a>|<a href=\\\"$MEGA\\\">Chapter $CHAPTER</a>|g" | wp post update $PAGE_ID -
        echo "REMOTE_PAGE_UPDATED"
      elif [ -n "$PAGE_ID" ]; then
        echo "Warning: Mega URL not available; release page update skipped."
      else
        echo "Warning: Could not find page with slug '$PAGE_SLUG'"
      fi
    """
    
    # Strip any stray \r characters from the script string
    clean_script = remote_script.replace('\r', '')
    clean_script = clean_script.replace('\r\n', '\n').replace('\r', '\n')

    # 2. Run the command by piping the script into SSH's stdin
    ssh_cmd = [
        "ssh",
        "-i", ssh_cfg["key_path"],
        f"{ssh_cfg['user']}@{ssh_cfg['host']}",
        "/bin/bash -s"
    ]
    
    # This sends the script to the remote shell WITHOUT cramming it into a single line
    result = subprocess.run(
        ssh_cmd,
        input=clean_script.encode('utf-8'),
        capture_output=True,
        text=False
    )
    
    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
    stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""

    if result.returncode == 0:
        if "REMOTE_POST_UPDATED" in stdout:
            print(color_text("✅WordPress NEWS POST update completed.", COLOR_WORDPRESS))
        else:
            print(color_text("⚠️WordPress NEWS POST update completed, but no remote success marker was found.", COLOR_WORDPRESS))

        if "REMOTE_PAGE_UPDATED" in stdout:
            print(color_text("✅WordPress RELEASE PAGE update completed.", COLOR_WORDPRESS))
        elif "Warning: Could not find page with slug" in stdout:
            print(color_text("❌WordPress RELEASE PAGE update skipped: page slug not found.", COLOR_WORDPRESS))
        else:
            print(color_text("⚠️WordPress RELEASE PAGE update completed, but no remote marker was found.", COLOR_WORDPRESS))
    else:
        print(color_text("WordPress update failed!", COLOR_WORDPRESS))
        print(color_text("WordPress update stderr:", COLOR_WORDPRESS))
        print(color_text(stderr.strip(), COLOR_WORDPRESS))

if __name__ == "__main__":
    main()