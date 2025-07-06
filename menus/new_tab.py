import arcade, arcade.gui, os, json

from utils.constants import button_style
from utils.preload import button_texture, button_hovered_texture

from menus.file_manager import FileManager

from arcade.gui.experimental.focus import UIFocusGroup

class NewTab(arcade.gui.UIView):
    def __init__(self, pypresence_client, *args, directory_selected=None):
        super().__init__()

        self.args = args
        self.directory_selected = directory_selected

        with open("settings.json", "r", encoding="utf-8") as file:
            self.settings_dict = json.load(file)

        self.tab_options = self.settings_dict.get("tab_options", [os.path.join("~", "Music"), os.path.join("~", "Downloads")])
        self.playlists = self.settings_dict.get("playlists", {})

        self.tab_type = "Directory"

        self.pypresence_client = pypresence_client
        self.pypresence_client.update(state="Adding new tab", start=self.pypresence_client.start_time)

    def on_show_view(self):
        super().on_show_view()

        self.create_ui()

    def change_tab_type(self, tab_type):
        self.tab_type = tab_type

        self.ui.clear()
        self.create_ui()

    def create_ui(self):
        self.anchor = self.add_widget(UIFocusGroup(size_hint=(1, 1)))
        self.box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=10), anchor_x="center", anchor_y="center")

        self.new_tab_type_label = self.box.add(arcade.gui.UILabel(text="Tab Type:", font_name="Roboto", font_size=32))
        self.tab_type_dropdown = self.box.add(arcade.gui.UIDropdown(options=["Directory", "Playlist"], default=self.tab_type, primary_style=button_style, dropdown_style=button_style, active_style=button_style, width=self.window.width / 3, height=self.window.height / 15))
        self.tab_type_dropdown.on_change = lambda e: self.change_tab_type(e.new_value)

        if self.tab_type == "Playlist":
            self.new_tab_label = self.box.add(arcade.gui.UILabel(text="New Tab Name:", font_name="Roboto", font_size=32))    
            self.new_tab_input = self.box.add(arcade.gui.UIInputText(font_name="Roboto", font_size=32, width=self.window.width / 3, height=self.window.height / 15))
        else:
            self.new_tab_label = self.box.add(arcade.gui.UILabel(text="New Tab Path:", font_name="Roboto", font_size=32))    
            self.add_music_input = self.box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=f'Select Directory ({self.directory_selected})', style=button_style, font_name="Roboto", font_size=32, width=self.window.width / 3, height=self.window.height / 15))
            self.add_music_input.on_click = lambda event: self.select_directory()

        self.new_tab_button = self.box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='Add new Tab', style=button_style, width=self.window.width / 3, height=self.window.height / 15))
        self.new_tab_button.on_click = lambda event: self.add_tab()

        self.back_button = self.anchor.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='<--', style=button_style, width=100, height=50), anchor_x="left", anchor_y="top", align_x=5, align_y=-5)
        self.back_button.on_click = lambda event: self.main_exit()

        self.anchor.detect_focusable_widgets()

    def select_directory(self):
        self.window.show_view(FileManager(os.path.expanduser("~"), [], "directory", self.pypresence_client, *self.args))

    def add_tab(self):
        if self.tab_type == "Directory":
            tab_path = self.directory_selected

            if not tab_path:
                return

            if not os.path.exists(os.path.expanduser(tab_path)) or not os.path.isdir(os.path.expanduser(tab_path)) or not os.path.isabs(os.path.expanduser(tab_path)):
                return

            if tab_path in self.tab_options or os.path.expanduser(tab_path) in self.tab_options:
                return

            self.tab_options.append(tab_path)
            self.settings_dict["tab_options"] = self.tab_options

        elif self.tab_type == "Playlist":
            self.playlists[self.new_tab_input.text] = []
            self.settings_dict["playlists"] = self.playlists

        with open("settings.json", "w", encoding="utf-8") as file:
            file.write(json.dumps(self.settings_dict))

    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client, *self.args))
