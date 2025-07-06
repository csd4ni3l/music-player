import musicbrainzngs as music_api
from iso3166 import countries

from utils.constants import MUSICBRAINZ_PROJECT_NAME, MUSICBRAINZ_CONTACT, MUSCIBRAINZ_VERSION

import urllib.request, json, os, arcade

WORD_BLACKLIST = ["compilation", "remix", "vs", "cover"]
LRCLIB_BASE_URL = "https://lrclib.net/api/search"

def check_blacklist(text, blacklist):
    return any(word in text for word in blacklist)

def finalize_blacklist(title):
    blacklist = WORD_BLACKLIST[:]

    for word in WORD_BLACKLIST:
        if word in title:
            blacklist.remove(word)

    return blacklist

def is_release_valid(release_id):
    try:
        release_data = music_api.get_release_by_id(release_id, includes=["release-groups"])
        rg = release_data.get("release", {}).get("release-group", {})
        if rg.get("primary-type", "").lower() == "album":
            return True
    except music_api.ResponseError:
        pass
    return False

def get_country(country_code):
    try:
        country = countries.get(country_code)
    except KeyError:
        country = None

    return country.name if country else None

def get_artists_metadata(artist_ids):
    with open("metadata_cache.json", "r") as file:
        metadata_cache = json.load(file)

    artist_metadata = {}

    for artist_id in artist_ids:
        if artist_id in metadata_cache["artist_by_id"]:
            data = metadata_cache["artist_by_id"][artist_id]
            name = data["name"]
            artist_metadata[name] = data
        else:
            artist_data = music_api.get_artist_by_id(artist_id)["artist"]

            artist_metadata[artist_data["name"]] = {
                "name": artist_data["name"],
                "musicbrainz_id": artist_id,
                "gender": artist_data.get("gender", "Unknown"),
                "country": get_country(artist_data.get("country", "WZ")) or "Unknown",
                "tag-list": [tag["name"] for tag in artist_data.get("tag_list", [])],
                "ipi-list": artist_data.get("ipi-list", []),
                "isni-list": artist_data.get("isni-list", []),
                "born": artist_data.get("life-span", {}).get("begin", "Unknown"),
                "dead": artist_data.get("life-span", {}).get("ended", "Unknown").lower() == "true",
                "comment": artist_data.get("disambiguation", "None")
            }

            metadata_cache["artist_by_id"][artist_id] = artist_metadata[artist_data["name"]]
    
    with open("metadata_cache.json", "w") as file:
        file.write(json.dumps(metadata_cache))

    return artist_metadata

def get_albums_metadata(release_list):
    with open("metadata_cache.json", "r") as file:
        metadata_cache = json.load(file)

    album_metadata = {}

    for release in release_list:
        release_title = release.get("title", "").lower()

        if any(word in release_title for word in ["single", "ep", "maxi"]):
            continue

        if release.get("status") == "Official":
            release_id = release["id"]
            if release_id in metadata_cache["is_release_album_by_id"]:
                if not metadata_cache["is_release_album_by_id"][release_id]:
                    continue
            else:
                if not is_release_valid(release_id):
                    metadata_cache["is_release_album_by_id"][release_id] = False
                    continue
            
            metadata_cache["is_release_album_by_id"][release_id] = True
            
            album_metadata[release.get("title", "")] = {
                "musicbrainz_id": release.get("id") if release else "Unknown",
                "album_name": release.get("title") if release else "Unknown",
                "album_date": release.get("date") if release else "Unknown",
                "album_country": (get_country(release.get("country", "WZ")) or "Worldwide") if release else "Unknown",
            }

    with open("metadata_cache.json", "w") as file:
        file.write(json.dumps(metadata_cache))

    return album_metadata

