import os
import sys
import time
import random
from ytmusicapi import YTMusic

### context:
# Folder New Playlists and Old Playlists contain .m3u files with the same names but different content/songs.
# We want to merge them, remove duplicates, before adding these songs to our YouTube Music playlists with another script.

### what this script does:
# 1. Reads .m3u files from "New Playlists" and "Old Playlists" directories.
# 2. Combines the entries from both files, ensuring no duplicates.
# 3. For each unique song entry, it searches YouTube Music to find the corresponding video ID.
# 4. Implements a robust search with random jitter and exponential backoff to handle rate limits.
# 5. Saves the cleaned playlist (in .m3u format) (with duplicates removed) to "To Add" directory
# 6. Saves the list of unique video IDs to "To Add (video_id)" directory for easy reference when later adding to YTM playlists with another script.

# --- CONFIGURATION ---
NEW_DIR = "New Playlists"   # Directory containing the .m3u files for 9 playlists with newer songs
OLD_DIR = "Old Playlists"   # Directory containing the .m3u files for 9 same playlists but with older songs
TO_ADD_DIR = "To Add"       # Output directory for cleaned and merged .m3u files (playlists of same name from 2 folders above are merged, duplicates removed)
VID_DIR = "To Add (video_id)"  # Output directory, contains the same songs of To Add folder, but in ID format, which is later used to add songs to YTM playlists with another script.)

# Create output directories if they don't exist
os.makedirs(TO_ADD_DIR, exist_ok=True)
os.makedirs(VID_DIR, exist_ok=True)

# --- HELPER FUNCTIONS ---

