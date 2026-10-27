"""Chargement des PNG, découpage des animations et coloration des cheveux."""
from functools import lru_cache

import pygame as pg

from poo.graphics.character import DEFAULT_HAIR
from poo.graphics.resources import sheet
from poo.graphics.resources import manifest
from poo.characters.jobs import WEAPONS


@lru_cache(maxsize=None)
def _image(name: str):
    specification = sheet(name)
    try:
        image = pg.image.load(str(specification.path))
    except (OSError, pg.error) as error:
        raise RuntimeError(f'Impossible de charger la ressource {specification.path.name}') from error
    width, height = specification.cell
    expected = (width * specification.columns, height * specification.rows)
    if image.get_size() != expected:
        raise RuntimeError(f'Dimensions incorrectes pour {specification.path.name} : {image.get_size()} au lieu de {expected}')
    return image.convert_alpha() if pg.display.get_surface() is not None else image


@lru_cache(maxsize=256)
def _frame(name: str, column: int = 0, row: int = 0):
    specification = sheet(name)
    return _image(name).subsurface(specification.rectangle(column, row)).copy()


def _resize(image, size):
    return image if image.get_size() == size else pg.transform.smoothscale(image, size)


@lru_cache(maxsize=256)
def actor(kind='hero', frame=0, facing='down', hair_color=DEFAULT_HAIR, *, size=None):
    name = 'hero_body' if kind == 'hero' else kind
    specification = sheet(name)
    directions = specification.directions
    row = directions.index(facing) if facing in directions else 0
    row = min(row, specification.rows - 1)
    column = frame % specification.columns
    image = _frame(name, column, row)
    if kind == 'hero':
        image = image.copy()
        hair = _frame('hero_hair', column, row).copy()
        # Les cheveux du PNG sont en gris ; cette multiplication préserve leurs
        # ombres et leur transparence sans recolorer le visage ou les vêtements.
        hair.fill((*hair_color, 255), special_flags=pg.BLEND_RGBA_MULT)
        image.blit(hair, (0, 0))
    return _resize(image, size or specification.display_size)


@lru_cache(maxsize=64)
def prop(kind, frame=0, opened=False):
    specification = sheet(kind)
    column = int(opened) if kind == 'gate' else frame % specification.columns
    return _resize(_frame(kind, column), specification.display_size)


@lru_cache(maxsize=16)
def effect(name='fire_projectile', frame=0):
    specification = sheet(name)
    return _resize(_frame(name, frame % specification.columns), specification.display_size)


@lru_cache(maxsize=128)
def animation(name: str, frame: int = 0, hair_color=DEFAULT_HAIR, *, size=None):
    """Image d'action et point d'ancrage des pieds, à la taille d'affichage."""
    specification = sheet(name)
    index = min(max(0, frame), specification.columns * specification.rows - 1)
    column, row = index % specification.columns, index // specification.columns
    image = _frame(name, column, row)
    if name == 'hero_sword':
        image = image.copy()
        hair = _frame('hero_sword_hair', column, row).copy()
        hair.fill((*hair_color, 255), special_flags=pg.BLEND_RGBA_MULT)
        image.blit(hair, (0, 0))
    output_size = size or specification.display_size
    anchor_x, anchor_y = specification.anchor(column, row)
    anchor = (anchor_x * output_size[0] / specification.cell[0],
              anchor_y * output_size[1] / specification.cell[1])
    return _resize(image, output_size), anchor


@lru_cache(maxsize=16)
def backdrop(name: str, size: tuple[int, int]):
    return _resize(_frame(name), size)


@lru_cache(maxsize=8)
def portrait(kind: str, *, size=(112, 128)):
    name = 'portrait_' + kind
    return _resize(_frame(name), size)


@lru_cache(maxsize=64)
def weapon_icon(weapon_id: str, size=(64, 80)):
    return _resize(_frame('weapon_' + weapon_id), size)


@lru_cache(maxsize=256)
def _held_weapon(weapon_id: str, angle: float):
    name = 'weapon_' + weapon_id
    specification = sheet(name)
    data = manifest()['sprites'][name]
    source = _frame(name)
    height = {'sword': 150, 'staff': 240, 'bow': 195, 'hammer': 160}[WEAPONS[weapon_id].family]
    ratio = height / specification.cell[1]
    source = _resize(source, (round(specification.cell[0] * ratio), height))
    grip = pg.Vector2(data['grip']) * ratio
    relative = grip - pg.Vector2(source.get_size()) / 2
    rotated = pg.transform.rotate(source, angle)
    pivot = pg.Vector2(rotated.get_size()) / 2 + relative.rotate(-angle)
    return rotated, pivot


@lru_cache(maxsize=512)
def player(class_id='warrior', weapon_id='iron_sword', frame=0, facing='down',
           hair_color=DEFAULT_HAIR, *, size=None, action=False):
    """Tenue, cheveux et arme indépendants, attachés à la main de chaque pose."""
    name = 'class_' + class_id + ('_action' if action else '')
    specification = sheet(name)
    column = frame % specification.columns
    row = 0 if action else specification.directions.index(facing)
    index = row * specification.columns + column
    data = manifest()['sprites'][name]
    body = _frame(name, column, row)
    image = pg.Surface(body.get_size(), pg.SRCALPHA)
    hand_x, hand_y, angle = data['hands'][index]
    weapon, pivot = _held_weapon(weapon_id, angle)
    location = (round(hand_x - pivot.x), round(hand_y - pivot.y))
    if facing == 'up' and not action:
        image.blit(weapon, location)
        image.blit(body, (0, 0))
    else:
        image.blit(body, (0, 0))
        image.blit(weapon, location)
    hair = _frame(name + '_hair', column, row).copy()
    hair.fill((*hair_color, 255), special_flags=pg.BLEND_RGBA_MULT)
    image.blit(hair, (0, 0))
    output = size or specification.display_size
    return _resize(image, output)


def player_action(hero, frame, hair_color):
    name = 'class_' + hero.class_id + '_action'
    specification = sheet(name)
    image = player(hero.class_id, hero.weapon_id, frame, 'right', hair_color, action=True)
    x, y = specification.anchor(frame)
    return image, (x * image.get_width() / specification.cell[0],
                   y * image.get_height() / specification.cell[1])
