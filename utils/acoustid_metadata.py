import os, platform, acoustid, logging

from utils.constants import ACOUSTID_API_KEY

def get_fpcalc_name():
    system = platform.system()
    if system == "Linux" or system == "Darwin":
        return "fpcalc"
    elif system == "Windows":
        return "fpcalc.exe"

def get_fpcalc_path():
    return os.path.join(os.getcwd(), "bin", get_fpcalc_name())

def get_recording_id_from_acoustid(filename):
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