import logging, sys, traceback, os, re, platform, urllib.request, zipfile, subprocess, textwrap, io, base64
from mutagen.easyid3 import EasyID3
from mutagen import File
from PIL import Image
from utils.constants import menu_background_color
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

class Card(arcade.gui.UIBoxLayout):
    def __init__(self, width: int, height: int, font_name: str, font_size: int, text: str, card_texture: arcade.Texture, padding=10):
        super().__init__(width=width, height=height, space_between=padding, align="top")

        self.button = self.add(arcade.gui.UITextureButton(
            texture=card_texture,
            texture_hovered=card_texture,
            texture_pressed=card_texture,
            texture_disabled=card_texture,
            width=width,
            height=height,
        ))

        wrapped_lines = textwrap.wrap(text, width=int(width / (font_size * 0.6)))
        wrapped_text = "\n".join(wrapped_lines)

        self.label = self.add(arcade.gui.UILabel(
            text=wrapped_text,
            font_name=font_name,
            font_size=font_size,
            width=width,
            height=height * 0.1,
            multiline=True,
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

def extract_metadata(filename):
    artist = "Unknown"
    title = ""

    basename = os.path.basename(filename)
    name_only = os.path.splitext(basename)[0]

    name_only = re.sub(r'\s*\[[a-zA-Z0-9\-_]{5,}\]$', '', name_only)

    try:
        thumb_audio = EasyID3(filename)

        artist = str(thumb_audio["artist"][0])
        title = str(thumb_audio["title"][0])

        artist_title_match = re.search(r'^.+\s*-\s*.+$', title) # check for Artist - Title titles, so Artist doesnt appear twice

        if artist_title_match:
            title = title.split("- ")[1]

        if artist != "Unknown" and title:
            return artist, title
    except:
        pass

    if artist == "Unknown" or not title:
        match = re.search(r'^(.*?)\s+-\s+(.*?)$', name_only)
        if match:
            filename_artist, filename_title = match.groups()

            if artist == "Unknown":
                artist = filename_artist

            if not title:
                title = filename_title

            return artist, title

    if not title:
        title = name_only

    return artist, title

def get_audio_thumbnail_texture(audio_path: str, window_resolution: tuple) -> arcade.Texture:
    ext = os.path.splitext(audio_path)[1].lower().lstrip('.')
    thumb_audio = File(audio_path)

    thumb_image_data = None

    try:
        if ext == 'mp3':
            for tag in thumb_audio.values():
                if tag.FrameID == "APIC":
                    thumb_image_data = tag.data
                    break

        elif ext in ('m4a', 'mp4', 'aac'):
            if 'covr' in thumb_audio:
                thumb_image_data = thumb_audio['covr'][0]

        elif ext == 'flac':
            if thumb_audio.pictures:
                thumb_image_data = thumb_audio.pictures[0].data

        elif ext in ('ogg', 'opus'):
            if "metadata_block_picture" in thumb_audio:
                pic_data = base64.b64decode(thumb_audio["metadata_block_picture"][0])
                import struct
                header_len = struct.unpack(">I", pic_data[0:4])[0]
                thumb_image_data = pic_data[4 + header_len:]

        if thumb_image_data:
            pil_image = Image.open(io.BytesIO(thumb_image_data)).convert("RGBA")
            pil_image = pil_image.resize((int(window_resolution[0] / 5), int(window_resolution[1] / 8)))
            thumb_texture = arcade.Texture(pil_image)
            return thumb_texture

    except Exception as e:
        logging.debug(f"[Thumbnail Error] {audio_path}: {e}")

    from utils.preload import music_icon
    return music_icon
