import random, asyncio, pypresence, time, copy, json, os, logging
import arcade, pyglet

from utils.preload import *
from utils.constants import button_style, slider_style, audio_extensions, discord_presence_id, view_modes
from utils.utils import FakePyPresence, UIFocusTextureButton, MusicItem
from utils.music_handling import update_last_play_statistics, extract_metadata_and_thumbnail, adjust_volume, truncate_end
from utils.file_watching import watch_directories, watch_files

from thefuzz import process, fuzz

from arcade.gui.experimental.scroll_area import UIScrollArea, UIScrollBar
from arcade.gui.experimental.focus import UIFocusGroup

class Main(arcade.gui.UIView):
    def __init__(self, pypresence_client: None | FakePyPresence | pypresence.Presence=None, current_mode: str | None=None, current_music_artist: str | None=None,
                current_music_title: str | None=None, current_music_path: str | None=None, current_length: int | None=None,
                current_music_player: pyglet.media.Player | None=None, queue: list | None=None, loaded_sounds: dict | None=None, shuffle: bool=False):
        
        super().__init__()
        self.pypresence_client = pypresence_client

        with open("settings.json", "r", encoding="utf-8") as file:
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

        self.tab_options = self.settings_dict.get("tab_options", [os.path.join("~", "Music"), os.path.join("~", "Downloads")])
        self.tab_content = {}
        self.playlist_content = {}
        self.file_metadata = {}
        self.tab_buttons = {}
        self.music_buttons = {}
        self.queue = []

        self.current_music_artist = current_music_artist
        self.current_music_title = current_music_title
        self.current_music_player = current_music_player
        self.current_music_path = current_music_path
        self.current_length = current_length if current_length else 0
        self.shuffle = shuffle
        self.volume = self.settings_dict.get("default_volume", 100)

        self.current_mode = current_mode or "files"
        self.current_playlist = None
        self.current_tab = self.tab_options[0]
        self.search_term = ""
        self.highest_score_file = ""

        self.time_to_seek = None
        self.should_reload = False
        
        self.tab_observer = None
        self.playlist_observer = None
        
        self.loaded_sounds = loaded_sounds if loaded_sounds else {}

    def on_show_view(self):
        super().on_show_view()

        self.load_content()

        self.create_ui()
        
    def create_ui(self):
        self.anchor = self.add_widget(UIFocusGroup(size_hint=(1, 1)))

        self.ui_box = self.anchor.add(arcade.gui.UIBoxLayout(size_hint=(1, 1), space_between=10))

        # Tabs
        self.tab_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(0.95, 0.1), space_between=10, vertical=False))
        self.load_tabs()

        if self.current_mode == "playlist" and not self.current_playlist:
            self.current_playlist = list(self.playlist_content.keys())[0] if self.playlist_content else None

        # Scrollable Sounds
        self.scroll_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(0.95, 0.85), space_between=15, vertical=False))

        self.scroll_area = UIScrollArea(size_hint=(0.95, 1)) # center on screen
        self.scroll_area.scroll_speed = -50
        self.scroll_box.add(self.scroll_area)

        self.scrollbar = UIScrollBar(self.scroll_area)
        self.scrollbar.size_hint = (0.02, 1)
        self.scroll_box.add(self.scrollbar)

        self.music_box = arcade.gui.UIBoxLayout(space_between=5)
        self.scroll_area.add(self.music_box)

        # Utility

        self.settings_box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=10), anchor_x="right", anchor_y="center", align_x=-10)

        self.new_tab_button = self.settings_box.add(UIFocusTextureButton(texture=plus_icon, texture_hovered=plus_icon, texture_pressed=plus_icon, style=button_style))
        self.new_tab_button.on_click = lambda event: self.new_tab()

        self.downloader_button = self.settings_box.add(UIFocusTextureButton(texture=download_icon, texture_hovered=download_icon, texture_pressed=download_icon, style=button_style))
        self.downloader_button.on_click = lambda event: self.downloader()
        
        if self.current_mode == "files":
            mode_icon = files_icon
        elif self.current_mode == "playlist":
            mode_icon = playlist_icon

        self.mode_button = self.settings_box.add(UIFocusTextureButton(texture=mode_icon, texture_hovered=mode_icon, texture_pressed=mode_icon, style=button_style))
        self.mode_button.on_click = lambda event: self.change_mode()

        self.settings_button = self.settings_box.add(UIFocusTextureButton(texture=settings_icon, style=button_style))
        self.settings_button.on_click = lambda event: self.settings()

        # Controls

        self.now_playing_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(0.99, 0.075), space_between=10, vertical=False))
        
        self.current_music_thumbnail_image = self.now_playing_box.add(arcade.gui.UIImage(texture=music_icon, width=self.window.width / 25, height=self.window.height / 15))

        self.now_playing_box.add(arcade.gui.UISpace(width=10))

        # Artist - Title
        self.current_music_box = self.now_playing_box.add(arcade.gui.UIBoxLayout(space_between=10))
        self.current_music_title_label = self.current_music_box.add(arcade.gui.UILabel(text=truncate_end(self.current_music_title, int(self.window.width / 50)) if self.current_music_title else "No songs playing", font_name="Roboto", font_size=12))
        self.current_music_artist_label = self.current_music_box.add(arcade.gui.UILabel(text=truncate_end(self.current_music_artist, int(self.window.width / 50)) if self.current_music_artist else "No songs playing", font_name="Roboto", font_size=10, text_color=arcade.color.GRAY))

        self.now_playing_box.add(arcade.gui.UISpace(width=self.window.width / 16))

        # Time box with controls, progressbar and time
        self.current_time_box = self.now_playing_box.add(arcade.gui.UIBoxLayout(space_between=10))
        
        # Controls
        self.controls_box = self.current_time_box.add(arcade.gui.UIBoxLayout(space_between=25, vertical=False))
        
        self.shuffle_button = self.controls_box.add(UIFocusTextureButton(texture=shuffle_icon))
        self.shuffle_button.on_click = lambda event: self.shuffle_sound()
        
        self.previous_button = self.controls_box.add(UIFocusTextureButton(texture=backwards_icon))
        self.previous_button.on_click = lambda event: self.previous_track()

        self.pause_start_button = self.controls_box.add(UIFocusTextureButton(texture=pause_icon if not self.current_music_player or self.current_music_player.playing else resume_icon))
        self.pause_start_button.on_click = lambda event: self.pause_start()

        self.next_button = self.controls_box.add(UIFocusTextureButton(texture=forward_icon))
        self.next_button.on_click = lambda event: self.next_track()

        self.loop_button = self.controls_box.add(UIFocusTextureButton(texture=no_loop_icon if self.current_music_player and self.current_music_player.loop else loop_icon))
        self.loop_button.on_click = lambda event: self.loop_sound()

        # Time - Progressbar - Full Length
        self.progressbar_box = self.current_time_box.add(arcade.gui.UIBoxLayout(vertical=False, space_between=10))

        self.time_label = self.progressbar_box.add(arcade.gui.UILabel(text="00:00", font_name="Roboto", font_size=13))

        self.progressbar = self.progressbar_box.add(arcade.gui.UISlider(style=slider_style, width=self.window.width / 3, height=self.window.height / 45))
        self.progressbar.on_change = self.on_progress_change

        self.full_length_label = self.progressbar_box.add(arcade.gui.UILabel(text="00:00", font_name="Roboto", font_size=13))

        if self.current_music_player:
            self.progressbar.max_value = self.current_length
            self.volume = int(self.current_music_player.volume * 100)

        self.now_playing_box.add(arcade.gui.UISpace(width=self.window.width / 16))

        self.volume_icon_label = self.now_playing_box.add(arcade.gui.UIImage(texture=volume_icon))
        self.volume_slider = self.now_playing_box.add(arcade.gui.UISlider(style=slider_style, width=self.window.width / 10, height=35, value=self.volume, max_value=100))
        self.volume_slider.on_change = self.on_volume_slider_change

        self.no_music_label = self.anchor.add(arcade.gui.UILabel(text="No music files were found in this directory or playlist.", font_name="Roboto", font_size=24), anchor_x="center", anchor_y="center")
        self.no_music_label.visible = False

        self.no_playlists_label = self.anchor.add(arcade.gui.UILabel(text="You have no playlists.", font_name="Roboto", font_size=24))
        self.no_playlists_label.visible = False

        if self.current_mode == "files":
            self.show_content(os.path.expanduser(self.current_tab))
        elif self.current_mode == "playlist":
            self.show_content(self.current_playlist)

        arcade.schedule(self.update_presence, 3)

        self.update_presence(None)

    def update_buttons(self):
        if self.current_mode == "files":
            mode_icon = files_icon
        elif self.current_mode == "playlist":
            mode_icon = playlist_icon

        self.mode_button.texture = mode_icon
        self.mode_button.texture_hovered = mode_icon
        self.mode_button.texture_pressed = mode_icon

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

        self.anchor.detect_focusable_widgets()

    def change_mode(self):
        if view_modes.index(self.current_mode) == len(view_modes) - 1:
            self.current_mode = view_modes[0]
        else:
            self.current_mode = view_modes[view_modes.index(self.current_mode) + 1]

        self.current_playlist = list(self.playlist_content.keys())[0] if self.playlist_content else None

        self.highest_score_file = ""
        self.search_term = ""

        self.reload()
        self.load_tabs()
        self.update_buttons()

    def previous_track(self):
        if not self.current_music_player is None:
            if self.current_mode == "files":
                if os.path.basename(self.current_music_path) in self.tab_content[self.current_tab]:
                    current_idx = self.tab_content[self.current_tab].index(os.path.basename(self.current_music_path))
                    self.queue.append(f"{self.current_tab}/{self.tab_content[self.current_tab][current_idx - 1]}")
            elif self.current_mode == "playlist":
                if os.path.basename(self.current_music_path) in self.playlist_content[self.current_playlist]:
                    current_idx = self.playlist_content[self.current_playlist].index(os.path.basename(self.current_music_path))
                    self.queue.append(f"{self.current_playlist}/{self.playlist_content[self.current_playlist][current_idx - 1]}")

            self.skip_sound()
        
    def next_track(self):
        if not self.current_music_player is None:
            if self.current_mode == "files":
                if os.path.basename(self.current_music_path) in self.tab_content[self.current_tab]:
                    current_idx = self.tab_content[self.current_tab].index(os.path.basename(self.current_music_path))
                    self.queue.append(f"{self.current_tab}/{self.tab_content[self.current_tab][current_idx + 1]}")
            elif self.current_mode == "playlist":
                if os.path.basename(self.current_music_path) in self.playlist_content[self.current_playlist]:
                    current_idx = self.playlist_content[self.current_playlist].index(os.path.basename(self.current_music_path))
                    self.queue.append(f"{self.current_playlist}/{self.playlist_content[self.current_playlist][current_idx + 1]}")

            self.skip_sound()

    def skip_sound(self):
        if not self.current_music_player is None:
            if self.current_music_player.loop:
                self.current_music_player.seek(0)
                return

            if self.settings_dict.get("music_mode", "Streaming") == "Streaming":
                del self.loaded_sounds[self.current_music_path]

            self.current_length = 0
            self.current_music_artist = None
            self.current_music_title = None
            self.current_music_player.delete()
            self.current_music_player = None
            self.current_music_path = None
            self.progressbar.value = 0
            self.current_music_thumbnail_image.texture = music_icon
            self.current_music_title_label.text = "No songs playing"
            self.full_length_label.text = "00:00"
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

    def view_metadata(self, file_path):
        from menus.metadata_viewer import MetadataViewer
        self.window.show_view(MetadataViewer(self.pypresence_client, "music", self.file_metadata[file_path], file_path, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def show_content(self, tab):
        for music_button in self.music_buttons.values():
            music_button.clear()
            self.music_box.remove(music_button)
            del music_button

        self.music_box.clear()
        self.music_buttons.clear()

        if self.current_mode == "files":
            self.current_tab = tab
            if not self.search_term == "":
                matches = process.extract(self.search_term, self.tab_content[self.current_tab], limit=5, processor=lambda text: text.lower(), scorer=fuzz.partial_token_sort_ratio)
                self.highest_score_file = f"{self.current_tab}/{matches[0][0]}"
                content_to_show = [match[0] for match in matches]

            else:
                self.highest_score_file = ""
                self.no_music_label.visible = not self.tab_content[tab]
                content_to_show = self.tab_content[tab]

            for music_filename in content_to_show:
                metadata = self.file_metadata[f"{tab}/{music_filename}"]
                
                self.music_buttons[f"{tab}/{music_filename}"] = self.music_box.add(MusicItem(metadata=metadata, width=self.window.width / 1.2, height=self.window.height / 22))
                self.music_buttons[f"{tab}/{music_filename}"].button.on_click = lambda event, music_path=f"{tab}/{music_filename}": self.music_button_click(event, music_path)
                self.music_buttons[f"{tab}/{music_filename}"].view_metadata_button.on_click = lambda event, music_path=f"{tab}/{music_filename}": self.view_metadata(music_path)

        elif self.current_mode == "playlist":
            self.current_playlist = tab

            if self.current_playlist:
                if not self.search_term == "":
                    matches = process.extract(self.search_term, self.playlist_content[tab], limit=5, processor=lambda text: text.lower(), scorer=fuzz.partial_token_sort_ratio)
                    self.highest_score_file = matches[0][0]
                    content_to_show = [match[0] for match in matches]

                else:
                    self.highest_score_file = ""
                    self.no_music_label.visible = not self.playlist_content[tab]
                    content_to_show = self.playlist_content[tab]

                for music_path in content_to_show:
                    metadata = self.file_metadata[music_path]
                    self.music_buttons[music_path] = self.music_box.add(MusicItem(metadata=metadata, width=self.window.width / 1.2, height=self.window.height / 22))
                    self.music_buttons[music_path].button.on_click = lambda event, music_path=music_path: self.music_button_click(event, music_path)
                    self.music_buttons[music_path].view_metadata_button.on_click = lambda event, music_path=music_path: self.view_metadata(music_path)

                self.music_buttons["add_music"] = self.music_box.add(MusicItem(metadata=None, width=self.window.width / 1.2, height=self.window.height / 22))
                self.music_buttons["add_music"].button.on_click = lambda event: self.add_music()

        self.anchor.detect_focusable_widgets()

    def music_button_click(self, event, music_path):
        if event.button == arcade.MOUSE_BUTTON_LEFT:
            self.queue.append(music_path)
        elif event.button == arcade.MOUSE_BUTTON_RIGHT:
            if self.current_mode == "files":
                os.remove(music_path)
            elif self.current_mode == "playlist":
                self.settings_dict["playlists"][self.current_playlist].remove(music_path)

                with open("settings.json", "w") as file:
                    file.write(json.dumps(self.settings_dict, indent=4))

            self.window.show_view(Main(self.pypresence_client, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, # temporarily fixes the issue of bad resolution after deletion with less than 2 rows
                                       self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))
            
    def load_content(self):
        self.tab_content.clear()
        self.playlist_content.clear()
        self.file_metadata.clear()
        
        for tab in self.tab_options:
            expanded_tab = os.path.expanduser(tab)

            if not os.path.exists(expanded_tab) or not os.path.isdir(expanded_tab):
                self.tab_options.remove(tab)
                continue
                    
            self.tab_content[expanded_tab] = []

            for filename in os.listdir(expanded_tab):
                if filename.split(".")[-1] in audio_extensions:
                    if f"{expanded_tab}/{filename}" not in self.file_metadata:
                        self.file_metadata[f"{expanded_tab}/{filename}"] = extract_metadata_and_thumbnail(f"{expanded_tab}/{filename}", (int(self.window.width / 16), int(self.window.height / 9)))
                    self.tab_content[expanded_tab].append(filename)

        if self.tab_observer:
            self.tab_observer.stop()
        self.tab_observer = watch_directories(self.tab_content.keys(), self.on_file_change)

        playlist_files = []
        for playlist, content in self.settings_dict.get("playlists", {}).items():
            for file in content:
                playlist_files.append(file)

                if not os.path.exists(file) or not os.path.isfile(file):
                    content.remove(file) # also removes reference from self.settings_dict["playlists"]
                    continue
                
                if file not in self.file_metadata:
                    self.file_metadata[file] = extract_metadata_and_thumbnail(file, (int(self.window.width / 16), int(self.window.height / 9)))
            self.playlist_content[playlist] = content

        if self.playlist_observer:
            self.playlist_observer.stop()
        self.playlist_observer = watch_files(playlist_files, self.on_file_change)

    def on_file_change(self, event_type, path):
        self.should_reload = True # needed because the observer runs in another thread and OpenGL is single-threaded.

    def load_tabs(self):
        for button in self.tab_buttons.values():
            self.tab_box.remove(button)
        self.tab_buttons.clear()

        if self.current_mode == "files":
            for tab in self.tab_options:
                self.tab_buttons[os.path.expanduser(tab)] = self.tab_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=os.path.basename(os.path.normpath(os.path.expanduser(tab))), style=button_style, width=self.window.width / 10, height=self.window.height / 15))
                self.tab_buttons[os.path.expanduser(tab)].on_click = lambda event, tab=os.path.expanduser(tab): self.show_content(os.path.expanduser(tab))
        elif self.current_mode == "playlist":
            for playlist in self.playlist_content:
                self.tab_buttons[playlist] = self.tab_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=playlist, style=button_style, width=self.window.width / 10, height=self.window.height / 15))
                self.tab_buttons[playlist].on_click = lambda event, playlist=playlist: self.show_content(playlist)

    def on_progress_change(self, event):
        if not self.current_music_player is None:
            scale = self.progressbar.value / self.progressbar.max_value

            self.time_to_seek = self.current_length * scale

    def on_volume_slider_change(self, event):
        self.volume = int(self.volume_slider.value)

        if not self.current_music_player is None:
            self.current_music_player.volume = self.volume / 100

    def on_update(self, delta_time):
        if self.should_reload:
            self.should_reload = False
            self.reload()

        if self.current_music_player is None or self.current_music_player.time == 0:
            if len(self.queue) > 0:
                music_path = self.queue.pop(0)

                artist, title = self.file_metadata[music_path]["artist"], self.file_metadata[music_path]["title"]

                if self.settings_dict.get("normalize_audio", True):
                    self.current_music_title_label.text = "Normalizing audio..."
                    self.window.draw(delta_time) # draw before blocking
                    try:
                        adjust_volume(music_path, self.settings_dict.get("normalized_volume", -8))
                    except Exception as e:
                        logging.error(f"Couldn't normalize volume for {music_path}: {e}")

                update_last_play_statistics(music_path)

                if not music_path in self.loaded_sounds:
                    self.loaded_sounds[music_path] = arcade.Sound(music_path, streaming=self.settings_dict.get("music_mode", "Stream") == "Stream")

                self.volume = self.settings_dict.get("default_volume", 100)
                self.volume_slider.value = self.volume

                self.current_music_player = self.loaded_sounds[music_path].play()
                self.current_music_player.volume = self.volume / 100
                self.current_length = self.loaded_sounds[music_path].get_length()

                self.current_music_artist = artist
                self.current_music_title = title
                self.current_music_title_label.text = title
                self.current_music_artist_label.text = artist
                self.current_music_path = music_path
                self.current_music_thumbnail_image.texture = self.file_metadata[music_path]["thumbnail"]
                self.time_label.text = "00:00"
                self.full_length_label.text = "00:00"
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
                mins, secs = divmod(self.current_length, 60)
                self.full_length_label.text = f"{int(mins):02d}:{int(secs):02d}"

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        if symbol == arcade.key.SPACE:
            self.pause_start()
        elif symbol == arcade.key.DELETE:
            self.skip_sound()
        elif symbol == arcade.key.RIGHT and self.current_music_player:
            self.current_music_player.seek(self.current_music_player.time + 5)
        elif symbol == arcade.key.LEFT and self.current_music_player:
            self.current_music_player.seek(self.current_music_player.time - 5)
        elif symbol == arcade.key.BACKSPACE:
            self.search_term = self.search_term[:-1]
            if self.current_mode == "files":
                self.show_content(os.path.expanduser(self.current_tab))
            elif self.current_mode == "playlist":
                self.show_content(self.current_playlist)
        elif symbol == arcade.key.ENTER and self.highest_score_file:
            self.queue.append(self.highest_score_file)
            self.highest_score_file = ""
            self.search_term = ""
            if self.current_mode == "files":
                self.show_content(os.path.expanduser(self.current_tab))
            elif self.current_mode == "playlist":
                self.show_content(self.current_playlist)
        elif symbol == arcade.key.ESCAPE:
            self.highest_score_file = ""
            self.search_term = ""
            if self.current_mode == "files":
                self.show_content(os.path.expanduser(self.current_tab))
            elif self.current_mode == "playlist":
                self.show_content(self.current_playlist)

    def on_button_press(self, controller, name):
        if name == "start":
            self.pause_start()
        elif name == "b":
            self.skip_sound()

    def on_text(self, text):
        if not text.isprintable() or text == " ":
            return

        self.search_term += text

        if self.current_mode == "files":
            self.show_content(os.path.expanduser(self.current_tab))
        elif self.current_mode == "playlist":
            self.show_content(self.current_playlist)

    def settings(self):
        from menus.settings import Settings
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(Settings(self.pypresence_client, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def new_tab(self):
        from menus.new_tab import NewTab
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(NewTab(self.pypresence_client, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def add_music(self):
        from menus.add_music import AddMusic
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(AddMusic(self.pypresence_client, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def downloader(self):
        from menus.downloader import Downloader
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(Downloader(self.pypresence_client, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def reload(self):
        self.load_content()

        self.no_playlists_label.visible = not self.playlist_content

        if self.current_mode == "files":
            self.show_content(os.path.expanduser(self.current_tab))
        elif self.current_mode == "playlist":
            self.show_content(self.current_playlist)

        self.anchor.detect_focusable_widgets()

    def update_presence(self, _):
        if self.current_music_title != "No songs playing" and self.current_music_player:
            details = f"Listening to {self.current_music_artist} - {self.current_music_title}"

            if self.current_music_player.playing:
                mins, secs = divmod(self.current_length, 60)
                state = f"{self.time_label.text} / {int(mins):02d}:{int(secs):02d}"
            else:
                state = "Paused"
        else:
            details = ""
            state = "No songs playing"

        self.pypresence_client.update(state=state, details=details, start=self.pypresence_client.start_time)
