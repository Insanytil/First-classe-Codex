"""Trois emplacements, écriture temporaire synchronisée puis remplacement atomique."""

import os
import tempfile
from pathlib import Path

from JRPG.application.save_data import GameSnapshot
from JRPG.application.saves import SaveError
from JRPG.infrastructure.save_codec import SaveCodec


class JsonSaveRepository:
    SLOT_COUNT = 3

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._codec = SaveCodec()

    def _path(self, slot: int) -> Path:
        if type(slot) is not int or not 1 <= slot <= self.SLOT_COUNT:
            raise SaveError("Emplacement compris entre 1 et 3 attendu.")
        return self.directory / f"slot-{slot}.json"

    def exists(self, slot: int) -> bool:
        return self._path(slot).is_file()

    def read(self, slot: int) -> GameSnapshot:
        try:
            return self._codec.decode(self._path(slot).read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as error:
            raise SaveError(f"Lecture de l'emplacement {slot} impossible : {error}") from error

    def write(self, slot: int, snapshot: GameSnapshot) -> None:
        target = self._path(slot)
        source = self._codec.encode(snapshot)
        temporary: Path | None = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(
                prefix=f".slot-{slot}-", suffix=".tmp", dir=self.directory
            )
            temporary = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(source)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        except OSError as error:
            raise SaveError(f"Écriture de l'emplacement {slot} impossible : {error}") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def default_save_directory() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / "technobel-jrpg" / "saves"