def get_music_metadata(artist, title):
    if os.path.exists("metadata_cache.json") and os.path.isfile("metadata_cache.json"):
        with open("metadata_cache.json", "r") as file:
            metadata_cache = json.load(file)
    else:
        metadata_cache = {
            "query_results": {},
            "recording_by_id": {},
            "artist_by_id": {},
            "is_release_album_by_id": {},
            "lyrics_by_id": {}
        }

    music_api.set_useragent(MUSICBRAINZ_PROJECT_NAME, MUSCIBRAINZ_VERSION, MUSICBRAINZ_CONTACT)

    if artist:
        query = f"{artist} - {title}"
    else:
        query = title

    if query in metadata_cache["query_results"]:
        recording_id = metadata_cache["query_results"][query]
    else:
        results = music_api.search_recordings(query=title, limit=100)["recording-list"]

        finalized_blacklist = finalize_blacklist(title)

        for r in results:
            if not r.get("title") or not r.get("isrc-list"):
                continue

            if check_blacklist(r["title"].lower(), finalized_blacklist) or check_blacklist(r.get("disambiguation", "").lower(), finalized_blacklist):
                continue

            recording_id = r["id"]
            break

        metadata_cache["query_results"][query] = recording_id

    if recording_id in metadata_cache["recording_by_id"]:
        detailed = metadata_cache["recording_by_id"][recording_id]
    else:
        detailed = music_api.get_recording_by_id(
            recording_id,
            includes=["artists", "releases", "isrcs", "tags", "ratings"]
        )["recording"]
        metadata_cache["recording_by_id"][recording_id] = {
            "artist-credit": [{"artist": {"id": artist_data["artist"]["id"]}} for artist_data in detailed.get("artist-credit", {}) if isinstance(artist_data, dict)],
            "isrc-list":  detailed["isrc-list"] if "isrc-list" in detailed else [],
            "rating": {"rating": detailed["rating"]["rating"]} if "rating" in detailed else {},
            "tags": detailed.get("tag-list", []),
            "release-list": [{"id": release["id"], "title": release["title"], "status": release.get("status"), "date": release.get("date"), "country": release.get("country", "WZ")} for release in detailed["release-list"]] if "release-list" in detailed else []
        }

    metadata_cache["lyrics_by_id"] = metadata_cache.get("lyrics_by_id", {})

    if recording_id in metadata_cache["lyrics_by_id"]:
        lyrics = metadata_cache["lyrics_by_id"][recording_id]
    else:
        lyrics = get_lyrics(artist, title)
        metadata_cache["lyrics_by_id"][recording_id] = lyrics

    with open("metadata_cache.json", "w") as file:
        file.write(json.dumps(metadata_cache))

    artist_ids = [artist_data["artist"]["id"] for artist_data in detailed.get("artist-credit", {}) if isinstance(artist_data, dict)] # isinstance is needed, because sometimes & is included as an artist str
    artist_metadata = get_artists_metadata(artist_ids)
    album_metadata = get_albums_metadata(detailed.get("release-list", []))

    music_metadata = {
        "musicbrainz_id": recording_id,
        "isrc-list": detailed["isrc-list"] if "isrc-list" in detailed else [],
        "musicbrainz_rating": detailed["rating"]["rating"] if "rating" in detailed.get("rating", {}) else "Unknown",
        "tags": [tag["name"] for tag in detailed.get("tag-list", [])]
    }

    return music_metadata, artist_metadata, album_metadata, lyrics

def get_lyrics(artist, title):
    if artist:
        query = f"{artist} - {title}"
    else:
        query = title
    
    query_string = urllib.parse.urlencode({"q": query})
    full_url = f"{LRCLIB_BASE_URL}?{query_string}"

    with urllib.request.urlopen(full_url) as request:
        data = json.loads(request.read().decode("utf-8"))
    
    for result in data:
        if result.get("plainLyrics"):
            return result["plainLyrics"]
        
    if artist: # if there was an artist, it might have been misleading. For example, on Youtube, the uploader might not be the artist. We retry with only title.
        return get_lyrics(None, title)

def get_album_cover_art(musicbrainz_album_id):
    try:
        cover_art_bytes = music_api.get_image_front(musicbrainz_album_id, 250)
    except music_api.ResponseError:
        return None

    with open("music_cover_art.jpg", "wb") as file:
        file.write(cover_art_bytes)
    
    texture = arcade.load_texture("music_cover_art.jpg")

    os.remove("music_cover_art.jpg")

    return texture