import logging, sys, traceback

from utils.constants import menu_background_color
from utils.preload import resume_icon, music_icon

import pyglet, arcade, arcade.gui

from arcade.gui.experimental.scroll_area import UIScrollArea

def dump_platform():
    import platform
    logging.debug(f'Platform: {platform.platform()}')
    logging.debug(f'Release: {platform.release()}')
    logging.debug(f'Machine: {platform.machine()}')
    logging.debug(f'Architecture: {platform.architecture()}')

def dump_gl():
    from pyglet.gl import gl_info as info
    logging.debug(f'gl_info.get_version(): {info.get_version()}')
    logging.debug(f'gl_info.get_vendor(): {info.get_vendor()}')
    logging.debug(f'gl_info.get_renderer(): {info.get_renderer()}')

def print_debug_info():
    logging.debug('########################## DEBUG INFO ##########################')
    logging.debug('')
    dump_platform()
    dump_gl()
    logging.debug('')
    logging.debug(f'Number of screens: {len(pyglet.display.get_display().get_screens())}')
    logging.debug('')
    for n, screen in enumerate(pyglet.display.get_display().get_screens()):
        logging.debug(f"Screen #{n+1}:")
        logging.debug(f'DPI: {screen.get_dpi()}')
        logging.debug(f'Scale: {screen.get_scale()}')
        logging.debug(f'Size: {screen.width}, {screen.height}')
        logging.debug(f'Position: {screen.x}, {screen.y}')
    logging.debug('')
    logging.debug('########################## DEBUG INFO ##########################')
    logging.debug('')

class ErrorView(arcade.gui.UIView):
    def __init__(self, message: str, title: str):
        super().__init__()

        self.message = message
        self.title = title

    def exit(self):
        logging.fatal('Exited with error code 1.')
        sys.exit(1)

    def on_show_view(self):
        super().on_show_view()

        self.window.set_caption('Music Player - Error')
        self.window.set_mouse_visible(True)
        self.window.set_exclusive_mouse(False)
        arcade.set_background_color(menu_background_color)

        msgbox = arcade.gui.UIMessageBox(width=self.window.width / 2, height=self.window.height / 2, message_text=self.message, title=self.title)
        msgbox.on_action = lambda event: self.exit()
        self.add_widget(msgbox)

class FakePyPresence():
    def __init__(self):
        ...
    def update(self, *args, **kwargs):
        ...
    def close(self, *args, **kwargs):
        ...

class UIFocusTextureButton(arcade.gui.UITextureButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        arcade.gui.bind(self, "hovered", self.on_hover)

    def on_hover(self):
        if self.hovered:
            self.resize(width=self.width * 1.1, height=self.height * 1.1)
        else:
            self.resize(width=self.width / 1.1, height=self.height / 1.1)

# Thanks to Eruvanos for the MouseAwareScrollArea and the UIMouseOutOfAreaEvent
class UIMouseOutOfAreaEvent(arcade.gui.UIEvent):
    """Indicates that the mouse is outside a specific area."""
    pass

class MouseAwareScrollArea(UIScrollArea):
    """Keep track of mouse position, None if outside of area."""
    mouse_inside = False
    def on_event(self, event: arcade.gui.UIEvent):
        if isinstance(event, arcade.gui.UIMouseMovementEvent):
            if self.rect.point_in_rect(event.pos):
                if not self.mouse_inside:
                    self.mouse_inside = True
            else:
                if self.mouse_inside:
                    self.mouse_inside = False
                    self.dispatch_ui_event(UIMouseOutOfAreaEvent(self))

        return super().on_event(event)
    
class MusicItem(arcade.gui.UIBoxLayout):
    def __init__(self, metadata: dict, width: int, height: int, padding=10):
        super().__init__(width=width, height=height, space_between=padding, align="top")

        self.metadata = metadata
        if metadata:
            self.button = self.add(arcade.gui.UITextureButton(
                texture=metadata["thumbnail"],
                texture_hovered=metadata["thumbnail"],
                width=width / 1.25,
                height=height * 0.5,
                interaction_buttons=[arcade.MOUSE_BUTTON_LEFT, arcade.MOUSE_BUTTON_RIGHT]
            ))

            self.title_label = self.add(arcade.gui.UILabel(
                text=metadata["title"],
                font_name="Roboto",
                font_size=14,
                width=width,
                height=height * 0.5,
                multiline=True
            ))

            self.artist_label = self.add(arcade.gui.UILabel(
                text=metadata["artist"],
                font_name="Roboto",
                font_size=12,
                width=width,
                height=height * 0.5,
                multiline=True,
                text_color=arcade.color.GRAY
            ))

            self.play_button = self.add(arcade.gui.UITextureButton(
                texture=resume_icon,
                texture_hovered=resume_icon,
                width=width / 10,
                height=height / 5,
                interaction_buttons=[arcade.MOUSE_BUTTON_LEFT, arcade.MOUSE_BUTTON_RIGHT]
            ))
            self.play_button.visible = False

        else:
            self.button = self.add(arcade.gui.UITextureButton(
                texture=music_icon,
                texture_hovered=music_icon,
                width=width / 1.25,
                height=height * 0.5,
            ))

            self.add_music_label = self.add(arcade.gui.UILabel(
                text="Add Music",
                font_name="Roboto",
                font_size=14,
                width=width,
                height=height * 0.5,
                multiline=True
            ))

    def on_event(self, event: arcade.gui.UIEvent):
        if self.metadata:
            if isinstance(event, UIMouseOutOfAreaEvent):
                # not hovering
                self.with_background(color=arcade.color.TRANSPARENT_BLACK)
                self.play_button.visible = False
                self.trigger_full_render()

            elif isinstance(event, arcade.gui.UIMouseMovementEvent):
                if self.rect.point_in_rect(event.pos):
                    # hovering
                    self.with_background(color=arcade.color.DARK_GRAY)
                    self.play_button.visible = True
                    self.trigger_full_render()
                else:
                    # not hovering
                    self.with_background(color=arcade.color.TRANSPARENT_BLACK)
                    self.play_button.visible = False
                    self.trigger_full_render()

            elif isinstance(event, arcade.gui.UIMousePressEvent) and self.rect.point_in_rect(event.pos):
                self.button.on_click(event)

        return super().on_event(event)

def on_exception(*exc_info):
    logging.error(f"Unhandled exception:\n{''.join(traceback.format_exception(exc_info[1], limit=None))}")

def get_closest_resolution():
    allowed_resolutions = [(1366, 768), (1440, 900), (1600,900), (1920,1080), (2560,1440), (3840,2160)]
    screen_width, screen_height = arcade.get_screens()[0].width, arcade.get_screens()[0].height
    if (screen_width, screen_height) in allowed_resolutions:
        if not allowed_resolutions.index((screen_width, screen_height)) == 0:
            closest_resolution = allowed_resolutions[allowed_resolutions.index((screen_width, screen_height))-1]
        else:
            closest_resolution = (screen_width, screen_height)
    else:
        target_width, target_height = screen_width // 2, screen_height // 2

        closest_resolution = min(
            allowed_resolutions,
            key=lambda res: abs(res[0] - target_width) + abs(res[1] - target_height)
        )
    return closest_resolution

def convert_seconds_to_date(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    result = ""
    if days > 0:
        result += "{} days ".format(int(days))
    if hours > 0:
        result += "{} hours ".format(int(hours))
    if minutes > 0:
        result += "{} minutes ".format(int(minutes))
    if seconds > 0 or not any([days, hours, minutes]):
        result += "{} seconds".format(int(seconds))

    return result.strip()