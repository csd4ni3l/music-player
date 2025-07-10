import musicbrainzngs as music_api

from utils.constants import MUSICBRAINZ_PROJECT_NAME, MUSICBRAINZ_CONTACT, MUSCIBRAINZ_VERSION, MUSIC_TITLE_WORD_BLACKLIST
from utils.lyrics_metadata import get_lyrics
from utils.utils import ensure_metadata_file

import json, iso3166

def get_country(code):
    country = iso3166.countries.get(code, None)
    return country.name if country else "Worldwide"

def check_blacklist(text, blacklist):
    return any(word in text for word in blacklist)

def finalize_blacklist(title):
    blacklist = MUSIC_TITLE_WORD_BLACKLIST[:]

    for word in MUSIC_TITLE_WORD_BLACKLIST:
        if word in title:
            blacklist.remove(word)

    return blacklist

def is_release_valid(release):
    return release.get("release-event-count", 0) == 0 # only include albums

def get_artists_metadata(artist_ids):
    metadata_cache = ensure_metadata_file()

    artist_metadata = {}

    for artist_id in artist_ids:
        if artist_id in metadata_cache["artist_by_id"]:
            data = metadata_cache["artist_by_id"][artist_id]
            name = data["name"]
            artist_metadata[name] = data
        else:
            artist_data = music_api.get_artist_by_id(artist_id, includes=["annotation", "releases", "url-rels"])["artist"]

            metadata = {
                "name": artist_data["name"],
                "musicbrainz_id": artist_id,
                "example_tracks": [release["title"] for release in artist_data.get("release-list", [])[:3]],
                "gender": artist_data.get("gender", "Unknown"),
                "country": get_country(artist_data.get("country", "WZ")) or "Unknown",
                "tag-list": [tag["name"] for tag in artist_data.get("tag_list", [])],
                "ipi-list": artist_data.get("ipi-list", []),
                "isni-list": artist_data.get("isni-list", []),
                "born": artist_data.get("life-span", {}).get("begin", "Unknown"),
                "dead": artist_data.get("life-span", {}).get("ended", "Unknown").lower() == "true",
                "comment": artist_data.get("disambiguation", "None"),
                "urls": {}
            }

            for url_data in artist_data.get("url-relation-list", []):
                url_type = url_data.get("type", "").lower()
                url_target = url_data.get("target", "")
                if not url_type or not url_target or not url_type in ["youtube", "imdb", "viaf", "soundcloud", "wikidata", "last.fm", "lyrics", "official homepage"]:
                    continue

                if url_type in metadata["urls"]:
                    metadata["urls"][url_type].append(url_target)
                else:
                    metadata["urls"][url_type] = [url_target]

            artist_metadata[artist_data["name"]] = metadata
            metadata_cache["artist_by_id"][artist_id] = metadata
    
    with open("metadata_cache.json", "w") as file:
        file.write(json.dumps(metadata_cache))

    return artist_metadata

def extract_release_metadata(release_list):
    metadata_cache = ensure_metadata_file()

    album_metadata = {}

    for release in release_list:
        if not isinstance(release, dict):
            continue

        release_title = release.get("title", "").lower()
        release_id = release["id"]

        if any(word in release_title for word in ["single", "ep", "maxi"]):
            continue

        if release.get("status") == "Official":
            if release_id in metadata_cache["album_by_id"]:
                album_metadata[release_id] = metadata_cache["album_by_id"][release_id]
            else:
                album_metadata[release_id] = {
                    "musicbrainz_id": release.get("id") if release else "Unknown",
                    "album_name": release.get("title") if release else "Unknown",
                    "album_date": release.get("date") if release else "Unknown",
                    "album_country": (get_country(release.get("country", "WZ")) or "Worldwide") if release else "Unknown",
                    "album_tracks": [track['recording']['title'] for track in release.get('medium-list', [{}])[0].get('track-list', [])[:3]]
                }
                metadata_cache["album_by_id"][release_id] = album_metadata[release_id]

    with open("metadata_cache.json", "w") as file:
        file.write(json.dumps(metadata_cache))

    return album_metadata

def get_album_metadata(album_id):
    metadata_cache = ensure_metadata_file()

    release = music_api.get_release_by_id(album_id, includes=["recordings"])["release"]

    if album_id in metadata_cache["album_by_id"]:
        album_metadata = metadata_cache["album_by_id"][release["id"]]
    else:
        album_metadata = {
            "musicbrainz_id": release.get("id") if release else "Unknown",
            "album_name": release.get("title") if release else "Unknown",
            "album_date": release.get("date") if release else "Unknown",
            "album_country": (get_country(release.get("country", "WZ")) or "Worldwide") if release else "Unknown",
            "album_tracks": [track['recording']['title'] for track in release.get('medium-list', [{}])[0].get('track-list', [])[:3]]
        }
        metadata_cache["album_by_id"][release["id"]] = album_metadata

    with open("metadata_cache.json", "w") as file:
        file.write(json.dumps(metadata_cache))

    return album_metadata

