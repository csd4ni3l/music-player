import random, asyncio, pypresence, time, copy, json, os, logging
import arcade, pyglet

from utils.preload import *
from utils.constants import button_style, slider_style, audio_extensions, discord_presence_id
from utils.utils import FakePyPresence, UIFocusTextureButton, Card, MouseAwareScrollArea, get_wordwrapped_text
from utils.music_handling import update_last_play_statistics, extract_metadata_and_thumbnail, adjust_volume, truncate_end
from utils.file_watching import watch_directories, watch_files
from utils.lyrics_metadata import get_lyrics, get_closest_time, parse_synchronized_lyrics

from thefuzz import process, fuzz

from arcade.gui.experimental.scroll_area import UIScrollBar
from arcade.gui.experimental.focus import UIFocusGroup

class Main(arcade.gui.UIView):
    def __init__(self, pypresence_client: None | FakePyPresence | pypresence.Presence=None, current_tab: str | None=None, current_mode: str | None=None, current_music_artist: str | None=None,
                current_music_title: str | None=None, current_music_path: str | None=None, current_length: int | None=None,
                current_music_player: pyglet.media.Player | None=None, current_synchronized_lyrics: str | None=None, queue: list | None=None, loaded_sounds: dict | None=None, shuffle: bool=False):
        
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
        self.queue = queue or []

        self.current_music_artist = current_music_artist
        self.current_music_title = current_music_title
        self.current_music_player = current_music_player
        self.current_music_path = current_music_path
        self.current_length = current_length if current_length else 0
        self.current_synchronized_lyrics = current_synchronized_lyrics if current_synchronized_lyrics else None
        self.shuffle = shuffle
        self.volume = self.settings_dict.get("default_volume", 100)

        self.lyrics_times, self.parsed_lyrics = parse_synchronized_lyrics(self.current_synchronized_lyrics) if self.current_synchronized_lyrics else (None, None)

        self.current_mode = current_mode if current_mode else "files"
        self.current_tab = current_tab if current_tab else self.tab_options[0]
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

        self.ui_box = self.anchor.add(arcade.gui.UIBoxLayout(size_hint=(1, 0.97), space_between=5, vertical=False))

        self.ui_box.add(arcade.gui.UISpace(width=5))

        # Tabs
        self.tab_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(0.05, 1), space_between=10, align="center"))
        self.load_tabs()

        self.ui_box.add(arcade.gui.UISpace(width=5))

        self.content_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(0.915, 1), space_between=10))

        self.search_bar = self.content_box.add(arcade.gui.UIInputText(size_hint=(0.5, 0.04), font_size=14))
        self.search_bar.on_change = lambda e: self.search()

        if self.current_mode == "playlist" and not self.current_tab:
            self.current_tab = list(self.playlist_content.keys())[0] if self.playlist_content else None

        # Scrollable Sounds and Lyrics
        self.scroll_box = self.content_box.add(arcade.gui.UIBoxLayout(size_hint=(1, 0.90), space_between=15, vertical=False))

        self.scroll_area = MouseAwareScrollArea(size_hint=(0.8, 1)) # center on screen
        self.scroll_area.scroll_speed = -50
        self.scroll_box.add(self.scroll_area)

        self.scrollbar = UIScrollBar(self.scroll_area)
        self.scrollbar.size_hint = (0.02, 1)
        self.scroll_box.add(self.scrollbar)

        self.music_grid = arcade.gui.UIGridLayout(horizontal_spacing=10, vertical_spacing=10, row_count=99, column_count=6)
        self.scroll_area.add(self.music_grid)

        self.lyrics_box = self.scroll_box.add(arcade.gui.UIBoxLayout(space_between=5, size_hint=(0.25, 1), align="left"))

        self.current_lyrics_label = arcade.gui.UILabel(size_hint=(0.2, 0.05), width=self.window.width * 0.2, multiline=True, font_size=16, font_name="Roboto", text_color=arcade.color.WHITE, text=self.current_synchronized_lyrics if self.current_synchronized_lyrics else "Play a song to get lyrics.")
        self.lyrics_box.add(self.current_lyrics_label)

        self.next_lyrics_label = arcade.gui.UILabel(size_hint=(0.2, 0.95), width=self.window.width * 0.2, multiline=True, font_size=16, font_name="Roboto", text_color=arcade.color.GRAY, text=self.current_synchronized_lyrics if self.current_synchronized_lyrics else "Play a song to get lyrics.")
        self.lyrics_box.add(self.next_lyrics_label)

        # Controls

        self.now_playing_box = self.content_box.add(arcade.gui.UIBoxLayout(size_hint=(0.99, 0.075), space_between=10, vertical=False))
        
        self.current_music_thumbnail_image = self.now_playing_box.add(arcade.gui.UIImage(texture=music_icon, width=self.window.width / 25, height=self.window.height / 15))

        self.now_playing_box.add(arcade.gui.UISpace(width=10))

        # Artist - Title
        self.current_music_box = self.now_playing_box.add(arcade.gui.UIBoxLayout(space_between=10))
        self.current_music_title_label = self.current_music_box.add(arcade.gui.UILabel(text=truncate_end(self.current_music_title, int(self.window.width / 50)) if self.current_music_title else "No songs playing", font_name="Roboto", font_size=12))
        self.current_music_artist_label = self.current_music_box.add(arcade.gui.UILabel(text=truncate_end(self.current_music_artist, int(self.window.width / 50)) if self.current_music_artist else "No songs playing", font_name="Roboto", font_size=10, text_color=arcade.color.GRAY))

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

        self.progressbar = self.progressbar_box.add(arcade.gui.UISlider(style=slider_style, width=self.window.width / 4, height=self.window.height / 45))
        self.progressbar.on_change = self.on_progress_change

        self.full_length_label = self.progressbar_box.add(arcade.gui.UILabel(text="00:00", font_name="Roboto", font_size=13))

        if self.current_music_player:
            self.progressbar.max_value = self.current_length
            self.volume = int(self.current_music_player.volume * 100)

        self.volume_icon_label = self.now_playing_box.add(arcade.gui.UIImage(texture=volume_icon))
        self.volume_slider = self.now_playing_box.add(arcade.gui.UISlider(style=slider_style, width=self.window.width / 10, height=35, value=self.volume, max_value=100))
        self.volume_slider.on_change = self.on_volume_slider_change

        self.tools_box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=15, vertical=False), anchor_x="right", anchor_y="bottom", align_x=-15, align_y=15)

        self.global_search_button = self.tools_box.add(UIFocusTextureButton(texture=global_search_icon, style=button_style))
        self.global_search_button.on_click = lambda event: self.global_search()

        self.metadata_button = self.tools_box.add(UIFocusTextureButton(texture=metadata_icon, style=button_style))
        self.metadata_button.on_click = lambda event: self.view_metadata(self.current_music_path) if self.current_music_path else None

        self.downloader_button = self.tools_box.add(UIFocusTextureButton(texture=download_icon, style=button_style))
        self.downloader_button.on_click = lambda event: self.downloader()

        self.settings_button = self.tools_box.add(UIFocusTextureButton(texture=settings_icon, style=button_style), anchor_x="right", anchor_y="bottom", align_x=-15, align_y=15)
        self.settings_button.on_click = lambda event: self.settings()

        self.no_music_label = self.anchor.add(arcade.gui.UILabel(text="No music files were found in this directory or playlist.", font_name="Roboto", font_size=24), anchor_x="center", anchor_y="center", align_x=-self.window.width * 0.1)
        self.no_music_label.visible = False

        if self.current_mode == "files":
            self.show_content(os.path.expanduser(self.current_tab), "files")
        elif self.current_mode == "playlist":
            self.show_content(self.current_tab, "playlist")

        arcade.schedule(self.update_presence, 3)

        self.update_presence(None)

    def update_buttons(self):
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

    def previous_track(self):
        if not self.current_music_player is None:
            if self.current_mode == "files":
                if os.path.basename(self.current_music_path) in self.tab_content[self.current_tab]:
                    current_idx = self.tab_content[self.current_tab].index(os.path.basename(self.current_music_path))
                    self.queue.append(f"{self.current_tab}/{self.tab_content[self.current_tab][current_idx - 1]}")
            elif self.current_mode == "playlist":
                if os.path.basename(self.current_music_path) in self.playlist_content[self.current_tab]:
                    current_idx = self.playlist_content[self.current_tab].index(os.path.basename(self.current_music_path))
                    self.queue.append(f"{self.current_tab}/{self.playlist_content[self.current_tab][current_idx - 1]}")

            self.skip_sound()
        
    def next_track(self):
        if not self.current_music_player is None:
            if self.current_mode == "files":
                if os.path.basename(self.current_music_path) in self.tab_content[self.current_tab]:
                    current_idx = self.tab_content[self.current_tab].index(os.path.basename(self.current_music_path))
                    self.queue.append(f"{self.current_tab}/{self.tab_content[self.current_tab][current_idx + 1]}")
            elif self.current_mode == "playlist":
                if os.path.basename(self.current_music_path) in self.playlist_content[self.current_tab]:
                    current_idx = self.playlist_content[self.current_tab].index(os.path.basename(self.current_music_path))
                    self.queue.append(f"{self.current_tab}/{self.playlist_content[self.current_tab][current_idx + 1]}")

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
            self.current_synchronized_lyrics = None
            self.lyrics_times = None
            self.parsed_lyrics = None
            self.current_lyrics_label.text = "Play a song to get lyrics."
            self.next_lyrics_label.text = "Play a song to get lyrics."
            self.current_music_artist_label.text = "No songs playing"
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
        self.window.show_view(MetadataViewer(self.pypresence_client, "file", self.file_metadata[file_path], file_path, self.current_tab, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.current_synchronized_lyrics, self.queue, self.loaded_sounds, self.shuffle))

    def show_content(self, tab, content_type):
        for music_button in self.music_buttons.values():
            music_button.clear()
            self.music_grid.remove(music_button)
            del music_button

        self.music_grid.clear()
        self.music_buttons.clear()

        self.current_tab = tab
        self.current_mode = content_type

        original_content = self.tab_content[tab] if self.current_mode == "files" else self.playlist_content[tab]

        if not self.search_term == "":
            matches = process.extract(self.search_term, original_content, limit=5, processor=lambda text: text.lower(), scorer=fuzz.partial_token_sort_ratio)
            if matches:
                self.highest_score_file = f"{self.current_tab}/{matches[0][0]}"
                content_to_show = [match[0] for match in matches]
            else:
                self.highest_score_file = ""
                content_to_show = []

        else:
            self.highest_score_file = ""
            self.no_music_label.visible = not original_content
            content_to_show = original_content

        n = 0
        row, col = 0, 0

        for n, music_filename in enumerate(content_to_show):
            row = n // self.music_grid.column_count
            col = n % self.music_grid.column_count

            if self.current_mode == "files":
                music_path = f"{tab}/{music_filename}"
            else:
                music_path = music_filename

            metadata = self.file_metadata[music_path]
            
            self.music_buttons[music_path] = self.music_grid.add(Card(metadata["thumbnail"], get_wordwrapped_text(metadata["title"]), get_wordwrapped_text(metadata["artist"]), width=self.window.width / (self.music_grid.column_count + 1), height=self.window.width / (self.music_grid.column_count + 1)), row=row, column=col)
            self.music_buttons[music_path].button.on_click = lambda event, music_path=music_path: self.music_button_click(event, music_path)

        row = (n + 1) // self.music_grid.column_count
        col = (n + 1) % self.music_grid.column_count

        self.music_grid.row_count = row + 1
        self.music_grid._update_size_hints()

        if self.current_mode == "playlist":
            self.music_buttons["add_music"] = self.music_grid.add(Card(music_icon, "Add Music", None, width=self.window.width / (self.music_grid.column_count + 1), height=self.window.width / (self.music_grid.column_count + 1)), row=row, column=col)
            self.music_buttons["add_music"].button.on_click = lambda event: self.add_music()

        self.anchor.detect_focusable_widgets()

    def music_button_click(self, event, music_path):
        if event.button == arcade.MOUSE_BUTTON_LEFT:
            self.queue.append(music_path)
        elif event.button == arcade.MOUSE_BUTTON_RIGHT:
            if self.current_mode == "files":
                os.remove(music_path)
            elif self.current_mode == "playlist":
                self.settings_dict["playlists"][self.current_tab].remove(music_path)

                with open("settings.json", "w") as file:
                    file.write(json.dumps(self.settings_dict, indent=4))

            self.window.show_view(Main(self.pypresence_client, self.current_tab, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.current_synchronized_lyrics, self.queue, self.loaded_sounds, self.shuffle))
            
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
        for tab in self.tab_options:
            self.tab_buttons[os.path.expanduser(tab)] = self.tab_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=os.path.basename(os.path.normpath(os.path.expanduser(tab))), style=button_style, width=self.window.width / 15, height=self.window.height / 15))
            self.tab_buttons[os.path.expanduser(tab)].on_click = lambda event, tab=os.path.expanduser(tab): self.show_content(os.path.expanduser(tab), "files")
        
        for playlist in self.playlist_content:
            self.tab_buttons[playlist] = self.tab_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=playlist, style=button_style, width=self.window.width / 15, height=self.window.height / 15))
            self.tab_buttons[playlist].on_click = lambda event, playlist=playlist: self.show_content(playlist, "playlist")

        self.new_tab_button = self.tab_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, style=button_style, text="Add Tab", width=self.window.width / 15, height=self.window.height / 15))
        self.new_tab_button.on_click = lambda event: self.new_tab()

    def on_progress_change(self, event):
        if not self.current_music_player is None:
            scale = self.progressbar.value / self.progressbar.max_value

            self.time_to_seek = self.current_length * scale

    def on_volume_slider_change(self, event):
        self.volume = int(self.volume_slider.value)

        if not self.current_music_player is None:
            self.current_music_player.volume = self.volume / 100

    def on_update(self, delta_time):
        if self.current_synchronized_lyrics:
            closest_lyrics_time = get_closest_time(self.current_music_player.time, self.lyrics_times)
            self.current_lyrics_label.text = self.parsed_lyrics.get(closest_lyrics_time, '[Music]') or '[Music]'
            self.current_lyrics_label.fit_content()

            if closest_lyrics_time in self.lyrics_times:
                next_lyrics_times = self.lyrics_times[self.lyrics_times.index(closest_lyrics_time) + 1:self.lyrics_times.index(closest_lyrics_time) + 11]
                self.next_lyrics_label.text = '\n'.join([self.parsed_lyrics[next_lyrics_time] for next_lyrics_time in next_lyrics_times])
            else:
                self.next_lyrics_label.text = '\n'.join(list(self.parsed_lyrics.values())[0:10])
            self.next_lyrics_label.fit_content()

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

                self.current_music_artist = artist
                self.current_music_title = title
                self.current_music_title_label.text = title
                self.current_music_artist_label.text = artist
                self.current_music_path = music_path
                self.current_music_thumbnail_image.texture = self.file_metadata[music_path]["thumbnail"]
                self.time_label.text = "00:00"
                self.full_length_label.text = "00:00"
                self.current_synchronized_lyrics = get_lyrics(self.current_music_artist, self.current_music_title)[1]
                self.lyrics_times, self.parsed_lyrics = parse_synchronized_lyrics(self.current_synchronized_lyrics) if self.current_synchronized_lyrics else (None, None)

                if not self.current_synchronized_lyrics:
                    self.current_lyrics_label.text = "No known lyrics found"
                    self.next_lyrics_label.text = "No known lyrics found"

                if not music_path in self.loaded_sounds:
                    self.loaded_sounds[music_path] = arcade.Sound(music_path, streaming=self.settings_dict.get("music_mode", "Stream") == "Stream")

                self.volume = self.settings_dict.get("default_volume", 100)
                self.volume_slider.value = self.volume
                self.current_music_player = self.loaded_sounds[music_path].play()
                self.current_music_player.volume = self.volume / 100
                self.current_length = self.loaded_sounds[music_path].get_length()
                self.progressbar.max_value = self.current_length
                self.progressbar.value = 0
            else:
                if self.current_music_player is not None:
                    self.skip_sound() # reset properties

                if self.shuffle:
                    if self.current_mode == "files":
                        self.queue.append(f"{self.current_tab}/{random.choice(self.tab_content[self.current_tab])}")
                    elif self.current_mode == "playlist":
                        self.queue.append(random.choice(self.playlist_content[self.current_tab]))

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
        elif symbol == arcade.key.ENTER and self.highest_score_file:
            self.queue.append(self.highest_score_file)
            self.highest_score_file = ""
            self.search_term = ""
            self.search_bar.text = ""
            if self.current_mode == "files":
                self.show_content(os.path.expanduser(self.current_tab), "files")
            elif self.current_mode == "playlist":
                self.show_content(self.current_tab, "playlist")
        elif symbol == arcade.key.ESCAPE:
            self.highest_score_file = ""
            self.search_term = ""
            self.search_bar.text = ""
            if self.current_mode == "files":
                self.show_content(os.path.expanduser(self.current_tab), "files")
            elif self.current_mode == "playlist":
                self.show_content(self.current_tab, "playlist")

    def on_button_press(self, controller, name):
        if name == "start":
            self.pause_start()
        elif name == "b":
            self.skip_sound()

    def search(self):
        self.search_term = self.search_bar.text

        if self.current_mode == "files":
            self.show_content(os.path.expanduser(self.current_tab), "files")
        elif self.current_mode == "playlist":
            self.show_content(self.current_tab, "playlist")

    def global_search(self):
        from menus.global_search import GlobalSearch
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(GlobalSearch(self.pypresence_client, self.current_tab, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.current_synchronized_lyrics, self.queue, self.loaded_sounds, self.shuffle))

    def settings(self):
        from menus.settings import Settings
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(Settings(self.pypresence_client, self.current_tab, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.current_synchronized_lyrics, self.queue, self.loaded_sounds, self.shuffle))

    def new_tab(self):
        from menus.new_tab import NewTab
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(NewTab(self.pypresence_client, self.current_tab, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.current_synchronized_lyrics, self.queue, self.loaded_sounds, self.shuffle))

    def add_music(self):
        from menus.add_music import AddMusic
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(AddMusic(self.pypresence_client, self.current_tab, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.current_synchronized_lyrics, self.queue, self.loaded_sounds, self.shuffle))

    def downloader(self):
        from menus.downloader import Downloader
        arcade.unschedule(self.update_presence)
        self.ui.clear()
        self.window.show_view(Downloader(self.pypresence_client, self.current_tab, self.current_mode, self.current_music_artist, self.current_music_title, self.current_music_path, self.current_length, self.current_music_player, self.current_synchronized_lyrics, self.queue, self.loaded_sounds, self.shuffle))

    def reload(self):
        self.load_content()

        if self.current_mode == "files":
            self.show_content(os.path.expanduser(self.current_tab), "files")
        elif self.current_mode == "playlist":
            self.show_content(self.current_tab, "playlist")

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
            details = "No songs playing"
            state = "No songs playing"

        self.pypresence_client.update(state=state, details=details, start=self.pypresence_client.start_time)
