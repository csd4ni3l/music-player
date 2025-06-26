import logging, sys, traceback, os, re, platform, urllib.request, io, base64, tempfile, struct

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen import File

from pydub import AudioSegment

from PIL import Image

from utils.constants import menu_background_color, button_style
from utils.preload import button_texture, button_hovered_texture

import pyglet, arcade, arcade.gui

def dump_platform():
    import platform
    logging.debug(f'Platform: {platform.platform()}')
    logging.debug(f'Release: {platform.release()}')
    logging.debug(f'Machine: {platform.machine()}')
    logging.debug(f'Architecture: {platform.architecture()}')

def dump_gl():
    from pyglet.gl import gl_info as info
    logging.debug(f'gl_info.get_version(): {info.get_version()}')
    logging.debug(f'gl_info.get_vendor(): {info.get_vendor()}')
    logging.debug(f'gl_info.get_renderer(): {info.get_renderer()}')

def print_debug_info():
    logging.debug('########################## DEBUG INFO ##########################')
    logging.debug('')
    dump_platform()
    dump_gl()
    logging.debug('')
    logging.debug(f'Number of screens: {len(pyglet.display.get_display().get_screens())}')
    logging.debug('')
    for n, screen in enumerate(pyglet.display.get_display().get_screens()):
        logging.debug(f"Screen #{n+1}:")
        logging.debug(f'DPI: {screen.get_dpi()}')
        logging.debug(f'Scale: {screen.get_scale()}')
        logging.debug(f'Size: {screen.width}, {screen.height}')
        logging.debug(f'Position: {screen.x}, {screen.y}')
    logging.debug('')
    logging.debug('########################## DEBUG INFO ##########################')
    logging.debug('')

class ErrorView(arcade.gui.UIView):
    def __init__(self, message: str, title: str):
        super().__init__()

        self.message = message
        self.title = title

    def exit(self):
        logging.fatal('Exited with error code 1.')
        sys.exit(1)

    def on_show_view(self):
        super().on_show_view()

        self.window.set_caption('Music Player - Error')
        self.window.set_mouse_visible(True)
        self.window.set_exclusive_mouse(False)
        arcade.set_background_color(menu_background_color)

        msgbox = arcade.gui.UIMessageBox(width=self.window.width / 2, height=self.window.height / 2, message_text=self.message, title=self.title)
        msgbox.on_action = lambda event: self.exit()
        self.add_widget(msgbox)


class FakePyPresence():
    def __init__(self):
        ...
    def update(self, *args, **kwargs):
        ...
    def close(self, *args, **kwargs):
        ...

