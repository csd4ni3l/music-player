import urllib.parse, urllib.request, json

from utils.utils import ensure_metadata_file
from utils.constants import LRCLIB_BASE_URL

def convert_syncronized_time_to_seconds(synchronized_time):
    minutes_str, seconds_str = synchronized_time.split(":")
    return float(minutes_str) * 60 + float(seconds_str)

def parse_synchronized_lyrics(synchronized_lyrics: str):
    lyrics_list = {}
    
    for lyrics_line in synchronized_lyrics.splitlines():
        uncleaned_date, text = lyrics_line.split("] ")
        cleaned_date = uncleaned_date.replace("[", "")

        lyrics_list[convert_syncronized_time_to_seconds(cleaned_date)] = text

    return list(lyrics_list.keys()), lyrics_list

def get_closest_time(current_time, lyrics_times):
    closest_time = 0

    for lyrics_time in lyrics_times:
        if lyrics_time <= current_time and lyrics_time > closest_time:
            closest_time = lyrics_time

    return closest_time

def get_lyrics(artist, title):
    metadata_cache = ensure_metadata_file()

    if (artist, title) in metadata_cache["lyrics_by_artist_title"]:
        return metadata_cache["lyrics_by_artist_title"][(artist, title)]
    else:
        if artist:
            query = f"{artist} - {title}"
        else:
            query = title
    
        query_string = urllib.parse.urlencode({"q": query})
        full_url = f"{LRCLIB_BASE_URL}?{query_string}"

        with urllib.request.urlopen(full_url) as request:
            data = json.loads(request.read().decode("utf-8"))
    
        for result in data:
            if result.get("plainLyrics") and result.get("syncedLyrics"):
                metadata_cache["lyrics_by_artist_title"][(artist, title)] = (result["plainLyrics"], result["syncedLyrics"])
                return (result["plainLyrics"], result["syncedLyrics"])
        
    with open("metadata_cache.json", "w") as file:
        file.write(json.dumps(metadata_cache))

    if artist: # if there was an artist, it might have been misleading. For example, on Youtube, the uploader might not be the artist. We retry with only title.
        return get_lyrics(None, title)
    
    return [None, None]
