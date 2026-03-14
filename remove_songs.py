# This is to removed n songs that was last added to the playlist
# This is useful when the sync_playlists.py added wrong songs to the playlist

from ytmusicapi import YTMusic

# PLAYLIST_NAME = "(M2) Hyper" # Replace with your actual playlist name
PLAYLIST_NAME = "(M1) Trap & Dubstep"

NUMBER_SONGS_REMOVE = 250 # Number of songs to remove

def findTracksOfPlaylist(yt):
    """Find the tracks to be removed of the target playlist and return them along with the playlist ID."""
    global PLAYLIST_NAME
    global NUMBER_SONGS_REMOVE

    # Get all your playlists
    playlists = yt.get_library_playlists()
    
    # Find the target playlist
    playlist_id = None
    for playlist in playlists:
        if playlist['title'] == PLAYLIST_NAME:
            playlist_id = playlist['playlistId']
            break
    if not playlist_id:
        print(f"Error: Playlist '{PLAYLIST_NAME}' not found.")
        return None, None

    # Get the playlist tracks
    playlist_data = yt.get_playlist(playlist_id)
    tracks = playlist_data.get('tracks', [])
    if not tracks:
        print("Playlist is empty.")
        return None, playlist_id

    # Identify the songs to remove (list is ordered by added time, newest first)
    if NUMBER_SONGS_REMOVE > len(tracks):
        NUMBER_SONGS_REMOVE = len(tracks)
    songs_to_remove = tracks[:NUMBER_SONGS_REMOVE]

    return songs_to_remove, playlist_id


def remove_last_n_songs():
    global NUMBER_SONGS_REMOVE
    global PLAYLIST_NAME
    
    # Load authentication
    yt = YTMusic('browser.json')
    
    # Get the tracks to be removed and the playlist ID
    songs_to_remove, playlist_id = findTracksOfPlaylist(yt)
    if songs_to_remove is None or playlist_id is None:
        print("Error occurred while fetching tracks to be removed.")
        return

    # 4. SAFETY CHECK: Print what will be deleted
    preview_count = 10
    print(f"--- PREVIEW: The first and last {min(preview_count, len(songs_to_remove))} of {NUMBER_SONGS_REMOVE} songs to be removed ---")
    for i, song in enumerate(songs_to_remove[:preview_count]):
        print(f"{i + 1}. {song.get('title')} - {song.get('artists')[0]['name']}")
    print("...")
    for i, song in enumerate(songs_to_remove[-preview_count:]):
        print(f"{len(songs_to_remove) - preview_count + i + 1}. {song.get('title')} - {song.get('artists')[0]['name']}")

    confirm = input("\nAre you sure you want to remove these? (y/n): ")
    
    if confirm.lower() == 'y':
        # Remove the items
        print(f"Removing {len(songs_to_remove)} songs from '{PLAYLIST_NAME}'...")
        yt.remove_playlist_items(playlist_id, songs_to_remove)
        print("Successfully removed.")
    else:
        print("Operation cancelled.")
    

# --- Configuration ---
if __name__ == "__main__":
    remove_last_n_songs()