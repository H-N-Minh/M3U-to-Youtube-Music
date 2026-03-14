import os
import sys
from ytmusicapi import YTMusic
import time
import random

# --- CONFIGURATION ---
VID_DIR = "To Add (video_id)"

# --- HELPER FUNCTIONS ---
def getTxtFiles(directory):
    """
    Scans the specified directory and returns a list of all .txt files.
    """
    # Check if the folder exists
    if not os.path.exists(VID_DIR):
        print(f"Directory '{VID_DIR}' not found. Please run the process_m3u.py script first.")
        return None

    # Get all text files in the directory
    txt_files = [f for f in os.listdir(VID_DIR) if f.lower().endswith('.txt')]
    if not txt_files:
        print(f"No text files found in '{VID_DIR}'.")
        return None
    print(f"Found {len(txt_files)} playlist(s) in '{VID_DIR}'")
    return txt_files

def removeDuplicates(tracks, yt, playlist_id):
    # Identify and remove duplications within the existing playlist
    seen_vids = set()
    duplicates_to_remove =[]
    duplicate_titles = [] # To show the user friendly names

    for track in tracks:
        vid = track.get('videoId')
        set_vid = track.get('setVideoId')
        title = track.get('title', 'Unknown Title')

        if not vid:
            print(f"⚠️  Warning: Found a track without a videoId. Skipping this track.")
            continue  # Skip invalid or local-only tracks

        if vid in seen_vids:
            # It's a duplicate currently sitting in the YTM playlist
            if set_vid: # setVideoId is required by YTM API to remove specific playlist items
                duplicates_to_remove.append({'videoId': vid, 'setVideoId': set_vid})
                duplicate_titles.append(title)
        else:
            seen_vids.add(vid)

    if duplicates_to_remove:
        print(f"\n--- Found {len(duplicates_to_remove)} duplicate(s) ---")
        for i, name in enumerate(duplicate_titles, 1):
            print(f"{i}. {name}")
        
        # Confirmation Prompt
        choice = input("\nDo you want to remove these duplicates from the playlist? (y/n): ").lower().strip()
        
        if choice == 'y':
            print("Removing duplicates...")
            yt.remove_playlist_items(playlist_id, duplicates_to_remove)
            print("Done!")
        else:
            print("Skipped removal. Duplicates were left in the playlist.")
    else:
        print("No existing duplicates found in the current playlist.")

    return seen_vids

def setUp():
    # Authenticate with YouTube Music using the browser.json file
    print("Setting up...")
    try:
        yt = YTMusic('browser.json')
    except Exception as e:
        print(f"Error authenticating: {e}")
        print("Make sure 'browser.json' exists in this directory.")
        return None, None, None

    # Get all text files in the "To Add (video_id)" directory
    txt_files = getTxtFiles(VID_DIR)
    if txt_files is None:
        print(f"No text files found in '{VID_DIR}'. Exiting the program.")
        return None, None, None

    # Fetch all library playlists to map their names to their IDs
    library_playlists = yt.get_library_playlists(limit=None)
    playlist_map = {p['title']: p['playlistId'] for p in library_playlists}

    return yt, txt_files, playlist_map

def fetchUniqueExistingVids(yt, playlist_id, playlist_name):
    # Fetch all existing tracks in the playlist and remove any duplicates
    playlist_data = yt.get_playlist(playlist_id, limit=None)
    tracks = playlist_data.get('tracks',[])
    print(f"Found {len(tracks)} song(s) in the playlist '{playlist_name}'.")
    return removeDuplicates(tracks, yt, playlist_id)

