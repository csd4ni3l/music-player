import musicbrainzngs as music_api
from iso3166 import countries
import urllib.request, json
from utils.constants import MUSICBRAINZ_PROJECT_NAME, MUSICBRAINZ_CONTACT, MUSCIBRAINZ_VERSION

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

def get_music_metadata(artist, title):
    music_api.set_useragent(MUSICBRAINZ_PROJECT_NAME, MUSCIBRAINZ_VERSION, MUSICBRAINZ_CONTACT)

    if artist:
        results = music_api.search_recordings(query=f"{artist} - {title}", limit=100)["recording-list"]
    else:
        results = music_api.search_recordings(query=title, limit=100)["recording-list"]

    finalized_blacklist = finalize_blacklist(title)

    for r in results:
        if not r.get("title") or not r.get("isrc-list"):
            continue

        if check_blacklist(r["title"].lower(), finalized_blacklist) or check_blacklist(r.get("disambiguation", "").lower(), finalized_blacklist):
            continue

        recording_id = r["id"]

        try:
            detailed = music_api.get_recording_by_id(
                recording_id,
                includes=["artists", "releases", "isrcs", "tags", "ratings"]
            )["recording"]
        except music_api.ResponseError:
            continue

        release = None
        for rel in detailed.get("release-list", []):
            release_title = rel.get("title", "").lower()

            if any(word in release_title for word in ["single", "ep", "maxi"]):
                continue

            if rel.get("status") == "Official" and is_release_valid(rel["id"]): # Only do it if the album is official, skipping many API calls
                release = rel

        metadata = {
            "musicbrainz_id": recording_id,
            "isrc": detailed["isrc-list"][0] if "isrc-list" in detailed else "Unknown",
            "musicbrainz_album_id": release.get("id") if release else "Unknown",
            "album_name": release.get("title") if release else "Unknown",
            "album_date": release.get("date") if release else "Unknown",
            "album_country": (get_country(release.get("country")) or "Worldwide") if release else "Unknown",
            "recording_length": int(detailed["length"]) if "length" in detailed else "Unknown",
            "musicbrainz_rating": detailed["rating"]["rating"] if "rating" in detailed else "Unknown",
            "tags": [tag["name"] for tag in detailed.get("tag-list", [])]
        }

        return metadata

    return None

def get_artist_metadata(artist):
    music_api.set_useragent(MUSICBRAINZ_PROJECT_NAME, MUSCIBRAINZ_VERSION, MUSICBRAINZ_CONTACT)

    result = music_api.search_artists(query=artist, limit=10)

    for r in result["artist-list"]:
        if not r["type"] == "Person":
            continue
            
        return {
            "musicbrainz_id": r["id"],
            "gender": r.get("gender", "Unknown"),
            "country": get_country(r.get("country")) or "Unknown",
            "ipi-list": r.get("ipi-list", "None"),
            "isni-list": r.get("isni-list", "None"),
            "born": r.get("life-span", {}).get("begin", "Unknown"),
            "dead": r.get("life-span", {}).get("ended").lower() == "true",
            "comment": r["disambiguation"]
        }

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
        
    return "Unknown"

def get_album_cover_art(musicbrainz_album_id):
    cover_art_bytes = music_api.get_image_front(musicbrainz_album_id)
    with open("music_cover_art.jpg", "wb") as file:
        file.write(cover_art_bytes)
    