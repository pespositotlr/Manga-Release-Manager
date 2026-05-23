# Manga Release Manager

A Python automation tool that orchestrates multi-platform manga chapter releases from a single command. Given a ZIP archive and some basic metadata, it uploads to **Catbox.moe**, **Mega.nz**, **Cubari** (via ImageChest/Kaguya), **MangaDex**, and **Mangataro** — then automatically updates the corresponding WordPress news post and downloads page with the new links.

## Related Tools

This script acts as an orchestrator around several other tools. You'll need to set them up separately:

- [**Mangadex-Scheduled-Uploader**](https://github.com/pespositotlr/Mangadex-Scheduled-Uploader) — Handles MangaDex chapter uploads
- [**Mangataro-Scheduled-Uploader**](https://github.com/pespositotlr/Mangataro-Scheduled-Uploader) — Handles Mangataro chapter uploads
- [**Auto-Kaguya**](https://github.com/pespositotlr/auto-kaguya) (Fork of wotakumoe/kaguya) — Uploads images to ImageChest for Cubari reader links (see note below)
- **catbox CLI** — Must be installed and on your PATH for Catbox uploads
- **MEGAcmd** — Must be installed and on your PATH for Mega uploads (`mega-login`, `mega-put`, `mega-export`)
- **WP-CLI** — Must be accessible on your remote server via SSH for WordPress updates

> **Kaguya note:** This script is designed to interface with Auto-Kaguya, a custom fork of the [original Kaguya](https://github.com/wotakumoe/kaguya). This fork includes an auto_kaguya.py wrapper that bypasses interactive prompts via a local auto.txt configuration, ensuring the Manga-Release-Manager can proceed through the upload sequence without manual input.

## Features

- Single-command release to five platforms simultaneously
- Detects the series automatically from your WordPress post title
- Finds the correct Kaguya upload folder by chapter/volume number, wipes old pages, and replaces them with the new ZIP contents (so re-releases work cleanly)
- Auto-extracts chapter title from the folder name if not provided manually
- Constructs the Cubari reader URL automatically from your config
- Updates WordPress news posts **and** the downloads page via SSH + WP-CLI — no manual copy-pasting of links
- Skips the WordPress update entirely if post title is left blank
- Optional `--schedule` flag to delay uploads until a specific date/time, with a live countdown progress bar (ZIP extraction and folder prep happen immediately; only the uploads wait)
- Color-coded terminal output per platform for easy reading, with live stdout/stderr output from each sub-tool
- Saves all generated links to `release_links.txt`

## Prerequisites

- Python 3.11+
- `colorama` Python package (`pip install colorama`)
- catbox CLI tool on your PATH
- MEGAcmd on your PATH
- SSH key-based access to your WordPress server (passwordless — the script pipes commands via SSH)
- WP-CLI installed on the remote server

## Installation

```
git clone https://github.com/pespositotlr/Manga-Release-Manager
cd Manga-Release-Manager
pip install colorama
```

Also clone and set up the related uploader tools linked above, noting their own installation steps.

## Configuration

Create a `series_config.json` file in the same directory as `release-updater.py`. It has four top-level sections plus one entry per series:

```json
{
  "ssh_settings": {
    "host": "your.server.ip.or.hostname",
    "user": "your-ssh-username",
    "key_path": "C:\\Users\\you\\.ssh\\id_rsa"
  },
  "uploader_locations": {
    "mangadex_uploader": "C:\\path\\to\\Mangadex-Scheduled-Uploader",
    "mangataro_uploader": "C:\\path\\to\\Mangataro-Scheduled-Uploader",
    "auto_kaguya": "C:\\path\\to\\kaguya"
  },
  "upload_credentials": {
    "catbox_userhash": "your_catbox_userhash",
    "mega_login": "you@example.com",
    "mega_pass": "your_mega_password"
  },
  "My Manga Series": {
    "toml": "my_manga_series.toml",
    "cubari_base": "https://cubari.moe/read/gist/BASE64GISTID/",
    "kaguya_folder": "C:\\path\\to\\kaguya\\uploads\\My Manga Series",
    "downloads_page": "my-manga-series-downloads"
  }
}
```

### Config field reference

**`ssh_settings`**

| Field | Description |
| --- | --- |
| `host` | IP address or hostname of your WordPress server |
| `user` | SSH username |
| `key_path` | Path to your private SSH key (passwordless auth required) |

**`uploader_locations`**

| Field | Description |
| --- | --- |
| `mangadex_uploader` | Directory of your Mangadex-Scheduled-Uploader clone |
| `mangataro_uploader` | Directory of your Mangataro-Scheduled-Uploader clone |
| `auto_kaguya` | Directory of your Kaguya clone |

**`upload_credentials`**

| Field | Description |
| --- | --- |
| `catbox_userhash` | Your Catbox.moe user hash (for persistent file ownership) |
| `mega_login` | Your Mega.nz account email |
| `mega_pass` | Your Mega.nz account password |

**Per-series entries** (key = exact series name as it appears in your WordPress post title)

| Field | Description |
| --- | --- |
| `toml` | The `.toml` config filename used by Mangadex-Scheduled-Uploader |
| `cubari_base` | Base Cubari URL up to (but not including) the chapter number |
| `kaguya_folder` | Absolute path to the folder containing chapter subfolders for Kaguya |
| `downloads_page` | WordPress page slug for your downloads/releases archive page |

### Kaguya folder structure

The script expects your Kaguya folder to contain chapter subfolders named in the format `V## Ch###` or `Ch###`, for example:

```
My Manga Series/
  V01 Ch001 The Beginning/
  V01 Ch002 Another Chapter/
  Ch003 Standalone Chapter/
```

The script matches on chapter (and optionally volume) number, clears the folder contents, then extracts the new ZIP into it before running Kaguya. Files from the ZIP are extracted flat into the target folder (any sub-folder structure inside the ZIP is stripped).

The chapter title is also automatically extracted from the folder name (everything after the `Ch###` prefix) if you leave the chapter name prompt blank.

### WordPress setup

The WordPress update works by SSHing into your server and running WP-CLI commands to find your post by title and your downloads page by slug, then replacing existing URLs in the content with the newly generated ones.

Rather than matching on link text labels, the script identifies existing links by their **URL domain or file extension** — so it doesn't matter what the visible link text says. The sed replacements target:

- URLs containing `catbox.moe` → replaced with the new Catbox link
- URLs containing `mega.nz` → replaced with the new Mega link
- URLs containing `cubari.moe` → replaced with the new Cubari link
- URLs containing `mangadex.org` → replaced with the new MangaDex link
- URLs containing `mangataro.org` → replaced with the new Mangataro link

This means your WordPress post just needs to have existing links to those domains — the link text/label can be anything you like.

The downloads page update finds chapter links matching `<a href="...">Chapter N</a>` (where N is the chapter number you entered) and replaces the URL with the new Mega link.

You need passwordless SSH key access to your server for this to work. The script pipes a remote bash script into `ssh` via stdin rather than passing commands as a single inline argument.

## Usage

### Basic usage

```
python release-updater.py
```

The script will prompt you for:

- **WordPress Post Title** — used to detect the series from your config and to find the post to update (leave blank to skip the WordPress update entirely)
- **Full Path to Zip** — the release archive (e.g. `C:\Releases\Ch036.zip`)
- **Chapter Number** — supports decimals (e.g. `36`, `36.5`)
- **Volume Number** — optional, leave blank if not applicable
- **Chapter Name** — optional; if left blank, it will be extracted from the Kaguya folder name automatically

### Scheduled release

Use `--schedule` to delay all uploads until a specific time:

```
python release-updater.py --schedule "2026-06-01 12:00:00"
```

The script will prepare everything (extract the ZIP into the Kaguya folder, detect the series, etc.) immediately, then display a live countdown progress bar and start uploading when the scheduled time arrives.

## What it does, step by step

1. Reads your inputs and loads `series_config.json`
2. Detects the series from the WordPress post title
3. Finds the matching chapter folder inside `kaguya_folder`, deletes its current contents, and extracts the ZIP into it (files are extracted flat — sub-folders inside the ZIP are ignored)
4. Auto-extracts the chapter title from the folder name if none was provided
5. Determines the chapter's index position within the folder (needed by Kaguya)
6. *(If `--schedule` was passed, waits until the scheduled time with a live countdown)*
7. Uploads the ZIP to **Catbox.moe** and captures the URL
8. Uploads the ZIP to **Mega.nz** (logs in if needed, removes any existing file with the same name, uploads, exports a public link)
9. Runs **Auto-Kaguya** (`auto_kaguya.py`) against the updated folder to push pages to ImageChest and update the Cubari gist; constructs the Cubari reader URL from config
10. Runs **Mangadex-Scheduled-Uploader** with the series TOML, ZIP path, chapter number, volume, and title
11. Runs **Mangataro-Scheduled-Uploader** with the series name, chapter number, title, and ZIP path
12. Prints a summary box with all five URLs and saves them to `release_links.txt`
13. SSHes into your WordPress server and updates the news post and downloads page links by matching on URL domain/extension

## Output

All generated links are printed to the terminal in a formatted summary and also written to `release_links.txt` in the working directory:

```
CATBOX=https://files.catbox.moe/xxxxxx.zip
MEGA=https://mega.nz/file/xxxxxxxx
CUBARI=https://cubari.moe/read/gist/BASE64/036/1/
MANGADEX=https://mangadex.org/chapter/xxxxxxxx
MANGATARO=https://mangataro.org/manga/my-manga/chapter-36
```
