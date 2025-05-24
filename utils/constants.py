import arcade.color
from arcade.types import Color
from arcade.gui.widgets.buttons import UITextureButtonStyle, UIFlatButtonStyle
from arcade.gui.widgets.slider import UISliderStyle

menu_background_color = (17, 17, 17)
log_dir = 'logs'
discord_presence_id = 1368277020332523530

audio_extensions = [
    "3g2", "3gp", "aac", "ac3", "aiff", "alac", "amr", "ape", "au", "caf",
    "dts", "flac", "gsm", "m4a", "mka", "mlp", "mmf", "mp2", "mp3",
    "oga", "ogg", "opus", "ra", "rm", "sln", "tta", "vorbis", "voc", "vox",
    "wav", "webm", "wma", "wv"
]

yt_dlp_parameters = {
  "final_ext": "mp3",
  "format": "bestaudio/best",
  "outtmpl": {"pl_thumbnail": "", "default": "downloaded_music.mp3"},
  "postprocessors": [
    {
      "key": "FFmpegExtractAudio",
      "nopostoverwrites": False,
      "preferredcodec": "mp3",
      "preferredquality": "5"
    },
    {
      "add_chapters": True,
      "add_infojson": "if_exists",
      "add_metadata": True,
      "key": "FFmpegMetadata"
    },
    { "already_have_thumbnail": False, "key": "EmbedThumbnail" }
  ],
  "writethumbnail": True
}

button_style = {'normal': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK), 'hover': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK),
                'press': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK), 'disabled': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK)}
big_button_style = {'normal': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK, font_size=26), 'hover': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK, font_size=26),
                'press': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK, font_size=26), 'disabled': UITextureButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK, font_size=26)}

dropdown_style = {'normal': UIFlatButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK, bg=Color(128, 128, 128)), 'hover': UIFlatButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK, bg=Color(49, 154, 54)),
                  'press': UIFlatButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK, bg=Color(128, 128, 128)), 'disabled': UIFlatButtonStyle(font_name="Protest Strike", font_color=arcade.color.BLACK, bg=Color(128, 128, 128))}

slider_default_style = UISliderStyle(bg=Color(128, 128, 128), unfilled_track=Color(128, 128, 128), filled_track=Color(49, 154, 54))
slider_hover_style = UISliderStyle(bg=Color(49, 154, 54), unfilled_track=Color(128, 128, 128), filled_track=Color(49, 154, 54))

slider_style = {'normal': slider_default_style, 'hover': slider_hover_style, 'press': slider_hover_style, 'disabled': slider_default_style}

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