def parse_m3u(filepath):
    """
    Unified parser that handles the different formats of New Playlists and Old Playlists
            Old format example:
            #EXTINF:210,LZRD - Anything Anymore
            C:\Music\LZRD - Anything Anymore.mp3

            New format example:
            C:\Music\LZRD - Anything Anymore.mp3

            => new format just doesnt have metadata, like the artist name and song duration.
    This func reads an M3U file (a playlist), and extracts all songs of this playlist.
    Returns a list of dictionaries with 'query' (for YTM search) and 'raw' (original M3U text block).
            Example:
            [
                {
                    "query": "LZRD - Anything Anymore",
                    "raw": "#EXTINF:210,LZRD - Anything Anymore\nC:\Music\LZRD - Anything Anymore.mp3"
                },
                ...
            ]
    The query is used to later search for the song on Youtube Music
    The raw text is used to later save the cleaned M3U file in the "To Add" folder
    """
    entries =[]
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines =[line.strip() for line in f if line.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if line.upper() == "#EXTM3U":
            i += 1
            continue
            
        # If it's the OLD format containing #EXTINF
        if line.startswith("#EXTINF"):
            # Extract Artist - Title. E.g., "#EXTINF:210,LZRD - Anything Anymore" -> "LZRD - Anything Anymore"
            query = line.split(",", 1)[1].strip() if "," in line else line.replace("#EXTINF:", "").strip()
            
            # Check if the next line is the file path
            if i + 1 < len(lines) and not lines[i+1].startswith("#"):
                path = lines[i+1]
                entries.append({"query": query, "raw": f"{line}\n{path}"})
                i += 2
            else:
                entries.append({"query": query, "raw": line})
                i += 1
                
        # If it's the NEW format (just a file path)
        else:
            filename = os.path.basename(line)
            # Remove the .mp3 extension for a clean YouTube Music search query
            query = os.path.splitext(filename)[0].strip()
            entries.append({"query": query, "raw": line})
            i += 1
            
    return entries

def search_ytm_with_backoff(yt, query):
    """
    Search on YouTube Music with the given query, to find the corresponding video ID for the song.
    Since Youtube bans IPs that make too many requests in a short time, we implement a robust search with random jitter and exponential backoff:
        Each Search is delayed between 0.5 and 1.5 seconds (random jitter) to mimic human behavior and avoid hitting rate limits.
        If we still hit a rate limit, we wait a bit (backoff) before retrying the same query, until we get the video ID
        The backoff time doubles with each retry (2s, 4s, 8s, etc.) to give YouTube more time to reset the rate limit.
        If the backoff time exceeds 5 minutes, we assume something is wrong (e.g., the session is invalid, or the IP is temporarily banned) 
           and we stop the entire program immediately to protect the user from further issues.
    Returns the video ID if any result (song/video) is found, or None if no results are found for the query.
    """
    base_sleep = 2 
    attempt = 0
    
    while True:
        try:
            # Jitter: Random sleep between 0.5 and 1.5 seconds
            time.sleep(random.uniform(0.5, 1.5))
            
            # Perform search (filtered by songs for best accuracy)
            results = yt.search(query, filter="songs")
            if results and 'videoId' in results[0]:
                return results[0]['videoId']
            
            # Fallback: if no "songs" found, try general search
            results_any = yt.search(query)
            if results_any and 'videoId' in results_any[0]:
                return results_any[0]['videoId']
                
            return None # No video found
            
        except Exception as e:
            # Calculate exponential backoff: 2, 4, 8, 16, 32...
            sleep_time = base_sleep * (2 ** attempt)
            
            if sleep_time > 300: # 5 minutes = 300 seconds
                print(f"\n[FATAL ERROR] Rate limit backoff exceeded 5 minutes ({sleep_time}s).")
                print("Stopping the program immediately to protect your IP from being banned.")
                sys.exit(1) # Terminates the python script completely
                
            print(f"  [!] Error searching '{query}': {e}.")
            print(f"  [!] Retrying in {sleep_time} seconds (Attempt {attempt + 1})...")
            time.sleep(sleep_time)
            attempt += 1

def getPlaylistNamesFromM3U(filepath):
    """
    Return a list of all playlists we working with. (list of strings)
    """
    playlists =[f for f in os.listdir(NEW_DIR) if f.lower().endswith('.m3u')]
    
    if not playlists:
        print(f"No .m3u files found in '{NEW_DIR}'. Please check your folders.")
        return None

    return playlists

def getAllSongsFromSamePlaylist(playlist):
    """Since both folders have the same playlist names, we can parse both files with the same name and combine their entries.
    Return is a list of all songs (with duplicates) that belongs to this playlist"""
    new_path = os.path.join(NEW_DIR, playlist)
    old_path = os.path.join(OLD_DIR, playlist)

    # make sure these files exist, if it does, get all songs of this playlist from that folder.
    if not os.path.exists(new_path):
        print(f"Warning: '{playlist}' not found in '{NEW_DIR}'. Skipping this playlist.")
        entries_new = []
    else:
        entries_new = parse_m3u(new_path)

    if not os.path.exists(old_path):
        print(f"Warning: '{playlist}' not found in '{OLD_DIR}'. Skipping this playlist.")
        entries_old = []
    else:  
         entries_old = parse_m3u(old_path)

    # Merge into 1 big entries list
    all_entries = entries_old + entries_new
    print(f"  Found {len(all_entries)} total lines/songs to evaluate.")
    return all_entries

def getVideoIdForSong(yt, all_entries, query_cache, unique_songs):
    """ search each song of this playlist on YTM. Each song get its own VideoID. All unique ID is stored in unique_songs."""
    
    for i, entry in enumerate(all_entries):
        query = entry['query']
        print(f"  ({i+1}/{len(all_entries)}) Searching: {query}...", end=" ", flush=True)
        
        # Check local memory cache first (saves API calls!)
        if query in query_cache:
            video_id = query_cache[query]
        else:
            video_id = search_ytm_with_backoff(yt, query)
            if not video_id:
                print("[Not Found on YTM] with query: " + query)
                not_found_count += 1
            else:
                query_cache[query] = video_id # Save to cache, to prevent future queries for same song

                # Save the ID if it is a new song for this playlist
                if video_id not in unique_songs:
                    unique_songs[video_id] = entry['raw']
                
def saveResults(playlist, unique_songs):
    """ Save the merged and cleaned playlist in M3U format. 
    Also save the list of unique VideoID of this playlist in a text file, for later we can add all these songs to 
    YTM using another script."""
    # 1. Save Cleaned M3U
    clean_m3u_path = os.path.join(TO_ADD_DIR, playlist)
    with open(clean_m3u_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for raw_text in unique_songs.values():
            f.write(raw_text + "\n")
            
    # 2. Save Video IDs to a text file
    vid_playlist = os.path.splitext(playlist)[0] + ".txt"
    vid_path = os.path.join(VID_DIR, vid_playlist)
    with open(vid_path, 'w', encoding='utf-8') as f:
        for vid in unique_songs.keys():
            f.write(vid + "\n")


# --- MAIN LOGIC ---

def main():
    yt = YTMusic('browser.json')
    
    # Get all playlist names
    playlists = getPlaylistNamesFromM3U(NEW_DIR)
    if not playlists:
        return

    # Go through each playlist
    query_cache = {}    # Dictionary to cache exact text queries so we don't query YTM twice for the same song. {"Artist - Title": "videoId"}
    not_found_count = 0 # Counter to track how many songs we couldn't find on YTM
    for playlist in playlists:
        print(f"\n--- Processing Playlist: {playlist} ---")
        
        # Get all songs from both folders for this playlist
        all_entries = getAllSongsFromSamePlaylist(playlist)
        if len(all_entries) == 0:
            print(f"  No songs found for '{playlist}' in either folder. Skipping.")
            continue

        # Search each of these songs to get their ID
        unique_songs = {} # contains all unique songs for this playlist {videoId: "Artist - Title"}
        getVideoIdForSong(yt, all_entries, query_cache, unique_songs)
                
        # Save the merged and cleaned playlist in M3U format. Also save the list of unique VideoID of this playlist in a text file.
        saveResults(playlist, unique_songs)
                
        # Print Confirmation
        print(f"\n✅ Finished merging & cleaning '{playlist}'!")
        print(f"   -> Songs not found on YTM: {not_found_count}")

if __name__ == "__main__":
    main()