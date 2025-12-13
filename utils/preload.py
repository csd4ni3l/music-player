import arcade.gui, arcade, os

# Get the directory where this module is located
_module_dir = os.path.dirname(os.path.abspath(__file__))
_assets_dir = os.path.join(os.path.dirname(_module_dir), 'assets')

button_texture = arcade.gui.NinePatchTexture(64 // 4, 64 // 4, 64 // 4, 64 // 4, arcade.load_texture(os.path.join(_assets_dir, "graphics", "button.png")))
button_hovered_texture = arcade.gui.NinePatchTexture(64 // 4, 64 // 4, 64 // 4, 64 // 4, arcade.load_texture(os.path.join(_assets_dir, "graphics", "button_hovered.png")))

loop_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "loop.png"))
no_loop_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "no_loop.png"))

shuffle_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "shuffle.png"))
no_shuffle_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "no_shuffle.png"))

pause_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "pause.png"))
resume_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "resume.png"))
forward_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "forward.png"))
backwards_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "backwards.png"))
volume_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "volume.png"))

person_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "person.png"))
music_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "music.png"))

global_search_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "global_search.png"))
settings_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "settings.png"))
download_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "download.png"))
metadata_icon = arcade.load_texture(os.path.join(_assets_dir, "graphics", "metadata.png"))
