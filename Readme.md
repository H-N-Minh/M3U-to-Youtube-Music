# YouTube Music Playlist Manager & Sync Tool

This project is a suite of Python scripts designed to intelligently merge local `.m3u` playlist files and synchronize them to your YouTube Music account. It is built to handle huge lists, avoid duplicates (both locally and on YouTube Music), and protect your IP from rate-limit bans using human-like delays and exponential backoff.

## Features

- **Intelligent M3U Merging**: Combines old `.m3u` formats (with `#EXTINF` metadata) and new `.m3u` formats (raw file paths) into a single, clean list.
- **Duplicate Prevention**: Checks for duplicates locally before searching, and checks your actual YouTube Music playlists to prevent adding a song you already have.
- **Rate Limit Protection**: Implements Jitter (randomized delays) and Exponential Backoff to ensure YouTube doesn't block your IP for spamming search requests.
- **Safety Previews**: Provides a readable "First 10 / Last 10" preview of songs with their Artist and Title, requiring explicit user confirmation before modifying online playlists.
- **Query Caching**: Remembers searches locally so it never queries YouTube Music for the exact same text string twice, drastically speeding up the process.
- **Undo Utility**: Includes a script to easily remove the last N added songs if you make a mistake.

## Prerequisites

- Python 3.10+ installed on your system.
- Install the required `ytmusicapi` library:

```bash
pip install ytmusicapi
```

## Authentication (browser.json)

Because YouTube Music does not have an official playlist API, this tool acts as your web browser. You must authenticate it by creating a `browser.json` file.

1. Open your web browser and go to [music.youtube.com](https://music.youtube.com) (make sure you are logged in).
2. Open Developer Tools (Press `F12` or right-click > Inspect).
3. Go to the **Network** tab. Search for `browse` in the filter box.
4. Refresh the page. Click on the first `browse?` request that appears.
5. In the headers section, find **Request Headers**, right-click, and copy them.
6. Open your terminal in this project's folder and run:

```bash
ytmusicapi browser
```

7. Paste the headers when prompted and press Enter. This will generate the `browser.json` file in your directory. **Keep this file private!**

## How to Use (Workflow)

### Step 1: Merge and Resolve IDs (`process_m3u.py`)

This script reads your local `.m3u` files, merges them, removes duplicates, and searches YouTube Music to find the official `videoId` for every track.

1. Place your `.m3u` files into the `To Add Later` and `bro` folders.
2. Run the script:

```bash
python process_m3u.py
```

**Output**: The script will create two new folders:

- `To Add/`: Contains your beautifully merged and cleaned `.m3u` files.
- `To Add (video_id)/`: Contains `.txt` files with the raw YouTube Music video IDs required for Step 2.

### Step 2: Sync to YouTube Music (`add_songs.py`)

This script reads the IDs generated in Step 1 and safely pushes them to your actual YouTube Music account.

1. Ensure the playlists actually exist on your YouTube Music account (they must have the exact same name as your `.txt` files).
2. Run the script:

```bash
python add_songs.py
```

The script will:

- Fetch your current YTM playlist.
- Ask to clean up any duplicates currently sitting in your online playlist.
- Compare existing YTM songs against the new songs to skip duplicates.
- Show you a preview of the songs it is about to add.
- Wait for your typing `y` to confirm before making any online changes.

### Step 3: Undo Mistakes (`remove_songs.py`)

If you accidentally added the wrong batch of songs or want to clear out recent additions, use this script.

1. Open `remove_songs.py` in a text editor.
2. Edit the configuration variables at the top of the file:

```python
PLAYLIST_NAME = "(M1) House"   # Name of the playlist to target
NUMBER_SONGS_REMOVE = 194      # Number of recent songs to delete
```

3. Run the script:

```bash
python remove_songs.py
```

It will show a safety preview of what it is about to delete. Type `y` to confirm.

## Important Notes

- **Rate Limits**: The `process_m3u.py` script makes live searches on YouTube Music. If you process thousands of songs at once, YouTube may temporarily rate-limit your IP. The script is designed to pause (backoff) automatically. If it backs off for more than 5 minutes, it will safely kill the process to protect your IP.

- **API Reliability**: This relies on the unofficial `ytmusicapi`. If YouTube changes its website architecture, the API might temporarily break until the community updates the library.

- **Case Sensitivity**: Make sure your `.m3u` filenames match your actual YouTube Music playlist names exactly (including capitalization and spacing).
