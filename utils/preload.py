import arcade.gui, arcade

button_texture = arcade.gui.NinePatchTexture(64 // 4, 64 // 4, 64 // 4, 64 // 4, arcade.load_texture("assets/graphics/button.png"))
button_hovered_texture = arcade.gui.NinePatchTexture(64 // 4, 64 // 4, 64 // 4, 64 // 4, arcade.load_texture("assets/graphics/button_hovered.png"))

loop_icon = arcade.load_texture("assets/graphics/loop.png")
no_loop_icon = arcade.load_texture("assets/graphics/no_loop.png")

shuffle_icon = arcade.load_texture("assets/graphics/shuffle.png")
no_shuffle_icon = arcade.load_texture("assets/graphics/no_shuffle.png")

pause_icon = arcade.load_texture("assets/graphics/pause.png")
resume_icon = arcade.load_texture("assets/graphics/resume.png")
forward_icon = arcade.load_texture("assets/graphics/forward.png")
backwards_icon = arcade.load_texture("assets/graphics/backwards.png")
volume_icon = arcade.load_texture("assets/graphics/volume.png")

person_icon = arcade.load_texture("assets/graphics/person.png")
music_icon = arcade.load_texture("assets/graphics/music.png")

global_search_icon = arcade.load_texture("assets/graphics/global_search.png")
settings_icon = arcade.load_texture("assets/graphics/settings.png")
download_icon = arcade.load_texture("assets/graphics/download.png")
metadata_icon = arcade.load_texture("assets/graphics/metadata.png")
