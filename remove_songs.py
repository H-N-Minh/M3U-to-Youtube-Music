# This is to removed n songs that was last added to the playlist
# This is useful when the sync_playlists.py added wrong songs to the playlist

from ytmusicapi import YTMusic

# First Row
# PLAYLIST_NAME = "(M2) Hyper"
# PLAYLIST_NAME = "(M1) Trap & Dubstep"
# PLAYLIST_NAME = "(M1) Pop"
# PLAYLIST_NAME = "(M0) FAVORITES"

# Second Row
# PLAYLIST_NAME = "(M1) Chillax"
PLAYLIST_NAME = "(M1) House"
# PLAYLIST_NAME = "(M1) Vietnam"

NUMBER_SONGS_REMOVE = 194 # Number of songs to remove


def findPlaylistIdByName(yt):
    """Find the playlist ID by its name."""
    playlists = yt.get_library_playlists(limit=100)
    for playlist in playlists:
        if playlist['title'] == PLAYLIST_NAME:
            print(f"Found playlist '{PLAYLIST_NAME}'")
            return playlist['playlistId']
    print(f"Error: Playlist '{PLAYLIST_NAME}' not found.")
    return None

def findTracksOfPlaylist(yt, playlist_id):
    """Get the tracks of the playlist by its ID."""
    playlist_data = yt.get_playlist(playlist_id, limit=None)
    tracks = playlist_data.get('tracks', [])
    if not tracks:
        print("Playlist is empty.")
        return None
    print(f"Found {len(tracks)} tracks in the playlist.")
    return tracks

def getTracksToRemove(tracks):
    """Identify the songs to remove (list is ordered by added time, newest first)."""
    global NUMBER_SONGS_REMOVE
    if NUMBER_SONGS_REMOVE > len(tracks):
        print(f"Warning: NUMBER_SONGS_REMOVE ({NUMBER_SONGS_REMOVE}) is greater than the total number of tracks ({len(tracks)}). Adjusting to remove all tracks.")
        NUMBER_SONGS_REMOVE = len(tracks)
    songs_to_remove = tracks[:NUMBER_SONGS_REMOVE]
    songs_not_removed = tracks[NUMBER_SONGS_REMOVE: NUMBER_SONGS_REMOVE + 10]  # For previewing the next songs that won't be removed

    if not songs_to_remove or not songs_not_removed:
        print("Error: Could not identify songs to remove or songs that will not be removed.")
        return None, None
    
    print(f"Identified {len(songs_to_remove)} songs to remove and {len(songs_not_removed)} following songs that will not be removed.")
    return songs_to_remove, songs_not_removed

def saftyCheck(songs_to_remove, songs_not_removed, total_tracks):
    """Perform a safety check by previewing the songs to be removed and not removed."""
    preview_count = min(10, len(songs_to_remove))

    # Preview the songs to be removed
    print(f"--- PREVIEW: The first and last {preview_count} of {len(songs_to_remove)} songs to be removed ---")
    for i, song in enumerate(songs_to_remove[:preview_count]):
        print(f"{i + 1}. {song.get('title')} - {song.get('artists')[0]['name']}")
    print("...")
    for i, song in enumerate(songs_to_remove[-preview_count:]):
        print(f"{len(songs_to_remove) - preview_count + i + 1}. {song.get('title')} - {song.get('artists')[0]['name']}")

    # Preview the songs that will not be removed
    preview_count = min(10, len(songs_not_removed))
    print(f"\n--- PREVIEW: The next {preview_count} songs that will NOT be removed ---")
    for i, song in enumerate(songs_not_removed[:preview_count]):
        print(f"{i + 1 + len(songs_to_remove)}. {song.get('title')} - {song.get('artists')[0]['name']}")
    
    print(f"\nTotal {total_tracks} tracks in playlist, {len(songs_to_remove)} will be removed, {total_tracks - len(songs_to_remove)} will remain.")
    confirmation = input("\nDo you want to proceed with removing these songs? (y/n): ")
    return confirmation.lower() == 'y'

def remove_last_n_songs():
    global NUMBER_SONGS_REMOVE
    global PLAYLIST_NAME
    
    # Load authentication
    yt = YTMusic('browser.json')

    # 1. Get the playlist ID
    playlist_id = findPlaylistIdByName(yt)
    if playlist_id is None:
        return
    
    # 2. Get the tracks of the playlist
    tracks = findTracksOfPlaylist(yt, playlist_id)
    if tracks is None:
        return

    # 3. Identify the songs to remove
    songs_to_remove, songs_not_removed = getTracksToRemove(tracks)
    if songs_to_remove is None or songs_not_removed is None:
        return
    
    # 4. Safety check with preview
    if not saftyCheck(songs_to_remove, songs_not_removed, len(tracks)):
        print("Operation cancelled by the user.")
        return
    
    # 5. Remove the identified songs
    print(f"Removing {len(songs_to_remove)} songs from '{PLAYLIST_NAME}'...")
    yt.remove_playlist_items(playlist_id, songs_to_remove)
    print("Successfully removed.")    
    
    

# --- Configuration ---
if __name__ == "__main__":
    remove_last_n_songs()