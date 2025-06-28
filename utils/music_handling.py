import io, base64, tempfile, struct, re, os, logging, arcade, time

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TXXX, ID3NoHeaderError
from mutagen import File

from pydub import AudioSegment
from PIL import Image

from utils.utils import convert_seconds_to_date

def truncate_end(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text
    return text[:max_length - 3] + '...'

def extract_metadata_and_thumbnail(file_path: str, thumb_resolution: tuple) -> tuple:
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
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')

    try:
        thumb_audio = EasyID3(file_path)
        try:
            artist = str(thumb_audio["artist"][0])
            title = str(thumb_audio["title"][0])
            upload_year = int(thumb_audio["date"][0])
        except KeyError:
            artist_title_match = re.search(r'^.+\s*-\s*.+$', title)
            if artist_title_match:
                title = title.split("- ")[1]

        file_audio = File(file_path)
        if hasattr(file_audio, 'info'):
            sound_length = round(file_audio.info.length, 2)
            bitrate = int((file_audio.info.bitrate or 0) / 1000)
            sample_rate = int(file_audio.info.sample_rate / 1000)

        thumb_image_data = None
        if ext == 'mp3':
            for tag in file_audio.values():
                if tag.FrameID == "APIC":
                    thumb_image_data = tag.data
                    break
        elif ext in ('m4a', 'aac'):
            if 'covr' in file_audio:
                thumb_image_data = file_audio['covr'][0]
        elif ext == 'flac':
            if file_audio.pictures:
                thumb_image_data = file_audio.pictures[0].data
        elif ext in ('ogg', 'opus'):
            if "metadata_block_picture" in file_audio:
                pic_data = base64.b64decode(file_audio["metadata_block_picture"][0])
                header_len = struct.unpack(">I", pic_data[0:4])[0]
                thumb_image_data = pic_data[4 + header_len:]

        id3 = ID3(file_path)
        for frame in id3.getall("WXXX"):
            if frame.desc.lower() == "uploader":
                uploader_url = frame.url
            elif frame.desc.lower() == "source":
                source_url = frame.url

        for frame in id3.getall("TXXX"):
            if frame.desc.lower() == "last_played":
                last_played = float(frame.text[0])
            elif frame.desc.lower() == "play_count":
                play_count = int(frame.text[0])

        if thumb_image_data:
            pil_image = Image.open(io.BytesIO(thumb_image_data)).convert("RGBA")
            pil_image = pil_image.resize(thumb_resolution)
            thumb_texture = arcade.Texture(pil_image)

    except Exception as e:
        logging.debug(f"[Metadata/Thumbnail Error] {file_path}: {e}")

    if artist == "Unknown" or not title:
        match = re.search(r'^(.*?)\s+-\s+(.*?)$', name_only)
        if match:
            file_path_artist, file_path_title = match.groups()
            if artist == "Unknown":
                artist = file_path_artist
            if not title:
                title = file_path_title

    if not title:
        title = name_only

    if thumb_texture is None:
        from utils.preload import music_icon
        thumb_texture = music_icon

    file_size = round(os.path.getsize(file_path) / (1024 ** 2), 2) # MiB

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
        "thumbnail": thumb_texture
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
