import arcade.gui, arcade

button_texture = arcade.gui.NinePatchTexture(64 // 4, 64 // 4, 64 // 4, 64 // 4, arcade.load_texture("assets/graphics/button.png"))
button_hovered_texture = arcade.gui.NinePatchTexture(64 // 4, 64 // 4, 64 // 4, 64 // 4, arcade.load_texture("assets/graphics/button_hovered.png"))

pause_icon = arcade.load_texture("assets/graphics/pause.png")
resume_icon = arcade.load_texture("assets/graphics/resume.png")

stop_icon = arcade.load_texture("assets/graphics/stop.png")
loop_icon = arcade.load_texture("assets/graphics/loop.png")
no_loop_icon = arcade.load_texture("assets/graphics/no_loop.png")

shuffle_icon = arcade.load_texture("assets/graphics/shuffle.png")
no_shuffle_icon = arcade.load_texture("assets/graphics/no_shuffle.png")

settings_icon = arcade.load_texture("assets/graphics/settings.png")
reload_icon = arcade.load_texture("assets/graphics/reload.png")
download_icon = arcade.load_texture("assets/graphics/download.png")
plus_icon = arcade.load_texture("assets/graphics/plus.png")
playlist_icon = arcade.load_texture("assets/graphics/playlist.png")
files_icon = arcade.load_texture("assets/graphics/files.png")

music_icon = arcade.load_texture("assets/graphics/music.png")
