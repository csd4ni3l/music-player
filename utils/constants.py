import arcade.color
from arcade.types import Color
from arcade.gui.widgets.buttons import UIFlatButtonStyle
from arcade.gui.widgets.slider import UISliderStyle

menu_background_color = (17, 17, 17)
log_dir = 'logs'
discord_presence_id = 1368277020332523530

audio_extensions = ["mp3", "m4a", "aac", "flac", "ogg", "opus", "wav"]

view_modes = ["files", "playlist"]

DARK_GRAY = Color(45, 45, 45)
GRAY = Color(70, 70, 70)
LIGHT_GRAY = Color(150, 150, 150)
PRIMARY = Color(0, 189, 126)
PRIMARY_DARK = Color(0, 145, 96)
DISABLED = Color(90, 90, 90)
FONT_COLOR = arcade.color.BLACK
FONT = "Roboto"
FONT_SIZE = 14
BIG_FONT_SIZE = 22

button_style = {
    "normal": UIFlatButtonStyle(font_name=FONT, font_size=FONT_SIZE, font_color=FONT_COLOR, bg=GRAY),
    "hover": UIFlatButtonStyle(font_name=FONT, font_size=FONT_SIZE, font_color=FONT_COLOR, bg=PRIMARY),
    "press": UIFlatButtonStyle(font_name=FONT, font_size=FONT_SIZE, font_color=FONT_COLOR, bg=PRIMARY_DARK),
    "disabled": UIFlatButtonStyle(font_name=FONT, font_size=FONT_SIZE, font_color=LIGHT_GRAY, bg=DISABLED),
}

big_button_style = {
    "normal": UIFlatButtonStyle(font_name=FONT, font_size=BIG_FONT_SIZE, font_color=FONT_COLOR, bg=GRAY),
    "hover": UIFlatButtonStyle(font_name=FONT, font_size=BIG_FONT_SIZE, font_color=FONT_COLOR, bg=PRIMARY),
    "press": UIFlatButtonStyle(font_name=FONT, font_size=BIG_FONT_SIZE, font_color=FONT_COLOR, bg=PRIMARY_DARK),
    "disabled": UIFlatButtonStyle(font_name=FONT, font_size=BIG_FONT_SIZE, font_color=LIGHT_GRAY, bg=DISABLED),
}

slider_default_style = UISliderStyle(
    bg=GRAY,
    unfilled_track=DARK_GRAY,
    filled_track=PRIMARY
)

slider_hover_style = UISliderStyle(
    bg=PRIMARY,
    unfilled_track=DARK_GRAY,
    filled_track=PRIMARY_DARK
)

slider_style = {
    "normal": slider_default_style,
    "hover": slider_hover_style,
    "press": slider_hover_style,
    "disabled": slider_default_style,
}

settings = {
    "Music": {
        "Default Volume": {"type": "slider", "min": 0, "max": 100, "config_key": "default_volume", "default": 100},
        "Audio Mode": {"type": "option", "options": ["Stream", "Preload"], "config_key": "audio_mode", "default": "Stream"},
        "Normalize Audio": {"type": "bool", "config_key": "normalize_audio", "default": True},
        "Normalized dBFS": {"type": "slider", "min": -30, "max": 0, "config_key": "normalized_volume", "default": -8},
    },
    "Graphics": {
        "Window Mode": {"type": "option", "options": ["Windowed", "Fullscreen", "Borderless"], "config_key": "window_mode", "default": "Windowed"},
        "Resolution": {"type": "option", "options": ["1366x768", "1440x900", "1600x900", "1920x1080", "2560x1440", "3840x2160"], "config_key": "resolution"},
        "Anti-Aliasing": {"type": "option", "options": ["None", "2x MSAA", "4x MSAA", "8x MSAA", "16x MSAA"], "config_key": "anti_aliasing", "default": "4x MSAA"},
        "VSync": {"type": "bool", "config_key": "vsync", "default": True},
        "FPS Limit": {"type": "slider", "min": 0, "max": 480, "config_key": "fps_limit", "default": 60},
    },
    "Miscellaneous": {
        "Discord RPC": {"type": "bool", "config_key": "discord_rpc", "default": True},
    },
    "Credits": {}
}

settings_start_category = "Music"
