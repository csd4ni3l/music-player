import os, platform, tarfile, acoustid, urllib.request, shutil, gzip, glob, logging, sys, io

from utils.constants import ACOUSTID_API_KEY

from zipfile import ZipFile

def get_fpcalc_name():
    system = platform.system()
    if system == "Linux" or system == "Darwin":
        return "fpcalc"
    elif system == "Windows":
        return "fpcalc.exe"

def get_fpcalc_path():
    return os.path.join(os.getcwd(), "bin", get_fpcalc_name())

def download_fpcalc():
    system = platform.system()
    architecture = platform.machine()

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

def get_recording_id_from_acoustic(filename):
    os.environ["FPCALC"] = get_fpcalc_path()

    try:
        results = acoustid.match(ACOUSTID_API_KEY, filename, meta=['recordings'], force_fpcalc=True, parse=False)["results"]
    except acoustid.NoBackendError:
        logging.debug("ChromaPrint library/tool not found")
        return None, None
    except acoustid.FingerprintGenerationError:
        logging.debug("Fingerprint could not be calculated")
        return None, None
    except acoustid.WebServiceError as exc:
        logging.debug(f"Web service request failed: {exc}")
        return None, None

    if not results:
        return None, None

    result = results[0]

    return result["id"], result["recordings"][0]["id"]