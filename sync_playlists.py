import os
import time
from ytmusicapi import YTMusic

# ==========================================
# CONFIGURATION

PLAYLIST_MAPPING = {    # Key: M3U filename, Value: YouTube Music playlist name
    "1. ELECTRO.m3u": "(M2) Hyper",
    "2. EDM & HOUSES.m3u": "(M1) House",
    "2.1 Progressive & Techno.m3u": "(M1) Progressive & Techno",
    "3. TRAP & DUBSTEP.m3u": "(M1) Trap & Dubstep",
    "4. CHILLAX.m3u": "(M1) Chillax",
    "4.1 Instrumental.m3u": "(M2) Instrumental",
    "5. RAP.m3u": "(M1) Rap",
    "6. POPPING.m3u": "(M1) Pop",
    "7. MIX.m3u": "(M0) Mixed",
    "8. Vietnam.m3u": "(M1) Vietnam",
    "9. Oldies.m3u": "(M2) Goldies",
    "FAVORITE SONGS.m3u": "(M0) FAVORITES",
    
    "favorite songs2.m3u": "(M0) FAVORITES",
    "Random Favorites.m3u": "(M0) FAVORITES",
    "searched songs.m3u": "(M0) Nostalgia",
}
# ==========================================

def parse_m3u(file_path):
    """Extracts song names from an M3U file."""
    tracks = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('#EXTINF:'):
            parts = line.split(',', 1)
            if len(parts) > 1:
                tracks.append(parts[1].strip())
        elif line and not line.startswith('#'):
            if i > 0 and lines[i-1].strip().startswith('#EXTINF:'):
                continue
            filename = os.path.basename(line)
            name, _ = os.path.splitext(filename)
            tracks.append(name.strip())
    return tracks

def get_playlist_id_by_name(ytmusic, name):
    playlists = ytmusic.get_library_playlists(limit=100)
    for pl in playlists:
        if pl['title'].lower() == name.lower():
            return pl['playlistId']
    return None

def main():
    print("Authenticating with YouTube Music...")
    try:
        ytmusic = YTMusic('browser.json')
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # Create unadded folder
    os.makedirs("unadded", exist_ok=True)

    for m3u_file, ytm_playlist_name in PLAYLIST_MAPPING.items():
        print(f"\n--- Processing '{m3u_file}' -> '{ytm_playlist_name}' ---")
        
        # Validation
        if not os.path.exists(m3u_file):
            print(f"Error: M3U file '{m3u_file}' not found.")
            continue
            
        playlist_id = get_playlist_id_by_name(ytmusic, ytm_playlist_name)
        if not playlist_id:
            print(f"Error: Could not find YouTube playlist '{ytm_playlist_name}'.")
            continue

        # Setup
        tracks_to_search = parse_m3u(m3u_file)
        playlist_details = ytmusic.get_playlist(playlist_id, limit=None)
        
        existing_video_ids = set()
        existing_signatures = set()
        for track in playlist_details.get('tracks', []):
            if track.get('videoId'):
                existing_video_ids.add(track['videoId'])
            title = track.get('title', '').lower()
            artists = " ".join([a['name'] for a in track.get('artists', [])]).lower()
            existing_signatures.add(f"{title} - {artists}")

        video_ids_to_add = []
        unadded_tracks = []
        added_count = 0
        skipped_count = 0
        existed_count = 0

######################
        # Processing
        for track_name in tracks_to_search:
            search_results = ytmusic.search(track_name, filter='songs')
            
            if not search_results:
                print(f" - Not found: {track_name}")
                unadded_tracks.append(track_name)
                skipped_count += 1
                continue
#############
            best_match = search_results[0]
            video_id = best_match.get('videoId')
            match_title = best_match.get('title', '').lower()
            match_artists = " ".join([a['name'] for a in best_match.get('artists', [])]).lower()
            match_signature = f"{match_title} - {match_artists}"
            
            if video_id in existing_video_ids or match_signature in existing_signatures:
                existed_count += 1
            else:
                video_ids_to_add.append(video_id)
                existing_video_ids.add(video_id)
                existing_signatures.add(match_signature)
                added_count += 1
            
            time.sleep(0.5) # Slight delay to be polite to the API

        # Batch Add
        if video_ids_to_add:
            ytmusic.add_playlist_items(playlist_id, video_ids_to_add)

        # Reporting
        print(f"Summary for '{ytm_playlist_name}':")
        print(f" - Songs total in m3u: {len(tracks_to_search)}")
        print(f" - Songs added: {added_count}")
        print(f" - Songs not found: {skipped_count}")
        print(f" - Songs already existed: {existed_count}")

        # Save unadded list
        if unadded_tracks:
            unadded_file = os.path.join("unadded", f"{ytm_playlist_name}_unadded.m3u")
            with open(unadded_file, 'w', encoding='utf-8') as f:
                for t in unadded_tracks:
                    f.write(f"{t}\n")
            print(f" - Unadded tracks saved to: {unadded_file}")

if __name__ == "__main__":
    main()