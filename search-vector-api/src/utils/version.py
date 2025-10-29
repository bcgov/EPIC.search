"""Simple release version helper for the Vector API."""
from pathlib import Path


_RELEASE_FILE = Path(__file__).with_name("release.properties")


def _read_version():
    if not _RELEASE_FILE.exists():
        return "0.0.0"

    with _RELEASE_FILE.open("r", encoding="utf-8") as prop_file:
        for raw_line in prop_file:
            line = raw_line.strip()
            if line.startswith("version="):
                return line.split("=", 1)[1].strip()

    return "0.0.0"


__version__ = _read_version()


def get_version():
    """Expose the current release identifier."""
    return __version__
