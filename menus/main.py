import random, asyncio, pypresence, time, copy, json, os, logging
import arcade, arcade.gui, pyglet

from utils.preload import *
from utils.constants import button_style, slider_style, audio_extensions, discord_presence_id
from utils.utils import FakePyPresence, UIFocusTextureButton, extract_metadata, truncate_end

from thefuzz import process, fuzz
from pydub import AudioSegment

from arcade.gui.experimental.scroll_area import UIScrollArea, UIScrollBar
from arcade.gui.experimental.focus import UIFocusGroup

class Main(arcade.gui.UIView):
    def __init__(self, pypresence_client: None | FakePyPresence | pypresence.Presence=None, current_mode: str | None=None, current_music_name: str | None=None,
                current_length: int | None=None, current_music_player: pyglet.media.Player | None=None, queue: list | None=None,
                loaded_sounds: dict | None=None, shuffle: bool=False):
        super().__init__()
        self.pypresence_client = pypresence_client

        with open("settings.json", "r") as file:
            self.settings_dict = json.load(file)

        if self.settings_dict.get('discord_rpc', True):
            if self.pypresence_client == None: # Game has started
                try:
                    asyncio.get_event_loop()
                except:
                    asyncio.set_event_loop(asyncio.new_event_loop())

                try:
                    self.pypresence_client = pypresence.Presence(discord_presence_id)
                    self.pypresence_client.connect()
                    self.pypresence_client.start_time = time.time()
                except:
                    self.pypresence_client = FakePyPresence()
                    self.pypresence_client.start_time = time.time()

            elif isinstance(self.pypresence_client, FakePyPresence): # the user has enabled RPC in the settings in this session.
                # get start time from old object
                start_time = copy.deepcopy(self.pypresence_client.start_time)
                try:
                    self.pypresence_client = pypresence.Presence(discord_presence_id)
                    self.pypresence_client.connect()
                    self.pypresence_client.start_time = start_time
                except:
                    self.pypresence_client = FakePyPresence()
                    self.pypresence_client.start_time = start_time

            else:
                self.pypresence_client = pypresence_client
        else: # game has started, but the user has disabled RPC in the settings.
            self.pypresence_client = FakePyPresence()
            self.pypresence_client.start_time = time.time()

        self.tab_options = self.settings_dict.get("tab_options", ["~/Music", "~/Downloads"])
        self.tab_content = {}
        self.playlist_content = {}
        self.tab_buttons = {}
        self.music_buttons = {}

        self.current_music_name = current_music_name
        self.current_length = current_length if current_length else 0
        self.current_music_player = current_music_player
        self.current_mode = current_mode or "files"
        self.current_playlist = None
        self.time_to_seek = None
        self.current_tab = self.tab_options[0]
        self.queue = queue if queue else []
        self.loaded_sounds = loaded_sounds if loaded_sounds else {}
        self.shuffle = shuffle
        self.search_term = ""
        self.highest_score_file = ""
        self.volume = self.settings_dict.get("default_volume", 100)

    def on_show_view(self):
        super().on_show_view()

        self.anchor = self.add_widget(arcade.gui.UIAnchorLayout(size_hint=(1, 1)))

        self.ui_box = self.anchor.add(arcade.gui.UIBoxLayout(size_hint=(1, 1), space_between=10))

        # Tabs

        self.load_content()
        if self.current_mode == "playlist" and not self.current_playlist:
            self.current_playlist = list(self.playlist_content.keys())[0] if self.playlist_content else None
        self.load_tabs()

        # Scrollable Sounds
        self.scroll_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(0.95, 0.8), space_between=15, vertical=False))

        self.scroll_area = UIScrollArea(size_hint=(0.9, 1)) # center on screen
        self.scroll_area.scroll_speed = -50
        self.scroll_box.add(self.scroll_area)

        self.scrollbar = UIScrollBar(self.scroll_area)
        self.scrollbar.size_hint = (0.02, 1)
        self.scroll_box.add(self.scrollbar)

        self.music_box = arcade.gui.UIBoxLayout(space_between=2)
        self.scroll_area.add(self.music_box)

        # Utility

        self.settings_box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=10), anchor_x="right", anchor_y="center", align_x=-10)

        self.new_tab_button = self.settings_box.add(UIFocusTextureButton(texture=plus_icon, texture_hovered=plus_icon, texture_pressed=plus_icon, style=button_style))
        self.new_tab_button.on_click = lambda event: self.new_tab()

        self.downloader_button = self.settings_box.add(UIFocusTextureButton(texture=download_icon, texture_hovered=download_icon, texture_pressed=download_icon, style=button_style))
        self.downloader_button.on_click = lambda event: self.downloader()

        self.reload_button = self.settings_box.add(UIFocusTextureButton(texture=reload_icon, texture_hovered=reload_icon, texture_pressed=reload_icon, style=button_style))
        self.reload_button.on_click = lambda event: self.reload()

        mode_icon = playlist_icon if self.current_mode == "files" else files_icon

        self.mode_button = self.settings_box.add(UIFocusTextureButton(texture=mode_icon, texture_hovered=mode_icon, texture_pressed=mode_icon, style=button_style))
        self.mode_button.on_click = lambda event: self.change_mode()

        self.settings_button = self.settings_box.add(UIFocusTextureButton(texture=settings_icon, style=button_style))
        self.settings_button.on_click = lambda event: self.settings()

        # Controls

        self.control_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(0.95, 0.1), space_between=10, vertical=False))
        self.current_music_label = self.control_box.add(arcade.gui.UILabel(text=truncate_end(self.current_music_name, int(self.window.width / 30)) if self.current_music_name else "No songs playing", font_name="Protest Strike", font_size=16))
        self.time_label = self.control_box.add(arcade.gui.UILabel(text="00:00", font_name="Protest Strike", font_size=16))

        self.progressbar = self.control_box.add(arcade.gui.UISlider(style=slider_style, width=self.window.width / 3, height=35))
        self.progressbar.on_change = self.on_progress_change

        self.pause_start_button = self.control_box.add(UIFocusTextureButton(texture=pause_icon if not self.current_music_player or self.current_music_player.playing else resume_icon))
        self.pause_start_button.on_click = lambda event: self.pause_start()

        self.skip_button = self.control_box.add(UIFocusTextureButton(texture=stop_icon))
        self.skip_button.on_click = lambda event: self.skip_sound()

        self.loop_button = self.control_box.add(UIFocusTextureButton(texture=no_loop_icon if not self.current_music_player or self.current_music_player.loop else loop_icon))
        self.loop_button.on_click = lambda event: self.loop_sound()

        self.shuffle_button = self.control_box.add(UIFocusTextureButton(texture=shuffle_icon))
        self.shuffle_button.on_click = lambda event: self.shuffle_sound()

        if self.current_music_player:
            self.progressbar.max_value = self.current_length
            self.volume = int(self.current_music_player.volume * 100)

        self.volume_label = self.control_box.add(arcade.gui.UILabel(text=f"{self.volume}%", font_name="Protest Strike", font_size=16))
        self.volume_slider = self.control_box.add(arcade.gui.UISlider(style=slider_style, width=self.window.width / 10, height=35, value=self.volume, max_value=100))
        self.volume_slider.on_change = self.on_volume_slider_change

        if self.current_mode == "files":
            self.show_content(os.path.expanduser(self.current_tab))
        elif self.current_mode == "playlist":
            self.show_content(self.current_playlist)

        arcade.schedule(self.update_presence, 2.5)

        self.update_presence(None)

    def update_buttons(self):
        if self.current_mode == "files":
            self.mode_button.texture = playlist_icon
            self.mode_button.texture_hovered = playlist_icon
            self.mode_button.texture_pressed = playlist_icon

        elif self.current_mode == "playlist":
            self.mode_button.texture = files_icon
            self.mode_button.texture_hovered = files_icon
            self.mode_button.texture_pressed = files_icon

        self.shuffle_button.texture = no_shuffle_icon if self.shuffle else shuffle_icon
        self.shuffle_button.texture_hovered = no_shuffle_icon if self.shuffle else shuffle_icon
        self.shuffle_button.texture_pressed = no_shuffle_icon if self.shuffle else shuffle_icon

        if self.current_music_player:
            self.pause_start_button.texture = pause_icon if self.current_music_player.playing else resume_icon
            self.pause_start_button.texture_hovered = pause_icon if self.current_music_player.playing else resume_icon
            self.pause_start_button.texture_pressed = pause_icon if self.current_music_player.playing else resume_icon

            self.loop_button.texture = no_loop_icon if self.current_music_player.loop else loop_icon
            self.loop_button.texture_hovered = no_loop_icon if self.current_music_player.loop else loop_icon
            self.loop_button.texture_pressed = no_loop_icon if self.current_music_player.loop else loop_icon
        else:
            self.pause_start_button.texture = pause_icon
            self.pause_start_button.texture_hovered = pause_icon
            self.pause_start_button.texture_pressed = pause_icon

            self.loop_button.texture = loop_icon
            self.loop_button.texture_hovered = loop_icon
            self.loop_button.texture_pressed = loop_icon

    def change_mode(self):
        self.current_mode = "playlist" if self.current_mode == "files" else "files"

        self.current_playlist = list(self.playlist_content.keys())[0] if self.playlist_content else None

        self.highest_score_file = ""
        self.search_term = ""

        self.reload()

    def skip_sound(self):
        if not self.current_music_player is None:
            if self.current_music_player.loop:
                self.current_music_player.seek(0)
                return

            if self.settings_dict.get("music_mode", "Streaming") == "Streaming":
                del self.loaded_sounds[self.current_music_name]

            self.current_length = 0
            self.current_music_name = None
            self.current_music_player.delete()
            self.current_music_player = None
            self.progressbar.value = 0
            self.current_music_label.text = "No songs playing"
            self.time_label.text = "00:00"

            self.update_buttons()

    def pause_start(self):
        if self.current_music_player is not None:
            self.current_music_player._set_playing(not self.current_music_player.playing)
            self.update_buttons()

    def loop_sound(self):
        if not self.current_music_player is None:
            self.current_music_player.loop = not self.current_music_player.loop
            self.update_buttons()

    def shuffle_sound(self):
        if not self.current_music_player is None:
            self.shuffle = not self.shuffle
            self.update_buttons()

    def show_content(self, tab):
        self.music_box.clear()
        self.music_buttons.clear()

        if self.current_mode == "files":
            self.current_tab = tab
            if not self.search_term == "":
                matches = process.extract(self.search_term, self.tab_content[self.current_tab], limit=5, processor=lambda text: text.lower(), scorer=fuzz.partial_token_sort_ratio)
                self.highest_score_file = f"{self.current_tab}/{matches[0][0]}"
                for match in matches:
                    music_filename = match[0]
                    self.music_buttons[music_filename] = self.music_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=music_filename, style=button_style, width=self.window.width * 0.85, height=self.window.height / 30))
                    self.music_buttons[music_filename].on_click = lambda event, tab=tab, music_filename=music_filename: self.queue.append(f"{tab}/{music_filename}")

            else:
                self.highest_score_file = ""
                for music_filename in self.tab_content[tab]:
                    self.music_buttons[music_filename] = self.music_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=music_filename, style=button_style, width=self.window.width * 0.85, height=self.window.height / 30))
                    self.music_buttons[music_filename].on_click = lambda event, tab=tab, music_filename=music_filename: self.queue.append(f"{tab}/{music_filename}")

        elif self.current_mode == "playlist":
            self.current_playlist = tab

            if self.current_playlist:
                if not self.search_term == "":
                    matches = process.extract(self.search_term, self.playlist_content[tab], limit=5, processor=lambda text: text.lower(), scorer=fuzz.partial_token_sort_ratio)
                    self.highest_score_file = matches[0][0]
                    for match in matches:
                        music_filename = match[0]
                        self.music_buttons[music_filename] = self.music_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=music_filename, style=button_style, width=self.window.width * 0.85, height=self.window.height / 30))
                        self.music_buttons[music_filename].on_click = lambda event, tab=tab, music_filename=music_filename: self.queue.append(music_filename)

                else:
                    self.highest_score_file = ""
                    for music_filename in self.playlist_content[tab]:
                        self.music_buttons[music_filename] = self.music_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=music_filename, style=button_style, width=self.window.width * 0.85, height=self.window.height / 30))
                        self.music_buttons[music_filename].on_click = lambda event, tab=tab, music_filename=music_filename: self.queue.append(music_filename)

                self.music_buttons["add_music"] = self.music_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text="Add Music", style=button_style, width=self.window.width * 0.85, height=self.window.height / 30))
                self.music_buttons["add_music"].on_click = lambda event: self.add_music()

        self.update_buttons()

    def load_content(self):
        self.tab_content.clear()
        self.playlist_content.clear()

        for tab in self.tab_options:
            self.tab_content[os.path.expanduser(tab)] = []
            for filename in os.listdir(os.path.expanduser(tab)):
                if filename.split(".")[-1] in audio_extensions:
                    self.tab_content[os.path.expanduser(tab)].append(filename)

        for playlist, content in self.settings_dict.get("playlists", {}).items():
            self.playlist_content[playlist] = content

    def load_tabs(self):
        self.tab_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(0.95, 0.1), space_between=10, vertical=False))

        if self.current_mode == "files":
            for tab in self.tab_options:
                self.tab_buttons[os.path.expanduser(tab)] = self.tab_box.add(UIFocusTextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=os.path.basename(os.path.normpath(os.path.expanduser(tab))), style=button_style, width=self.window.width / 10, height=self.window.height / 15))
                self.tab_buttons[os.path.expanduser(tab)].on_click = lambda event, tab=os.path.expanduser(tab): self.show_content(tab)
        elif self.current_mode == "playlist":
            for playlist in self.playlist_content:
                self.tab_buttons[playlist] = self.tab_box.add(UIFocusTextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=playlist, style=button_style, width=self.window.width / 10, height=self.window.height / 15))
                self.tab_buttons[playlist].on_click = lambda event, playlist=playlist: self.show_content(playlist)

    def on_progress_change(self, event):
        if not self.current_music_player is None:
            scale = self.progressbar.value / self.progressbar.max_value

            self.time_to_seek = self.current_length * scale

    def on_volume_slider_change(self, event):
        self.volume = int(self.volume_slider.value)
        self.volume_label.text = f"{self.volume}%"

        if not self.current_music_player is None:
            self.current_music_player.volume = self.volume / 100

    def on_update(self, delta_time):
        if self.current_music_player is None or self.current_music_player.time == 0:
            if len(self.queue) > 0:
                music_path = self.queue.pop(0)

                artist, title = extract_metadata(music_path)

                music_name = f"{artist} - {title}"

                if self.settings_dict.get("normalize_audio", True):
                    try:
                        audio = AudioSegment.from_file(music_path)

                        if int(audio.dBFS) != self.settings_dict.get("normalized_volume", -8):
                            change = self.settings_dict.get("normalized_volume", -8) - audio.dBFS
                            audio = audio.apply_gain(change)

                            audio.export(music_path, format="mp3")
                    except Exception as e:
                        logging.error(f"Couldn't normalize volume for {music_path}: {e}")

                if not music_name in self.loaded_sounds:
                    self.loaded_sounds[music_name] = arcade.Sound(music_path, streaming=self.settings_dict.get("music_mode", "Stream") == "Stream")

                self.volume = self.settings_dict.get("default_volume", 100)
                self.volume_label.text = f"{self.volume}%"
                self.volume_slider.value = self.volume

                self.current_music_player = self.loaded_sounds[music_name].play()
                self.current_music_player.volume = self.volume / 100
                self.current_length = self.loaded_sounds[music_name].get_length()

                self.current_music_name = music_name
                self.current_music_label.text = truncate_end(music_name, int(self.window.width / 25))
                self.time_label.text = "00:00"
                self.progressbar.max_value = self.current_length
                self.progressbar.value = 0

            else:
                if self.current_music_player is not None:
                    self.skip_sound() # reset properties

                if self.shuffle:
                    self.queue.append(f"{self.current_tab}/{random.choice(self.tab_content[self.current_tab])}")

        if not self.current_music_player is None:
            if self.time_to_seek is not None:
                self.current_music_player.seek(self.time_to_seek)
                self.progressbar.value = self.time_to_seek
                self.time_to_seek = None
            else:
                self.progressbar.value = self.current_music_player.time
                mins, secs = divmod(self.current_music_player.time, 60)
                self.time_label.text = f"{int(mins):02d}:{int(secs):02d}"

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        if symbol == arcade.key.SPACE:
            self.pause_start()
        elif symbol == arcade.key.DELETE:
            self.skip_sound()
        elif symbol == arcade.key.RIGHT and self.current_music_player:
            self.current_music_player.seek(self.current_music_player.time + 5)
        elif symbol == arcade.key.LEFT and self.current_music_player:
            self.current_music_player.seek(self.current_music_player.time - 5)
        elif symbol == arcade.key.UP and self.current_music_player:
            self.current_music_player.pitch += 0.1 # type: ignore
        elif symbol == arcade.key.DOWN and self.current_music_player:
            self.current_music_player.pitch -= 0.1 # type: ignore
        elif symbol == arcade.key.BACKSPACE:
            self.search_term = self.search_term[:-1]
            if self.current_mode == "files":
                self.show_content(self.current_tab)
            elif self.current_mode == "playlist":
                self.show_content(self.current_playlist)
        elif symbol == arcade.key.ENTER and self.highest_score_file:
            self.queue.append(self.highest_score_file)
            self.highest_score_file = ""
            self.search_term = ""
            if self.current_mode == "files":
                self.show_content(self.current_tab)
            elif self.current_mode == "playlist":
                self.show_content(self.current_playlist)
        elif symbol == arcade.key.ESCAPE:
            self.highest_score_file = ""
            self.search_term = ""
            if self.current_mode == "files":
                self.show_content(self.current_tab)
            elif self.current_mode == "playlist":
                self.show_content(self.current_playlist)

    def on_text(self, text):
        if not text.isprintable() or text == " ":
            return

        self.search_term += text

        if self.current_mode == "files":
            self.show_content(self.current_tab)
        elif self.current_mode == "playlist":
            self.show_content(self.current_playlist)

    def settings(self):
        from menus.settings import Settings
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(Settings(self.pypresence_client, self.current_mode, self.current_music_name, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def new_tab(self):
        from menus.new_tab import NewTab
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(NewTab(self.pypresence_client, self.current_mode, self.current_music_name, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def add_music(self):
        from menus.add_music import AddMusic
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(AddMusic(self.pypresence_client, self.current_mode, self.current_music_name, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def downloader(self):
        from menus.downloader import Downloader
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(Downloader(self.pypresence_client, self.current_mode, self.current_music_name, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def reload(self):
        self.ui.clear()
        self.on_show_view()
        self.update_buttons()

    def update_presence(self, _):
        if self.current_music_label.text != "No songs playing" and self.current_music_player:
            details = f"Listening to {self.current_music_name}"

            if self.current_music_player.playing:
                mins, secs = divmod(self.current_length, 60)
                state = f"{self.time_label.text} / {int(mins):02d}:{int(secs):02d}"
            else:
                state = "Paused"
        else:
            details = ""
            state = "No songs playing"

        self.pypresence_client.update(state=state, details=details, start=self.pypresence_client.start_time)
