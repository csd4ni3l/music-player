from io import BytesIO

from PIL import Image

from concurrent.futures import ThreadPoolExecutor, as_completed

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from utils.constants import COVER_CACHE_DIR, MUSCIBRAINZ_VERSION, MUSICBRAINZ_CONTACT, MUSICBRAINZ_PROJECT_NAME

import musicbrainzngs as music_api

import os, logging, arcade

def fetch_image_bytes(url):
    try:
        req = Request(url, headers={"User-Agent": "csd4ni3l/music-player/git python-musicbrainzngs/0.7.1 ( csd4ni3l@proton.me )"})
        with urlopen(req, timeout=10) as resp:
            return resp.read()
    except (HTTPError, URLError) as e:
        logging.debug(f"Error fetching {url}: {e}")
        return None

def download_cover_art(mb_album_id, size=250):
    path = os.path.join(COVER_CACHE_DIR, f"{mb_album_id}_{size}.png")
    if os.path.exists(path):
        return mb_album_id, Image.open(path)

    url = f"https://coverartarchive.org/release/{mb_album_id}/front-{size}"
    img_bytes = fetch_image_bytes(url)
    if not img_bytes:
        return mb_album_id, None

    try:
        img = Image.open(BytesIO(img_bytes)).convert("RGBA")
        img.save(path)
        return mb_album_id, img
    except Exception as e:
        logging.debug(f"Failed to decode/save image for {mb_album_id}: {e}")
        return mb_album_id, None

def download_albums_cover_art(album_ids, size=250, max_workers=5):
    music_api.set_useragent(MUSICBRAINZ_PROJECT_NAME, MUSCIBRAINZ_VERSION, MUSICBRAINZ_CONTACT)
    os.makedirs(COVER_CACHE_DIR, exist_ok=True)
    images = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_cover_art, album_id, size) for album_id in album_ids]
        for future in as_completed(futures):
            album_id, img = future.result()
            images[album_id] = arcade.Texture(img) if img else None
    return images