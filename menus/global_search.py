import arcade, arcade.gui

from utils.preload import music_icon, person_icon, button_texture, button_hovered_texture
from utils.constants import button_style
from utils.utils import Card, MouseAwareScrollArea, get_wordwrapped_text
from utils.musicbrainz_metadata import search_recordings, search_artists, search_albums, get_artists_metadata, get_album_metadata

from arcade.gui.experimental.focus import UIFocusGroup
from arcade.gui.experimental.scroll_area import UIScrollBar

class GlobalSearch(arcade.gui.UIView):
    def __init__(self, pypresence_client, *args):
        super().__init__()
        
        self.args = args
        self.pypresence_client = pypresence_client

        self.anchor = self.add_widget(UIFocusGroup(size_hint=(1, 1)))

    def on_show_view(self):
        super().on_show_view()

        self.anchor.detect_focusable_widgets()

        self.ui_box = self.anchor.add(arcade.gui.UIBoxLayout(size_hint=(0.99, 0.99), space_between=10), anchor_x="center", anchor_y="center")

        self.search_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(1, 0.075), space_between=10, vertical=False))

        self.back_button = self.search_box.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='<--', style=button_style, width=100, height=50))
        self.back_button.on_click = lambda event: self.main_exit()

        self.search_bar = self.search_box.add(arcade.gui.UIInputText(width=self.window.width / 2, height=self.window.height / 20, font_size=20))
        self.search_bar.on_change = lambda event: self.fix_searchbar_text()
        self.search_type_dropdown = self.search_box.add(arcade.gui.UIDropdown(options=["Music", "Artist", "Album"], default="Music", primary_style=button_style, active_style=button_style, dropdown_style=button_style, width=self.window.width / 4, height=self.window.height / 20))

        self.scroll_box = self.ui_box.add(arcade.gui.UIBoxLayout(size_hint=(1, 0.925), space_between=15, vertical=False))

        self.scroll_area = MouseAwareScrollArea(size_hint=(1, 1))
        self.scroll_area.scroll_speed = -50
        self.scroll_box.add(self.scroll_area)

        self.scrollbar = UIScrollBar(self.scroll_area)
        self.scrollbar.size_hint = (0.02, 1)
        self.scroll_box.add(self.scrollbar)

        self.search_results_grid = arcade.gui.UIGridLayout(horizontal_spacing=25, vertical_spacing=25, column_count=8, row_count=999)
        self.scroll_area.add(self.search_results_grid)

        self.nothing_searched_label = self.anchor.add(arcade.gui.UILabel(text="Search for something to get results!", font_name="Roboto", font_size=24), anchor_x="center", anchor_y="center")
        self.nothing_searched_label.visible = True

    def fix_searchbar_text(self):
        self.search_bar.text = self.search_bar.text.encode("ascii", "ignore").decode().strip("\n")

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ENTER:
            self.fix_searchbar_text()
            self.search()

    def search(self):
        search_type = self.search_type_dropdown.value
        search_term = self.search_bar.text

        self.search_results_grid.clear()

        if search_type == "Music":
            recordings = search_recordings(search_term)

            self.nothing_searched_label.visible = not bool(recordings)

            for n, metadata in enumerate(recordings):
                row = n // 7
                col = n % 7

                card = self.search_results_grid.add(Card(music_icon, get_wordwrapped_text(metadata[1]), get_wordwrapped_text(metadata[0]), width=self.window.width / 7, height=self.window.width / 7), row=row, column=col)
                card.button.on_click = lambda event, metadata=metadata: self.open_metadata_viewer(metadata[2], metadata[0], metadata[1])

        elif search_type == "Artist":
            artists = search_artists(search_term)

            self.nothing_searched_label.visible = not bool(artists)

            for n, metadata in enumerate(artists):
                row = n // 7
                col = n % 7

                card = self.search_results_grid.add(Card(person_icon, get_wordwrapped_text(metadata[0]), None, width=self.window.width / 7, height=self.window.width / 4.5), row=row, column=col)
                card.button.on_click = lambda event, metadata=metadata: self.open_metadata_viewer(metadata[1])
        else:
            albums = search_albums(search_term)

            self.nothing_searched_label.visible = not bool(albums)

            for n, metadata in enumerate(albums):
                row = n // 7
                col = n % 7

                card = self.search_results_grid.add(Card(music_icon, get_wordwrapped_text(metadata[1]), get_wordwrapped_text(metadata[0]), width=self.window.width / 7, height=self.window.width / 7), row=row, column=col)
                card.button.on_click = lambda event, metadata=metadata: self.open_metadata_viewer(metadata[2])

        self.search_results_grid.row_count = row + 1
        self.search_results_grid._update_size_hints()

    def open_metadata_viewer(self, musicbrainz_id, artist=None, title=None):
        content_type = self.search_type_dropdown.value.lower()

        from menus.metadata_viewer import MetadataViewer
        if content_type == "music":
            self.window.show_view(MetadataViewer(self.pypresence_client, content_type, {"artist": artist, "title": title, "id": musicbrainz_id}, None, *self.args))
        elif content_type == "artist":
            self.window.show_view(MetadataViewer(self.pypresence_client, content_type, get_artists_metadata([musicbrainz_id])))
        elif content_type == "album":
            self.window.show_view(MetadataViewer(self.pypresence_client, content_type, {musicbrainz_id: get_album_metadata(musicbrainz_id)}))
            
    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client, *self.args))