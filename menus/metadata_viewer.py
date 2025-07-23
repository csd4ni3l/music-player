import arcade, arcade.gui, webbrowser, os

from arcade.gui.experimental.focus import UIFocusGroup
from arcade.gui.experimental.scroll_area import UIScrollArea, UIScrollBar

from utils.musicbrainz_metadata import get_music_metadata
from utils.cover_art import download_albums_cover_art
from utils.constants import button_style
from utils.preload import button_texture, button_hovered_texture
from utils.utils import convert_seconds_to_date
from utils.music_handling import convert_timestamp_to_time_ago, truncate_end, add_metadata_to_file
from utils.acoustid_metadata import get_recording_id_from_acoustid, get_fpcalc_path

class MetadataViewer(arcade.gui.UIView):
    def __init__(self, pypresence_client, metadata_type="file", metadata=None, file_path=None, *args):
        super().__init__()
        
        self.metadata_type = metadata_type
        self.pypresence_client = pypresence_client
        self.args = args
        self.more_metadata_buttons = []
        self.metadata_labels = []
        self.msgbox = None

        if metadata_type == "file":
            self.file_metadata = metadata
            self.file_path = file_path

            self.artist = self.file_metadata["artist"] if not self.file_metadata["artist"] == "Unknown" else None
            self.title = self.file_metadata["title"]

            if os.path.exists(get_fpcalc_path()):
                self.acoustid_id, musicbrainz_id = get_recording_id_from_acoustid(self.file_path)
            else:
                self.acoustid_id, musicbrainz_id = None, None

            if self.acoustid_id and musicbrainz_id:
                self.music_metadata, self.artist_metadata, self.album_metadata, self.lyrics_metadata = get_music_metadata(musicbrainz_id=musicbrainz_id)
                return
            
            self.music_metadata, self.artist_metadata, self.album_metadata, self.lyrics_metadata = get_music_metadata(artist=self.artist, title=self.title)
            
        elif metadata_type == "music":
            self.artist = metadata["artist"]
            self.title = metadata["title"]

            self.music_metadata, self.artist_metadata, self.album_metadata, self.lyrics_metadata = get_music_metadata(musicbrainz_id=metadata["id"])
        elif metadata_type == "artist":
            self.artist_metadata = metadata
        elif metadata_type == "album":
            self.album_metadata = metadata

    def on_show_view(self):
        super().on_show_view()

        if self.msgbox:
            return
        
        if self.metadata_type == "file":
            add_metadata_to_file(self.file_path, [artist['musicbrainz_id'] for artist in self.artist_metadata.values()], self.artist, self.title, self.lyrics_metadata[1], self.music_metadata["isrc-list"], self.acoustid_id)

        self.anchor = self.add_widget(UIFocusGroup(size_hint=(1, 1)))
        self.back_button = self.anchor.add(arcade.gui.UITextureButton(texture=button_texture, texture_hovered=button_hovered_texture, text='<--', style=button_style, width=100, height=50), anchor_x="left", anchor_y="top", align_x=5, align_y=-5)

        self.scroll_area = UIScrollArea(size_hint=(0.6, 0.8)) # center on screen
        self.scroll_area.scroll_speed = -50
        self.anchor.add(self.scroll_area, anchor_x="center", anchor_y="center")

        self.scrollbar = UIScrollBar(self.scroll_area)
        self.scrollbar.size_hint = (0.02, 1)
        self.anchor.add(self.scrollbar, anchor_x="right", anchor_y="center")

        self.box = arcade.gui.UIBoxLayout(space_between=10, align='center')
        self.scroll_area.add(self.box)

        self.more_metadata_box = self.anchor.add(arcade.gui.UIBoxLayout(space_between=10, vertical=False), anchor_x="left", anchor_y="bottom", align_x=10, align_y=10)

        self.show_metadata()

    def show_metadata(self):
        if self.metadata_type == "file":
            self.back_button.on_click = lambda event: self.main_exit()
        elif self.metadata_type == "music":
            self.back_button.on_click = lambda event: self.global_search()
        else:
            self.back_button.on_click = lambda event: self.reset_to_music_view()

        self.more_metadata_buttons.clear()
        self.metadata_labels.clear()

        self.box.clear()
        self.more_metadata_box.clear()

        if self.metadata_type in ["file", "music"]:
            tags = ', '.join(self.music_metadata['tags'])
            albums = truncate_end(', '.join([album["album_name"] for album in self.album_metadata.values()]), 50)
            name = f"{self.artist} - {self.title} Metadata"
            musicbrainz_metadata_text = f'''MusicBrainz Artist(s): {', '.join([artist for artist in self.artist_metadata])}
MusicBrainz ID: {self.music_metadata['musicbrainz_id']}
ISRC(s): {', '.join(self.music_metadata['isrc-list']) if self.music_metadata['isrc-list'] else "None"}
MusicBrainz Rating: {self.music_metadata['musicbrainz_rating']}
Tags: {tags if tags else 'None'}
Albums: {albums if albums else 'None'}'''
            if self.metadata_type == "file":
                metadata_text = f'''File path: {self.file_path}
File Artist(s): {self.file_metadata['artist']}
Title: {self.file_metadata['title']}

{musicbrainz_metadata_text}

File size: {self.file_metadata['file_size']}MiB
Upload Year: {self.file_metadata['upload_year'] or 'Unknown'}
Amount of times played: {self.file_metadata['play_count']}
Last Played: {convert_timestamp_to_time_ago(int(self.file_metadata['last_played']))}
Sound length: {convert_seconds_to_date(int(self.file_metadata['sound_length']))}
Bitrate: {self.file_metadata['bitrate']}Kbps
Sample rate: {self.file_metadata['sample_rate']}KHz'''
            else:
                metadata_text = musicbrainz_metadata_text

            metadata_text += f"\n\nLyrics:\n{self.lyrics_metadata[0]}"

            self.more_metadata_buttons.append(self.more_metadata_box.add(arcade.gui.UITextureButton(text="Artist Metadata", style=button_style, texture=button_texture, texture_hovered=button_hovered_texture, width=self.window.width / 4.5 if self.metadata_type == "file" else self.window.width / 2.5, height=self.window.height / 15)))
            self.more_metadata_buttons[-1].on_click = lambda event: self.show_artist_metadata()

            self.more_metadata_buttons.append(self.more_metadata_box.add(arcade.gui.UITextureButton(text="Album Metadata", style=button_style, texture=button_texture, texture_hovered=button_hovered_texture, width=self.window.width / 4.5 if self.metadata_type == "file" else self.window.width / 2.5, height=self.window.height / 15)))
            self.more_metadata_buttons[-1].on_click = lambda event: self.show_album_metadata()

            if self.metadata_type == "file":
                self.more_metadata_buttons.append(self.more_metadata_box.add(arcade.gui.UITextureButton(text="Open Uploader URL", style=button_style, texture=button_texture, texture_hovered=button_hovered_texture, width=self.window.width / 4.5, height=self.window.height / 15)))
                self.more_metadata_buttons[-1].on_click = lambda event: webbrowser.open(self.file_metadata["uploader_url"]) if not self.file_metadata.get("uploader_url", "Unknown") == "Unknown" else None

                self.more_metadata_buttons.append(self.more_metadata_box.add(arcade.gui.UITextureButton(text="Open Source URL", style=button_style, texture=button_texture, texture_hovered=button_hovered_texture, width=self.window.width / 4.5, height=self.window.height / 15)))
                self.more_metadata_buttons[-1].on_click = lambda event: webbrowser.open(self.file_metadata["source_url"]) if not self.file_metadata.get("source_url", "Unknown") == "Unknown" else None

            metadata_box = self.box.add(arcade.gui.UIBoxLayout(space_between=10, align='center'))
            self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=name, font_size=20, font_name="Roboto", multiline=True)))
            self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=metadata_text, font_size=18, font_name="Roboto", multiline=True)))

        elif self.metadata_type == "artist":
            for artist_name, artist_dict in self.artist_metadata.items():
                ipi_list = ', '.join(artist_dict['ipi-list'])
                isni_list = ', '.join(artist_dict['isni-list'])
                tag_list = ', '.join(artist_dict['tag-list'])
                example_tracks = ', '.join(artist_dict['example_tracks'])
                name = f"{artist_name} Metadata"
                metadata_text = f'''Artist MusicBrainz ID: {artist_dict['musicbrainz_id']}
Artist Gender: {artist_dict['gender']}
Example Tracks: {example_tracks}
Artist Tag(s): {tag_list if tag_list else 'None'}
Artist IPI(s): {ipi_list if ipi_list else 'None'}
Artist ISNI(s): {isni_list if isni_list else 'None'}
Artist Born: {artist_dict['born']}
Artist Dead: {'Yes' if artist_dict['dead'] else 'No'}
Artist Comment: {artist_dict['comment']}
'''             
                for url_name, url_target in artist_dict["urls"].items():
                    metadata_text += f"\n{url_name.capitalize()} Links: {', '.join(url_target)}"

                metadata_box = self.box.add(arcade.gui.UIBoxLayout(space_between=10, align='left'))
                self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=name, font_size=20, font_name="Roboto", multiline=True, align="center")))
                self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=metadata_text, font_size=18, font_name="Roboto", multiline=True)))

        elif self.metadata_type == "album":
            if not self.album_metadata:
                self.metadata_labels.append(self.anchor.add(arcade.gui.UILabel(text="We couldn't find any albums for this music.", font_size=32, font_name="Roboto"), anchor_x="center", anchor_y="center"))
                return
        
            self.cover_art_box = self.box.add(arcade.gui.UIBoxLayout(space_between=100, align="left"))

            album_cover_arts = download_albums_cover_art([album_id for album_id in self.album_metadata.keys()])

            for album_id, album_dict in self.album_metadata.items():
                name = f"{album_dict['album_name']} Metadata"
                metadata_text = f'''
MusicBrainz Album ID: {album_id}
Album Name: {album_dict['album_name']}
Album Date: {album_dict['album_date']}
Album Country: {album_dict['album_country']}
Example Tracks: {", ".join(album_dict['album_tracks'])}
'''
                full_box = self.box.add(arcade.gui.UIBoxLayout(space_between=30, align='center', vertical=False))
                metadata_box = full_box.add(arcade.gui.UIBoxLayout(space_between=10, align='center'))

                self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=name, font_size=20, font_name="Roboto", multiline=True)))
                self.metadata_labels.append(metadata_box.add(arcade.gui.UILabel(text=metadata_text, font_size=18, font_name="Roboto", multiline=True)))
                
                cover_art = album_cover_arts[album_id]

                if cover_art:
                    full_box.add(arcade.gui.UIImage(texture=cover_art, width=self.window.width / 10, height=self.window.height / 6))
                else:
                    full_box.add(arcade.gui.UILabel(text="No cover found.", font_size=18, font_name="Roboto"))

    def reset_to_music_view(self):
        if hasattr(self, "file_metadata"):
            self.metadata_type = "file"
        elif hasattr(self, "lyrics_metadata"):
            self.metadata_type = "music"
        else: # artists and albums from global search
            self.global_search()
            return
        self.show_metadata()

    def show_artist_metadata(self):
        self.metadata_type = "artist"
        self.show_metadata()

    def show_album_metadata(self):
        self.metadata_type = "album"
        self.show_metadata()

    def main_exit(self):
        from menus.main import Main
        self.window.show_view(Main(self.pypresence_client, *self.args))

    def global_search(self):
        from menus.global_search import GlobalSearch
        self.window.show_view(GlobalSearch(self.pypresence_client, *self.args))