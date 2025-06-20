from mutagen.easyid3 import EasyID3
from pydub import AudioSegment

import arcade, arcade.gui, os, json, threading, subprocess

from arcade.gui.experimental.focus import UIFocusGroup

from utils.utils import UIFocusTextureButton, ensure_yt_dlp
from utils.constants import button_style
from utils.preload import button_texture, button_hovered_texture

class Downloader(arcade.gui.UIView):
    def __init__(self, pypresence_client, current_mode, current_music_name, current_length, current_music_player, queue, loaded_sounds, shuffle):
        super().__init__()

        self.current_mode = current_mode
        self.current_music_name = current_music_name
        self.current_length = current_length
        self.current_music_player = current_music_player
        self.queue = queue
        self.loaded_sounds = loaded_sounds
        self.shuffle = shuffle

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
        self.status_label.text = self.yt_dl_buffer

        if "WARNING" in self.yt_dl_buffer:
            self.status_label.update_font(font_color=arcade.color.YELLOW)
        elif "ERROR" in self.yt_dl_buffer:
            self.status_label.update_font(font_color=arcade.color.RED)
        else:
            self.status_label.update_font(font_color=arcade.color.LIGHT_GREEN)

    def run_yt_dlp(self, url):
        yt_dlp_path = ensure_yt_dlp()

        command = [
            yt_dlp_path, f"{url}",
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
                audio = EasyID3("downloaded_music.mp3")
                audio["artist"] = artist
                audio["title"] = track_title
                audio.save()
            except Exception as meta_err:
                self.yt_dl_buffer = f"ERROR: Tried to override metadata based on title, but failed: {meta_err}"
                return

            if self.settings_dict.get("normalize_audio", True):
                try:
                    audio = AudioSegment.from_file("downloaded_music.mp3")

                    if int(audio.dBFS) != self.settings_dict.get("normalized_volume", -8):
                        change = self.settings_dict.get("normalized_volume", -8) - audio.dBFS
                        audio = audio.apply_gain(change)

                        audio.export("downloaded_music.mp3", format="mp3")

                except Exception as e:
                    self.yt_dl_buffer = f"ERROR: Could not normalize volume due to an error: {e}"
                    return
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

    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client, self.current_mode, self.current_music_name, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))
