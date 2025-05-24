import arcade, arcade.gui

import os, sys, subprocess, platform, urllib.request, zipfile, logging

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
                buttons=("Exit", "Auto Install")
            )
        )

        msgbox.on_action = lambda event: self.install_ffmpeg() if event.action == "Auto Install" else sys.exit()

    def install_ffmpeg(self):
        bin_dir = os.path.join(os.getcwd(), "bin")
        os.makedirs(bin_dir, exist_ok=True)

        system = platform.system()

        if system == "Linux" or system == "Darwin":
            url = "https://evermeet.cx/ffmpeg/ffmpeg-7.1.1.zip"
            filename = "ffmpeg.zip"

            logging.debug(f"Downloading FFmpeg from {url}...")
            file_path = os.path.join(bin_dir, filename)
            urllib.request.urlretrieve(url, file_path)

            logging.debug("Extracting FFmpeg...")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(bin_dir)
            ffmpeg_path = os.path.join(bin_dir, "ffmpeg")
            os.chmod(ffmpeg_path, 0o755)

            os.remove(file_path)
            logging.debug("FFmpeg installed in ./bin")

        elif system == "Windows":
            try:
                subprocess.run([
                    "winget", "install", "--id=Gyan.FFmpeg", "--scope=user",
                    "--accept-source-agreements", "--accept-package-agreements"
                ], check=True)
                logging.debug("FFmpeg installed via winget.")
            except subprocess.CalledProcessError as e:
                logging.debug("Failed to install FFmpeg via winget:", e)

        else:
            logging.error(f"Unsupported OS: {system}")

        from menus.main import Main
        self.window.show_view(Main())
