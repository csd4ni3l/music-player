import io, tempfile, re, os, logging, arcade, time

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TXXX, SYLT, ID3NoHeaderError

from pydub import AudioSegment
from PIL import Image

from utils.lyrics_metadata import parse_synchronized_lyrics
from utils.utils import convert_seconds_to_date

def truncate_end(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text
    return text[:max_length - 3] + '...'

def extract_metadata_and_thumbnail(file_path: str, thumb_resolution: tuple):
    artist = "Unknown"
    title = ""
    source_url = "Unknown"
    uploader_url = "Unknown"
    thumb_texture = None
    sound_length = 0
    bitrate = 0
    sample_rate = 0
    last_played = 0
    play_count = 0
    upload_year = 0

    basename = os.path.basename(file_path)
    name_only = os.path.splitext(basename)[0]

    try:
        try:
            easyid3 = EasyID3(file_path)
            if "artist" in easyid3:  
                artist = easyid3["artist"][0]
            if "title" in easyid3:
                title  = easyid3["title"][0]
            if "date" in easyid3:
                upload_year = int(re.match(r"\d{4}", easyid3["date"][0]).group())

            id3 = ID3(file_path)
            for frame in id3.getall("WXXX"):
                desc = frame.desc.lower()
                if desc == "uploader":
                    uploader_url = frame.url
                elif desc == "source":
                    source_url = frame.url
            for frame in id3.getall("TXXX"):
                desc = frame.desc.lower()
                if desc == "last_played":
                    last_played = float(frame.text[0])
                elif desc == "play_count":
                    play_count = int(frame.text[0])
        except ID3NoHeaderError:
            pass

        if hasattr(easyid3, "info"):
            sound_length = round(easyid3.info.length, 2)
            bitrate = int((easyid3.info.bitrate or 0) / 1000)
            sample_rate = int(easyid3.info.sample_rate / 1000)

        apic = id3.getall("APIC")
        thumb_image_data = apic[0].data if apic else None

        if thumb_image_data:
            pil_image = Image.open(io.BytesIO(thumb_image_data)).convert("RGBA")
            pil_image = pil_image.resize(thumb_resolution)
            thumb_texture = arcade.Texture(pil_image)

    except Exception as e:
        logging.debug(f"[Metadata/Thumbnail Error] {file_path}: {e}")

    if artist == "Unknown" or not title:
        m = re.match(r"^(.*?)\s+-\s+(.*?)$", name_only) # check for artist - title titles in the title
        if m:
            artist = m.group(1)
            title  = m.group(2)

    if not title: 
        title = name_only
    
    if thumb_texture is None:
        from utils.preload import music_icon
        thumb_texture = music_icon

    file_size = round(os.path.getsize(file_path) / (1024 ** 2), 2)

    return {
        "sound_length": sound_length,
        "bitrate": bitrate,
        "file_size": file_size,
        "last_played": last_played,
        "play_count": play_count,
        "upload_year": upload_year,
        "sample_rate": sample_rate,
        "uploader_url": uploader_url,
        "source_url": source_url,
        "artist": artist,
        "title": title,
        "thumbnail": thumb_texture,
    }


def adjust_volume(input_path, volume):
    audio = AudioSegment.from_file(input_path)
    change = volume - audio.dBFS

    if abs(change) < 1.0:
        return

    try:
        easy_tags = EasyID3(input_path)
        tags = dict(easy_tags)
        tags = {k: v[0] if isinstance(v, list) else v for k, v in tags.items()}
    except Exception as e:
        tags = {}

    try:
        id3 = ID3(input_path)
        apic_frames = [f for f in id3.values() if f.FrameID == "APIC"]
        cover_path = None
        if apic_frames:
            apic = apic_frames[0]
            ext = ".jpg" if apic.mime == "image/jpeg" else ".png"
            temp_cover = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_cover.write(apic.data)
            temp_cover.close()
            cover_path = temp_cover.name
        else:
            cover_path = None
    except Exception as e:
        cover_path = None

    audio = audio.apply_gain(change)

    export_args = {
        "format": "mp3",
        "tags": tags
    }
    if cover_path:
        export_args["cover"] = cover_path

    audio.export(input_path, **export_args)

def update_last_play_statistics(filepath):
    try:
        audio = ID3(filepath)
    except ID3NoHeaderError:
        audio = ID3()

    audio.setall("TXXX:last_played", [TXXX(desc="last_played", text=str(time.time()))])

    play_count_frames = audio.getall("TXXX:play_count")
    if play_count_frames:
        try:
            count = int(play_count_frames[0].text[0])
        except (ValueError, IndexError):
            count = 0
    else:
        count = 0

    audio.setall("TXXX:play_count", [TXXX(desc="play_count", text=str(count + 1))])

    audio.save(filepath)

def convert_timestamp_to_time_ago(timestamp):
    current_timestamp = time.time()
    elapsed_time = current_timestamp - timestamp
    if not timestamp == 0:
        return convert_seconds_to_date(elapsed_time) + ' ago'
    else:
        return "Never"

def add_metadata_to_file(file_path, musicbrainz_artist_ids, artist, title, synchronized_lyrics, isrc, acoustid_id=None):
    easyid3 = EasyID3(file_path)
    easyid3["musicbrainz_artistid"] = musicbrainz_artist_ids
    easyid3["artist"] = artist
    easyid3["title"] = title
    easyid3["isrc"] = isrc

    if acoustid_id:
        easyid3["acoustid_id"] = acoustid_id

    easyid3.save()

    id3 = ID3(file_path)
    id3.delall("SYLT")

    lyrics_dict = parse_synchronized_lyrics(synchronized_lyrics)[1]
    synchronized_lyrics_tuples = [(text, int(lyrics_time * 1000)) for lyrics_time, text in lyrics_dict.items()] # * 1000 because format 2 means milliseconds

    id3.add(SYLT(encoding=3, lang="eng", format=2, type=1, desc="From lrclib", text=synchronized_lyrics_tuples))
    
    id3.save()