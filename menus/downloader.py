from mutagen.id3 import ID3, TIT2, TPE1, WXXX
from mutagen.mp3 import MP3

import arcade, arcade.gui, os, json, threading, subprocess, urllib.request, platform

from arcade.gui.experimental.focus import UIFocusGroup

from utils.music_handling import adjust_volume, add_metadata_to_file
from utils.musicbrainz_metadata import get_music_metadata
from utils.acoustid_metadata import get_recording_id_from_acoustid
from utils.constants import button_style
from utils.preload import button_texture, button_hovered_texture

class Downloader(arcade.gui.UIView):
    def __init__(self, pypresence_client, *args):
        super().__init__()

        self.args = args

        self.pypresence_client = pypresence_client
        self.pypresence_client.update(state="Downloading music", start=self.pypresence_client.start_time)

        with open("settings.json", "r", encoding="utf-8") as file:
            self.settings_dict = json.load(file)

        self.tab_options = self.settings_dict.get("tab_options", [os.path.join("~", "Music"), os.path.join("~", "Downloads")])
        self.yt_dl_buffer = ""

    def on_show_view(self):
        super().on_show_view()

        self.anchor = self.add_widget(UIFocusGroup(size_hint=(1, 1)))

        self.download_box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=10), anchor_x="center", anchor_y="center")

        self.url_name_label = self.download_box.add(arcade.gui.UILabel(text="URL or Name:", font_name="Roboto", font_size=36))
        self.url_name_input = self.download_box.add(arcade.gui.UIInputText(font_name="Roboto", width=self.window.width / 2, height=self.window.height / 15, font_size=36))
        self.url_name_input.activate()

        self.tab_label = self.download_box.add(arcade.gui.UILabel(text="Path:", font_name="Roboto", font_size=36))
        self.tab_selector = self.download_box.add(arcade.gui.UIDropdown(default=self.tab_options[0], options=self.tab_options, width=self.window.width / 2, height=self.window.height / 15, primary_style=button_style, dropdown_style=button_style, active_style=button_style))

        self.status_label = self.download_box.add(arcade.gui.UILabel(text="No errors.", font_size=16, text_color=arcade.color.LIGHT_GREEN))

        self.download_button = self.anchor.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='Download', style=button_style, width=self.window.width / 2, height=self.window.height / 10), anchor_x="center", anchor_y="bottom", align_y=10)
        self.download_button.on_click = lambda event: threading.Thread(target=self.download, daemon=True).start()

        self.back_button = self.anchor.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='<--', style=button_style, width=100, height=50), anchor_x="left", anchor_y="top", align_x=5, align_y=-5)
        self.back_button.on_click = lambda event: self.main_exit()

        self.anchor.detect_focusable_widgets()

    def on_update(self, delta_time: float) -> bool | None:
        if not self.yt_dl_buffer == "download_yt_dlp":
            self.status_label.text = self.yt_dl_buffer

            if "WARNING" in self.yt_dl_buffer:
                self.status_label.update_font(font_color=arcade.color.YELLOW)
            elif "ERROR" in self.yt_dl_buffer:
                self.status_label.update_font(font_color=arcade.color.RED)
            else:
                self.status_label.update_font(font_color=arcade.color.LIGHT_GREEN)
        else:
            msgbox = self.ui.add(arcade.gui.UIMessageBox(width=self.window.width / 2, height=self.window.height / 2, title="This app needs to download third-party software.", message_text="This app needs to download yt-dlp (a third-party tool) to enable video/audio downloading.\n Do you want to continue?", buttons=("Yes", "No")))
            msgbox.on_action = lambda event: self.install_and_run_yt_dlp() if event.action == "Yes" else None
            self.yt_dl_buffer = ''

    def run_yt_dlp(self, url):
        if not self.check_for_yt_dlp():
            self.yt_dl_buffer = "download_yt_dlp"
            return None
                
        command = [
            self.get_yt_dlp_path(), f"{url}",
            "--write-info-json",
            "-x", "--audio-format", "mp3",
            "-o", "downloaded_music.mp3",
            "--no-playlist",
            "--embed-thumbnail",
            "--embed-metadata"
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        for line in process.stdout:
             self.yt_dl_buffer = line.strip()

        process.wait()

        if process.returncode != 0:
            return None

        try:
            with open("downloaded_music.mp3.info.json", "r", encoding="utf-8") as file:
                info = json.load(file)
            return info
        except (json.JSONDecodeError, OSError):
            self.yt_dl_buffer += "\nERROR: Failed to parse yt-dlp JSON output.\n"
            return None

    def download(self):
        if not self.tab_selector.value:
            return

        url = self.url_name_input.text

        if not "http" in url:
            url = f"ytsearch1:{url}"

        path = os.path.expanduser(self.tab_selector.value)

        info = self.run_yt_dlp(url)
        if not info:
            return # download will get re-executed.
        
        os.remove("downloaded_music.mp3.info.json")
        os.remove("downloaded_music.info.json")

        if info:
            title = info.get('title', 'Unknown')
            uploader = info.get('uploader', 'Unknown')

            if " - " in title:
                artist, track_title = title.split(" - ", 1)
            else:
                artist = uploader
                track_title = title
                title = f"{artist} - {track_title}"

            try:
                audio = MP3("downloaded_music.mp3", ID3=ID3)
                if audio.tags is None:
                    audio.add_tags()
                else:
                    for frame_id in ("TIT2", "TPE1", "WXXX"):
                        audio.tags.delall(frame_id)
                audio.tags.add(TIT2(encoding=3, text=track_title))
                audio.tags.add(TPE1(encoding=3, text=artist))
                if info.get("creator_url"):
                    audio.tags.add(WXXX(desc="Uploader", url=info["uploader_url"]))
                audio.tags.add(WXXX(desc="Source", url=info["webpage_url"]))

                audio.save()
            except Exception as meta_err:
                self.yt_dl_buffer = f"ERROR: Tried to override metadata based on title, but failed: {meta_err}"
                return

            if self.settings_dict.get("normalize_audio", True):
                self.yt_dl_buffer = "Normalizing audio..."
                try:
                    adjust_volume("downloaded_music.mp3", self.settings_dict.get("normalized_volume", -8))

                except Exception as e:
                    self.yt_dl_buffer = f"ERROR: Could not normalize volume due to an error: {e}"
                    return
                
            self.yt_dl_buffer = "Analyzing with Acoustid to get accurate metadata..."
            acoustid_id, musicbrainz_id = get_recording_id_from_acoustid("downloaded_music.mp3")

            self.yt_dl_buffer = "Caching MusicBrainz and Lyrics metadata..."
            if musicbrainz_id:
                music_metadata, artist_metadata, album_metadata, lyrics_metadata = get_music_metadata(musicbrainz_id=musicbrainz_id)
            else:
                music_metadata, artist_metadata, album_metadata, lyrics_metadata = get_music_metadata(artist=artist, title=title)

            self.yt_dl_buffer = "Adding missing metadata to file..."
            add_metadata_to_file("downloaded_music.mp3", [artist['musicbrainz_id'] for artist in artist_metadata.values()], artist, title, lyrics_metadata[1], music_metadata["isrc-list"], acoustid_id)

            try:
                output_filename = os.path.join(path, f"{title}.mp3")
                os.replace("downloaded_music.mp3", output_filename)

            except Exception as e:
                self.yt_dl_buffer = f"ERROR: Could not move file due to an error: {e}"
                return
        else:
            self.yt_dl_buffer = f"ERROR: Info unavailable. This maybe due to being unable to download it due to DRM or other issues"
            return

        self.yt_dl_buffer = f"Successfully downloaded {title} to {path}"

    def get_yt_dlp_path(self):
        system = platform.system()

        if system == "Windows":
            return os.path.join("bin", "yt-dlp.exe")
        elif system == "Darwin":
            return os.path.join("bin", "yt-dlp_macos")
        elif system == "Linux":
            return os.path.join("bin", "yt-dlp_linux")

    def check_for_yt_dlp(self):
        path = self.get_yt_dlp_path()
            
        if not os.path.exists("bin"):
            os.makedirs("bin")

        return os.path.exists(path)

    def install_and_run_yt_dlp(self):
        system = platform.system()
        path = self.get_yt_dlp_path()

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
        
        threading.Thread(target=self.download, daemon=True).start()

    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client, *self.args))