def get_music_metadata(artist=None, title=None, musicbrainz_id=None):
    metadata_cache = ensure_metadata_file()

    music_api.set_useragent(MUSICBRAINZ_PROJECT_NAME, MUSCIBRAINZ_VERSION, MUSICBRAINZ_CONTACT)

    if not musicbrainz_id:
        if artist:
            query = f"{artist} - {title}"
        else:
            query = title

        recording_id = None

        if query in metadata_cache["query_results"]:
            recording_id = metadata_cache["query_results"][query]
        else:
            results = music_api.search_recordings(query=query, limit=100)["recording-list"]

            finalized_blacklist = finalize_blacklist(title)            

            for r in results:
                if not r.get("title") or not r.get("isrc-list"):
                    continue

                if check_blacklist(r["title"].lower(), finalized_blacklist) or check_blacklist(r.get("disambiguation", "").lower(), finalized_blacklist):
                    continue
                
                recording_id = r["id"]
                break

            metadata_cache["query_results"][query] = recording_id
    else:
        recording_id = musicbrainz_id

    if recording_id in metadata_cache["recording_by_id"]:
        detailed = metadata_cache["recording_by_id"][recording_id]
    else:
        if recording_id:
            detailed = music_api.get_recording_by_id(
                recording_id,
                includes=["artists", "releases", "isrcs", "tags", "ratings"]
            )["recording"]
            metadata_cache["recording_by_id"][recording_id] = {
                "title": detailed["title"],
                "artist-credit": [{"artist": {"id": artist_data["artist"]["id"]}} for artist_data in detailed.get("artist-credit", {}) if isinstance(artist_data, dict)],
                "isrc-list":  detailed["isrc-list"] if "isrc-list" in detailed else [],
                "rating": {"rating": detailed["rating"]["rating"]} if "rating" in detailed else {},
                "tags": detailed.get("tag-list", []),
                "release-list": [{"id": release["id"], "title": release["title"], "status": release.get("status"), "date": release.get("date"), "country": release.get("country", "WZ")} for release in detailed["release-list"]] if "release-list" in detailed else [],
                "release-event-count": detailed.get("release-event-count", 0)
            }
        else:
            detailed = metadata_cache["recording_by_id"][recording_id] = {
                "title": title,
                "artist-credit": [],
                "isrc-list": [],
                "rating": {},
                "tags": [],
                "release-list": [],
                "release-event-count": 0
            }

    with open("metadata_cache.json", "w") as file:
        file.write(json.dumps(metadata_cache))

    artist_ids = [artist_data["artist"]["id"] for artist_data in detailed.get("artist-credit", {}) if isinstance(artist_data, dict)] # isinstance is needed, because sometimes & is included as an artist str
    artist_metadata = get_artists_metadata(artist_ids)
    album_metadata = extract_release_metadata(detailed.get("release-list", []))

    music_metadata = {
        "musicbrainz_id": recording_id,
        "isrc-list": detailed["isrc-list"] if "isrc-list" in detailed else [],
        "musicbrainz_rating": detailed["rating"]["rating"] if "rating" in detailed.get("rating", {}) else "Unknown",
        "tags": [tag["name"] for tag in detailed.get("tag-list", [])]
    }
    return music_metadata, artist_metadata, album_metadata, get_lyrics(', '.join([artist for artist in artist_metadata]), detailed["title"])

def search_recordings(search_term):
    music_api.set_useragent(MUSICBRAINZ_PROJECT_NAME, MUSCIBRAINZ_VERSION, MUSICBRAINZ_CONTACT)
    results = music_api.search_recordings(query=search_term, limit=100)["recording-list"]

    finalized_blacklist = finalize_blacklist(search_term)

    output_list = []

    for r in results:
        if not r.get("title") or not r.get("isrc-list"):
            continue

        if check_blacklist(r["title"].lower(), finalized_blacklist) or check_blacklist(r.get("disambiguation", "").lower(), finalized_blacklist):
            continue
        
        artist_str = ", ".join([artist["name"] for artist in r["artist-credit"] if isinstance(artist, dict)])
        output_list.append((artist_str, r["title"], r["id"]))

    return output_list

def search_artists(search_term):
    music_api.set_useragent(MUSICBRAINZ_PROJECT_NAME, MUSCIBRAINZ_VERSION, MUSICBRAINZ_CONTACT)
    
    results = music_api.search_artists(query=search_term)

    output_list = []

    for r in results["artist-list"]:
        output_list.append((r["name"], r["id"]))

    return output_list

def search_albums(search_term):
    music_api.set_useragent(MUSICBRAINZ_PROJECT_NAME, MUSCIBRAINZ_VERSION, MUSICBRAINZ_CONTACT)

    results = music_api.search_releases(search_term)

    output_list = []

    for r in results["release-list"]:
        artist_str = ", ".join([artist["name"] for artist in r["artist-credit"] if isinstance(artist, dict)])
        output_list.append((artist_str, r["title"], r["id"]))

    return output_list