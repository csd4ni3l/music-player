import arcade, arcade.gui, os, json

from utils.constants import button_style, audio_extensions
from utils.preload import button_texture, button_hovered_texture
from menus.file_manager import FileManager
from arcade.gui.experimental.focus import UIFocusGroup

class AddMusic(arcade.gui.UIView):
    def __init__(self, pypresence_client, current_mode, current_music_name, current_length, current_music_player, queue, loaded_sounds, shuffle, music_file_selected=None):
        super().__init__()

        self.current_mode = current_mode
        self.current_music_name = current_music_name
        self.current_length = current_length
        self.current_music_player = current_music_player
        self.queue = queue
        self.loaded_sounds = loaded_sounds
        self.shuffle = shuffle
        self.music_file_selected = music_file_selected

        with open("settings.json", "r", encoding="utf-8") as file:
            self.settings_dict = json.load(file)

        self.playlists = self.settings_dict.get("playlists", {})

        self.pypresence_client = pypresence_client
        self.pypresence_client.update(state="Adding music to playlist", start=self.pypresence_client.start_time)

    def on_show_view(self):
        super().on_show_view()

        self.anchor = self.add_widget(UIFocusGroup(size_hint=(1, 1)))
        self.box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=10), anchor_x="center", anchor_y="center")

        self.playlist_label = self.box.add(arcade.gui.UILabel(text="Playlist", font_name="Roboto", font_size=32))
        
        self.playlist_option = self.box.add(arcade.gui.UIDropdown(default=list(self.playlists.keys())[0], options=list(self.playlists.keys()), width=self.window.width / 2, height=self.window.height / 15, primary_style=button_style, dropdown_style=button_style, active_style=button_style))
        
        self.music_label = self.box.add(arcade.gui.UILabel(text="Music File Path", font_name="Roboto", font_size=32))
        
        self.add_music_input = self.box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=f'Select File ({self.music_file_selected})', style=button_style, font_name="Roboto", font_size=32, width=self.window.width / 2, height=self.window.height / 10))
        self.add_music_input.on_click = lambda event: self.select_file()

        self.add_music_button = self.box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='Add Music', style=button_style, width=self.window.width / 2, height=self.window.height / 10))
        self.add_music_button.on_click = lambda event: self.add_music()

        self.back_button = self.anchor.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='<--', style=button_style, width=100, height=50), anchor_x="left", anchor_y="top", align_x=5, align_y=-5)
        self.back_button.on_click = lambda event: self.main_exit()

        self.anchor.detect_focusable_widgets()

    def select_file(self):
        self.window.show_view(FileManager(os.path.expanduser("~"), [f".{extension}" for extension in audio_extensions], "file", self.pypresence_client, self.current_mode, self.current_music_name, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))

    def add_music(self):
        music_path = self.music_file_selected
        playlist = self.playlist_option.value

        if not music_path:
            return

        if not os.path.exists(os.path.expanduser(music_path)) or not os.path.isfile(os.path.expanduser(music_path)) or not os.path.isabs(os.path.expanduser(music_path)):
            return

        if music_path in self.playlists[playlist] or os.path.expanduser(music_path) in self.playlists[playlist]:
            return

        self.playlists[playlist].append(os.path.expanduser(music_path))
        self.settings_dict["playlists"] = self.playlists

        with open("settings.json", "w", encoding="utf-8") as file:
            file.write(json.dumps(self.settings_dict))

    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client, self.current_mode, self.current_music_name, self.current_length, self.current_music_player, self.queue, self.loaded_sounds, self.shuffle))