def getUniqueVidsToAdd(filename, unique_existing_vids):
    """Read the video IDs from the text file and filter out any that are already in the playlist"""
    # Read the new video IDs we want to add
    filepath = os.path.join(VID_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        new_vids = [line.strip() for line in f if line.strip()]

    # Filter out songs that are already exist in the YT playlist
    unique_vids_to_add =set() # Use a set to automatically handle duplicates in the text file itself
    
    for vid in new_vids:
        if vid not in unique_existing_vids and vid not in unique_vids_to_add:
            unique_vids_to_add.add(vid)

    return unique_vids_to_add

def searchSongNameWithBackoff(yt, vid):
    """Search for the song name using the video ID, with exponential backoff in case of rate limits."""
    backoff_time = 2  # Start with a 2 second backoff
    attempt = 0

    while True:
        try:
            # Jitter: Random sleep between 0.5 and 1.5 seconds
            time.sleep(random.uniform(0.5, 1.5))

            # Fetch song data
            song_data = yt.get_song(vid)
            title = song_data.get('videoDetails', {}).get('title', 'Unknown Title')
            author = song_data.get('videoDetails', {}).get('author', 'Unknown Artist')
            return f"{title} - {author}"
        except Exception as e:
            sleep_time = backoff_time * (2 ** attempt)
            if sleep_time > 300: # 5 minutes = 300 seconds
                print(f"\n[FATAL ERROR] Rate limit backoff exceeded 5 minutes ({sleep_time}s).")
                print("Stopping the program immediately to protect your IP from being banned.")
                sys.exit(1) # Terminates the python script completely

            print(f"Error, retrying in {sleep_time} seconds (Attempt {attempt + 1})...")
            time.sleep(sleep_time)
            attempt += 1


def printStatsAndPreview(playlist_name, unique_existing_vids, unique_vids_to_add, yt):
    """Print stats about the playlist and a preview of the songs to be added"""
    # print stats about the playlist and the new songs to be added
    print(f"\n📊 --- STATS FOR '{playlist_name}' ---")
    print(f"Current unique songs in playlist: {len(unique_existing_vids)}")
    print(f"New unique songs to be added:   {len(unique_vids_to_add)}")
    print("-" * 35)

    if len(unique_vids_to_add) == 0:
        print(f"Playlist already has all these songs. Nothing new to add.")
        return
    
    # Preview the first and last 10 songs of the new additions
    preview_vids =[]
    if len(unique_vids_to_add) <= 20:
        preview_vids = list(unique_vids_to_add)
    else:
        # Grab first 10, put a placeholder string, then grab last 10
        preview_vids = list(unique_vids_to_add)[:10] +["..."] + list(unique_vids_to_add)[-10:]

    print("\nPreview of some of songs to be added:")
    for i, vid in enumerate(preview_vids):
        if vid == "...":
            print("   ... [skipping middle tracks] ...")
            continue
        
        # Calculate the display number (e.g. 1-10, then jump to 90-100)
        if len(unique_vids_to_add) <= 20 or i < 10:
            display_num = i + 1
        else:
            display_num = len(unique_vids_to_add) + 1 - len(preview_vids) + i

        song_name = searchSongNameWithBackoff(yt, vid)
        print(f"   {display_num}. {song_name}")


# --- MAIN FUNCTION ---

def main():
    # Step 1: Set up and authenticate, get text files, and fetch playlist ids
    yt, txt_files, playlist_map = setUp()

    # Loop through each text file
    for filename in txt_files:
        playlist_name = os.path.splitext(filename)[0]
        print(f"\n" + "="*50)
        print(f"PROCESSING PLAYLIST: {playlist_name}")
        print("="*50)

        # Skip if playlist name not found in user's library
        if playlist_name not in playlist_map:
            print(f"❌ Playlist '{playlist_name}' not found on your YouTube Music account.")
            print("Skipping to the next playlist...")
            continue

        # Get the playlist ID, all the unique existing songs and all the unique songs to add
        print(f"Fetching existing songs for playlist '{playlist_name}'...")
        playlist_id = playlist_map[playlist_name]
        unique_existing_vids = fetchUniqueExistingVids(yt, playlist_id, playlist_name)
        unique_vids_to_add = getUniqueVidsToAdd(filename, unique_existing_vids)
        
        # Print stats about the playlist and the new songs to be added
        printStatsAndPreview(playlist_name, unique_existing_vids, unique_vids_to_add, yt)
       
        # 7. Ask for confirmation
        print("\n⚠️  ACTION REQUIRED")
        ans = input(f"Do you want to add these {len(unique_vids_to_add)} songs to '{playlist_name}'?(y/n)")

        if ans.strip().lower() == 'y':
            yt.add_playlist_items(playlist_id, list(unique_vids_to_add))
            print("✅ Successfully added all new songs!")
        else:
            print("\n🛑 Operation aborted by user. Stopping the entire program.")
            sys.exit(0) # Immediately shuts down the python script

    print("\nAll playlists have been evaluated and processed successfully!")

if __name__ == "__main__":
    main()
