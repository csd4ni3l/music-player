import arcade, arcade.gui

import os, sys, subprocess, platform, logging

class FFmpegMissing(arcade.gui.UIView):
    def __init__(self):
        super().__init__()

    def on_show_view(self):
        super().on_show_view()

        msgbox = self.add_widget(
            arcade.gui.UIMessageBox(
                width=self.window.width / 2,
                height=self.window.height / 2,
                title="FFmpeg Missing",
                message_text="FFmpeg has not been found but is required for this application.",
                buttons=("Exit", "Install")
            )
        )

        msgbox.on_action = lambda event: self.install_ffmpeg() if event.action == "Install" else sys.exit()

    def install_ffmpeg(self):
        bin_dir = os.path.join(os.getcwd(), "bin")
        os.makedirs(bin_dir, exist_ok=True)

        system = platform.system()

        if system == "Linux" or system == "Darwin":
            msgbox = self.add_widget(arcade.gui.UIMessageBox(message_text="You are on a Linux or Darwin based OS. You need to install FFmpeg, and libavcodec shared libraries from your package manager so it is in PATH.", width=self.window.width / 2, height=self.window.height / 2))
            msgbox.on_action = lambda: sys.exit()
            return

        elif system == "Windows":
            try:
                subprocess.run([
                    "winget", "install", "BtbN.FFmpeg.GPL.Shared.7.1",
                    "--accept-source-agreements", "--accept-package-agreements"
                ], check=True)
                logging.debug("FFmpeg installed via winget.")
                msgbox = self.add_widget(arcade.gui.UIMessageBox(message_text="You are on a Linux or Darwin based OS. You need to install FFmpeg, and libavcodec shared libraries from your package manager so it is in PATH.", width=self.window.width / 2, height=self.window.height / 2))
                msgbox.on_action = lambda: sys.exit()
                return

            except subprocess.CalledProcessError as e:
                logging.debug("Failed to install FFmpeg via winget:", e)

        else:
            self.add_widget(arcade.gui.UIMessageBox(message_text="Your OS is unsupported by this script. You are probably on some kind of BSD system. Please install FFmpeg and libavcodec shared libraries from your package manager so it is in PATH.", width=self.window.width / 2, height=self.window.height / 2))
