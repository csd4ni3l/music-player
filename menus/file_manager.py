import arcade, arcade.gui, os, time

from utils.constants import button_style
from utils.preload import button_texture, button_hovered_texture

from arcade.gui.experimental.scroll_area import UIScrollArea, UIScrollBar

class FileManager(arcade.gui.UIView):
    def __init__(self, start_directory, allowed_extensions, select_mode="dir", *args):
        super().__init__()

        self.select_mode = select_mode
        self.current_directory = start_directory
        self.allowed_extensions = allowed_extensions        
        self.file_buttons = []
        self.submitted_content = ""
        self.done = False
        self.args = args

        self.anchor = self.ui.add(arcade.gui.UIAnchorLayout(size_hint=(1, 1)))
        self.box = self.anchor.add(arcade.gui.UIBoxLayout(size_hint=(0.7, 0.7)), anchor_x="center", anchor_y="center")

        self.content_cache = {}
        self.pre_cache_contents()

    def on_show_view(self):
        super().on_show_view() 

        self.current_directory_label = self.anchor.add(arcade.gui.UILabel(text=self.current_directory, font_name="Roboto", font_size=24), anchor_x="center", anchor_y="top", align_y=-15)

        self.scroll_area = UIScrollArea(size_hint=(0.95, 1)) # center on screen
        self.scroll_area.scroll_speed = -50
        self.box.add(self.scroll_area)

        self.scrollbar = UIScrollBar(self.scroll_area)
        self.scrollbar.size_hint = (0.02, 1)
        self.anchor.add(self.scrollbar, anchor_x="right", anchor_y="center")

        self.files_box = arcade.gui.UIBoxLayout(space_between=5)
        self.scroll_area.add(self.files_box)
        
        self.back_button = self.anchor.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='<--', style=button_style, width=100, height=50), anchor_x="left", anchor_y="top", align_x=5, align_y=-5)
        self.back_button.on_click = lambda event: self.change_directory(os.path.dirname(self.current_directory))
        
        self.show_directory()

        if self.select_mode == "directory":
            self.submit_button = self.anchor.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text="Submit", style=button_style, width=self.window.width / 10, height=self.window.height / 10), anchor_x="right", anchor_y="bottom", align_x=-self.window.width / 30)
            self.submit_button.on_click = lambda event: self.submit(self.current_directory)
    
    def submit(self, content):
        self.submitted_content = content
        self.done = True
        
        if self.select_mode == "file":
            from menus.add_music import AddMusic
            self.window.show_view(AddMusic(*self.args, music_file_selected=self.submitted_content))
        elif self.select_mode == "directory":
            from menus.new_tab import NewTab
            self.window.show_view(NewTab(*self.args, directory_selected=self.submitted_content))

    def get_content(self, directory):
        if not directory in self.content_cache or time.perf_counter() - self.content_cache[directory][-1] >= 30:
            try:
                entries = os.listdir(directory)
            except PermissionError:
                return None
            
            filtered = [
                entry for entry in entries
                if (os.path.isdir(os.path.join(directory, entry)) and not "." in entry) or
                os.path.splitext(entry)[1].lower() in self.allowed_extensions
            ]
            
            sorted_entries = sorted(
                filtered,
                key=lambda x: (0 if os.path.isdir(os.path.join(directory, x)) else 1, x.lower())
            )

            self.content_cache[directory] = sorted_entries
            self.content_cache[directory].append(time.perf_counter())

        return self.content_cache[directory][:-1]
    
    def pre_cache_contents(self):
        for directory in self.walk_limited_depth(self.current_directory):
            self.get_content(directory)

    def walk_limited_depth(self, start_dir, max_depth=2):
        start_dir = os.path.abspath(start_dir)
        
        def _walk(current_dir, current_depth):
            if current_depth > max_depth:
                return
            
            yield current_dir
            try:
                with os.scandir(current_dir) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            yield from _walk(entry.path, current_depth + 1)
            except PermissionError:
                pass  # skip directories you can't access

        return _walk(start_dir, 0)

    def show_directory(self):
        self.files_box.clear()
        self.file_buttons.clear()

        self.current_directory_label.text = self.current_directory

        for file in self.get_content(self.current_directory):
            self.file_buttons.append(self.files_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text=file, style=button_style, width=self.window.width / 1.5)))
            
            if os.path.isdir(f"{self.current_directory}/{file}"):
                self.file_buttons[-1].on_click = lambda event, directory=f"{self.current_directory}/{file}": self.change_directory(directory)
            elif self.select_mode == "file":
                self.file_buttons[-1].on_click = lambda event, file=f"{self.current_directory}/{file}": self.submit(file)
        
    def change_directory(self, directory):
        if directory.startswith("//"): # Fix / paths
            directory = directory[1:]

        self.current_directory = directory
        
        self.show_directory()

    def on_key_press(self, symbol: int, modifiers: int) -> bool | None:
        if symbol == arcade.key.ESCAPE:
            from menus.main import Main
            self.window.show_view(Main(*self.args))

    def on_mouse_press(self, x, y, button, modifiers):
       if button == arcade.MOUSE_BUTTON_RIGHT:
           self.change_directory(os.path.dirname(self.current_directory))