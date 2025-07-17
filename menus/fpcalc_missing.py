import arcade, arcade.gui, sys, gzip, platform, tarfile, urllib.request, os, io, glob, shutil

from zipfile import ZipFile

from utils.acoustid_metadata import get_fpcalc_path, get_fpcalc_name

class FpcalcMissing(arcade.gui.UIView):
    def __init__(self):
        super().__init__()

    def on_show_view(self):
        super().on_show_view()

        msgbox = self.add_widget(arcade.gui.UIMessageBox(width=self.window.width / 2, height=self.window.height / 2, title="Third-party fpcalc download", message_text="We need to download fpcalc from AcoustID to recognize the song for you for better results.\nIf you say no, we will use a searching algorithm instead which might give wrong results.\nEven if fpcalc is downloaded, it might not find the music since its a community-based project.\nIf so, we will fallback to the searching algorithm.\nDo you want to continue?", buttons=("Yes", "No")))
        msgbox.on_action = lambda event: self.download_fpcalc() if event.action == "Yes" else self.exit()

    def download_fpcalc(self):
        system = platform.system()
        architecture = platform.machine()

        os.makedirs("bin", exist_ok=True)

        if system == "Linux":
            url = "https://github.com/acoustid/chromaprint/releases/download/v1.5.1/chromaprint-fpcalc-1.5.1-linux-x86_64.tar.gz"
        elif system == "Darwin":
            if architecture.lower() == "x86_64" or architecture.lower() == "amd64":
                url = "https://github.com/acoustid/chromaprint/releases/download/v1.5.1/chromaprint-fpcalc-1.5.1-macos-x86_64.tar.gz"
            else:
                url = "https://github.com/acoustid/chromaprint/releases/download/v1.5.1/chromaprint-fpcalc-1.5.1-macos-arm64.tar.gz"
        elif system == "Windows":
            url = "https://github.com/acoustid/chromaprint/releases/download/v1.5.1/chromaprint-fpcalc-1.5.1-windows-x86_64.zip"

        if url.endswith(".zip"):
            zip_path = os.path.join(os.getcwd(), "bin", "chromaprint.zip")
            urllib.request.urlretrieve(url, zip_path)
            with ZipFile(zip_path) as file:
                file.extractall(os.path.join(os.getcwd(), "bin"))

            os.remove(zip_path)
        else:
            tar_gz_path = os.path.join(os.getcwd(), "bin", "chromaprint.tar.gz")
            urllib.request.urlretrieve(url, tar_gz_path)

            with gzip.open(tar_gz_path, "rb") as f: # For some reason, tarfile by itself didnt work for tar.gz so i have to uncompress with gzip first and then with tarfile
                with tarfile.open(fileobj=io.BytesIO(f.read())) as tar:
                    tar.extractall(os.path.join(os.getcwd(), "bin"))

            os.remove(tar_gz_path)
                    
        chromaprint_matches = glob.glob(os.path.join("bin", "chromaprint*"))
        if chromaprint_matches:
            shutil.move(os.path.join(chromaprint_matches[0], get_fpcalc_name()), os.path.join("bin", get_fpcalc_name()))
            shutil.rmtree(chromaprint_matches[0])

        os.chmod(get_fpcalc_path(), 0o755)

        self.exit()

    def exit(self):
        from menus.main import Main
        self.window.show_view(Main())