class UIFocusTextureButton(arcade.gui.UITextureButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        arcade.gui.bind(self, "hovered", self.on_hover)

    def on_hover(self):
        if self.hovered:
            self.resize(width=self.width * 1.1, height=self.height * 1.1)
        else:
            self.resize(width=self.width / 1.1, height=self.height / 1.1)

class MusicItem(arcade.gui.UIBoxLayout):
    def __init__(self, metadata: dict, width: int, height: int, texture: arcade.Texture, padding=10):
        super().__init__(width=width, height=height, space_between=padding, align="top", vertical=False)

        if metadata:
            self.image = self.add(arcade.gui.UIImage(
                texture=texture,
                width=height * 1.5,
                height=height,
            ))

        self.button = self.add(arcade.gui.UITextureButton(
            text=f"{metadata['artist']} - {metadata['title']}" if metadata else "Add Music",
            texture=button_texture,
            texture_hovered=button_hovered_texture,
            texture_pressed=button_texture,
            texture_disabled=button_texture,
            style=button_style,
            width=width * 0.85,
            height=height,
            interaction_buttons=[arcade.MOUSE_BUTTON_LEFT, arcade.MOUSE_BUTTON_RIGHT]
        ))

        if metadata:
            self.view_metadata_button = self.add(arcade.gui.UITextureButton(
                text="View Metadata",
                texture=button_texture,
                texture_hovered=button_hovered_texture,
                texture_pressed=button_texture,
                texture_disabled=button_texture,
                style=button_style,
                width=width * 0.1,
                height=height,
            ))

def on_exception(*exc_info):
    logging.error(f"Unhandled exception:\n{''.join(traceback.format_exception(exc_info[1], limit=None))}")

def get_closest_resolution():
    allowed_resolutions = [(1366, 768), (1440, 900), (1600,900), (1920,1080), (2560,1440), (3840,2160)]
    screen_width, screen_height = arcade.get_screens()[0].width, arcade.get_screens()[0].height
    if (screen_width, screen_height) in allowed_resolutions:
        if not allowed_resolutions.index((screen_width, screen_height)) == 0:
            closest_resolution = allowed_resolutions[allowed_resolutions.index((screen_width, screen_height))-1]
        else:
            closest_resolution = (screen_width, screen_height)
    else:
        target_width, target_height = screen_width // 2, screen_height // 2

        closest_resolution = min(
            allowed_resolutions,
            key=lambda res: abs(res[0] - target_width) + abs(res[1] - target_height)
        )
    return closest_resolution

def get_yt_dlp_binary_path():
    system = platform.system()

    if system == "Windows":
        binary = "yt-dlp.exe"
    elif system == "Darwin":
        binary = "yt-dlp_macos"
    elif system == "Linux":
        binary = "yt-dlp_linux"

    return os.path.join("bin", binary)

def ensure_yt_dlp():
    path = get_yt_dlp_binary_path()

    if not os.path.exists("bin"):
        os.makedirs("bin")

    if not os.path.exists(path):
        system = platform.system()

        if system == "Windows":
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        elif system == "Darwin":
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
        elif system == "Linux":
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux"
        else:
            raise RuntimeError("Unsupported OS")

        urllib.request.urlretrieve(url, path)
        os.chmod(path, 0o755)

    return path

def truncate_end(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text
    return text[:max_length - 3] + '...'

def extract_metadata_and_thumbnail(filename: str, thumb_resolution: tuple) -> tuple:
    artist = "Unknown"
    title = ""
    source_url = "Unknown"
    creator_url = "Unknown"
    thumb_texture = None
    sound_length = 0
    bit_rate = 0

    basename = os.path.basename(filename)
    name_only = re.sub(r'\s*\[[a-zA-Z0-9\-_]{5,}\]$', '', os.path.splitext(basename)[0])
    ext = os.path.splitext(filename)[1].lower().lstrip('.')

    try:
        thumb_audio = EasyID3(filename)
        try:
            artist = str(thumb_audio["artist"][0])
            title = str(thumb_audio["title"][0])
        except KeyError:
            artist_title_match = re.search(r'^.+\s*-\s*.+$', title)
            if artist_title_match:
                title = title.split("- ")[1]

        file_audio = File(filename)
        if hasattr(file_audio, 'info'):
            sound_length = round(file_audio.info.length, 2)
            bit_rate = int((file_audio.info.bitrate or 0) / 1000)

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

        id3 = ID3(filename)
        for frame in id3.getall("WXXX"):
            if frame.desc.lower() == "creator":
                creator_url = frame.url
            elif frame.desc.lower() == "source":
                source_url = frame.url

        if thumb_image_data:
            pil_image = Image.open(io.BytesIO(thumb_image_data)).convert("RGBA")
            pil_image = pil_image.resize(thumb_resolution)
            thumb_texture = arcade.Texture(pil_image)

    except Exception as e:
        logging.debug(f"[Metadata/Thumbnail Error] {filename}: {e}")

    if artist == "Unknown" or not title:
        match = re.search(r'^(.*?)\s+-\s+(.*?)$', name_only)
        if match:
            filename_artist, filename_title = match.groups()
            if artist == "Unknown":
                artist = filename_artist
            if not title:
                title = filename_title

    if not title:
        title = name_only

    if thumb_texture is None:
        from utils.preload import music_icon
        thumb_texture = music_icon

    return sound_length, bit_rate, creator_url, source_url, artist, title, thumb_texture

def adjust_volume(input_path, volume):
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

    audio = AudioSegment.from_file(input_path)
    
    if int(audio.dBFS) == volume:
        return
    
    export_args = {
        "format": "mp3",
        "tags": tags
    }
    if cover_path:
        export_args["cover"] = cover_path

    change = volume - audio.dBFS
    audio.apply_gain(change)
    audio.export(input_path, **export_args)

def convert_seconds_to_date(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    result = ""
    if days > 0:
        result += "{} days ".format(int(days))
    if hours > 0:
        result += "{} hours ".format(int(hours))
    if minutes > 0:
        result += "{} minutes ".format(int(minutes))
    if seconds > 0 or not any([days, hours, minutes]):
        result += "{} seconds".format(int(seconds))

    return result.strip()