import arcade, arcade.gui, webbrowser

from arcade.gui.experimental.focus import UIFocusGroup
from arcade.gui.experimental.scroll_area import UIScrollArea, UIScrollBar

from utils.online_metadata import get_music_metadata, get_album_cover_art
from utils.constants import button_style
from utils.preload import button_texture, button_hovered_texture
from utils.utils import convert_seconds_to_date
from utils.music_handling import convert_timestamp_to_time_ago

class MetadataViewer(arcade.gui.UIView):
    def __init__(self, pypresence_client, metadata_type="music", metadata_dict=None, file_path=None, *args):
        super().__init__()
        self.metadata_type = metadata_type
        if metadata_type == "music":
            self.file_metadata = metadata_dict
            self.artist = self.file_metadata["artist"]
            self.file_path = file_path
            if self.artist == "Unknown":
                self.artist = None
            self.title = self.file_metadata["title"]

            self.online_metadata = get_music_metadata(self.artist, self.title)

        elif metadata_type == "artist":
            self.artist_metadata = metadata_dict
        elif metadata_type == "album":
            self.album_metadata = metadata_dict

        self.pypresence_client = pypresence_client
        self.args = args
        self.more_metadata_buttons = []
        self.metadata_labels = []

    def on_show_view(self):
        super().on_show_view()

        self.anchor = self.add_widget(UIFocusGroup(size_hint=(1, 1)))
        self.back_button = self.anchor.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='<--', style=button_style, width=100, height=50), anchor_x="left", anchor_y="top", align_x=5, align_y=-5)
        self.back_button.on_click = lambda event: self.main_exit()

        self.scroll_area = UIScrollArea(size_hint=(0.6, 0.8)) # center on screen
        self.scroll_area.scroll_speed = -50
        self.anchor.add(self.scroll_area, anchor_x="center", anchor_y="center")

        self.scrollbar = UIScrollBar(self.scroll_area)
        self.scrollbar.size_hint = (0.02, 1)
        self.anchor.add(self.scrollbar, anchor_x="right", anchor_y="center")

        self.box = arcade.gui.UIBoxLayout(space_between=10, align='top')
        self.scroll_area.add(self.box)

        self.more_metadata_box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=10, vertical=False), anchor_x="left", anchor_y="bottom", align_x=10, align_y=10)

        if self.metadata_type == "music":
            tags = ', '.join(self.online_metadata[0]['tags'])
            albums = ', '.join(list(self.online_metadata[2].keys()))
            name = f"{self.file_metadata['artist']} - {self.file_metadata['title']} Metadata"
            metadata_text = f'''File path: {self.file_path}
File Artist: {self.file_metadata['artist']}
MusicBrainz Artists: {', '.join([artist for artist in self.online_metadata[1]])}
Title: {self.file_metadata['title']}
MusicBrainz ID: {self.online_metadata[0]['musicbrainz_id']}
ISRC(s): {', '.join(self.online_metadata[0]['isrc-list']) if self.online_metadata[0]['isrc-list'] else "None"}
MusicBrainz Rating: {self.online_metadata[0]['musicbrainz_rating']}
Tags: {tags if tags else 'None'}
Albums: {albums if albums else 'None'}

File size: {self.file_metadata['file_size']}MiB
Upload Year: {self.file_metadata['upload_year'] or 'Unknown'}
Amount of times played: {self.file_metadata['play_count']}
Last Played: {convert_timestamp_to_time_ago(int(self.file_metadata['last_played']))}
Sound length: {convert_seconds_to_date(int(self.file_metadata['sound_length']))}
Bitrate: {self.file_metadata['bitrate']}Kbps
Sample rate: {self.file_metadata['sample_rate']}KHz
'''
            self.more_metadata_buttons.append(self.more_metadata_box.add(arcade.gui.UITextureButton(text=f"Artist Metadata", style=button_style, texture=button_texture, texture_hovered=button_hovered_texture, width=self.window.width / 4.25, height=self.window.height / 15)))
            self.more_metadata_buttons[-1].on_click = lambda event: self.window.show_view(MetadataViewer(self.pypresence_client, "artist", self.online_metadata[1], None, *self.args))

            self.more_metadata_buttons.append(self.more_metadata_box.add(arcade.gui.UITextureButton(text=f"Album Metadata", style=button_style, texture=button_texture, texture_hovered=button_hovered_texture, width=self.window.width / 4.25, height=self.window.height / 15)))
            self.more_metadata_buttons[-1].on_click = lambda event: self.window.show_view(MetadataViewer(self.pypresence_client, "album", self.online_metadata[2], None, *self.args))

            self.more_metadata_buttons.append(self.more_metadata_box.add(arcade.gui.UITextureButton(text=f"Open Uploader URL", style=button_style, texture=button_texture, texture_hovered=button_hovered_texture, width=self.window.width / 4.25, height=self.window.height / 15)))
            self.more_metadata_buttons[-1].on_click = lambda event: webbrowser.open(self.file_metadata["uploader_url"]) if not self.file_metadata.get("uploader_url", "Unknown") == "Unknown" else None

            self.more_metadata_buttons.append(self.more_metadata_box.add(arcade.gui.UITextureButton(text=f"Open Source URL", style=button_style, texture=button_texture, texture_hovered=button_hovered_texture, width=self.window.width / 4.25, height=self.window.height / 15)))
            self.more_metadata_buttons[-1].on_click = lambda event: webbrowser.open(self.file_metadata["source_url"]) if not self.file_metadata.get("source_url", "Unknown") == "Unknown" else None


            metadata_box = self.box.add(arcade.gui.UIBoxLayout(space_between=10, align='left'))

            self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=name, font_size=20, font_name="Roboto", multiline=True)))
            self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=metadata_text, font_size=18, font_name="Roboto", multiline=True)))

        elif self.metadata_type == "artist":
            for artist_name, artist_dict in self.artist_metadata.items():
                ipi_list = ', '.join(artist_dict['ipi-list'])
                isni_list = ', '.join(artist_dict['isni-list'])
                tag_list = ','.join(artist_dict['tag-list'])
                name = f"{artist_name} Metadata"
                metadata_text = f'''Artist MusicBrainz ID: {artist_dict['musicbrainz_id']}
Artist Gender: {artist_dict['gender']}
Artist Tag(s): {tag_list if tag_list else 'None'}
Artist IPI(s): {ipi_list if ipi_list else 'None'}
Artist ISNI(s): {isni_list if isni_list else 'None'}
Artist Born: {artist_dict['born']}
Artist Dead: {'Yes' if artist_dict['dead'] else 'No'}
Artist Comment: {artist_dict['comment']}
'''             
                metadata_box = self.box.add(arcade.gui.UIBoxLayout(space_between=10, align='left'))
                self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=name, font_size=20, font_name="Roboto", multiline=True)))
                self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=metadata_text, font_size=18, font_name="Roboto", multiline=True)))

        elif self.metadata_type == "album":
            if not self.album_metadata:
                self.metadata_labels.append(self.anchor.add(arcade.gui.UILabel(text="We couldn't find any albums for this music.", font_size=32, font_name="Roboto"), anchor_x="center", anchor_y="center"))
                return
        
            self.cover_art_box = self.box.add(arcade.gui.UIBoxLayout(space_between=100, align="left"))

            for album_name, album_dict in self.album_metadata.items():
                name = f"{album_name} Metadata"
                metadata_text = f'''
MusicBrainz Album ID: {album_dict['musicbrainz_id']}
Album Name: {album_dict['album_name']}
Album Date: {album_dict['album_date']}
Album Country: {album_dict['album_country']} 
'''
                full_box = self.box.add(arcade.gui.UIBoxLayout(space_between=30, align='center', vertical=False))
                metadata_box = full_box.add(arcade.gui.UIBoxLayout(space_between=10, align='center'))

                self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=name, font_size=20, font_name="Roboto", multiline=True)))
                self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=metadata_text, font_size=18, font_name="Roboto", multiline=True)))
                
                cover_art = get_album_cover_art(album_dict["musicbrainz_id"])

                if cover_art:
                    full_box.add(arcade.gui.UIImage(texture=cover_art, width=self.window.width / 10, height=self.window.height / 6))
                else:
                    full_box.add(arcade.gui.UILabel(text="No cover found.", font_size=18, font_name="Roboto"))

    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client, *self.args))
