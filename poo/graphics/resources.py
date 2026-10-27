"""Descriptions des fichiers graphiques, sans dépendance à Pygame."""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

ASSET_ROOT = Path(__file__).resolve().parents[2] / 'assets'
DIRECTIONS = ('down', 'left', 'up', 'right')


@dataclass(frozen=True)
class SpriteSheet:
    path: Path
    cell: tuple[int, int]
    columns: int
    rows: int
    display_size: tuple[int, int]
    directions: tuple[str, ...]
    anchors: tuple[tuple[float, float], ...] = ()

    def rectangle(self, column: int, row: int = 0) -> tuple[int, int, int, int]:
        if not 0 <= column < self.columns or not 0 <= row < self.rows:
            raise ValueError(f'Image hors de la planche : {self.path.name}')
        width, height = self.cell
        return column * width, row * height, width, height

    def anchor(self, column: int, row: int = 0) -> tuple[float, float]:
        self.rectangle(column, row)
        if self.anchors:
            return self.anchors[row * self.columns + column]
        return self.cell[0] / 2, self.cell[1] * .95


@lru_cache(maxsize=1)
def manifest() -> dict:
    return json.loads((ASSET_ROOT / 'manifest.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=None)
def sheet(name: str) -> SpriteSheet:
    data = manifest()['sprites'][name]
    cell = tuple(data['cell'])
    display_size = tuple(data.get('display_size', [value * manifest()['scale'] for value in cell]))
    return SpriteSheet(ASSET_ROOT / data['file'], cell, data['columns'], data['rows'],
                       display_size, tuple(data.get('directions', DIRECTIONS)),
                       tuple(tuple(point) for point in data.get('anchors', ())))
