"""Contrat des fichiers PNG et du manifeste, sans installer Pygame."""
import struct
import unittest
from pathlib import Path

from poo.graphics.resources import ASSET_ROOT, DIRECTIONS, manifest, sheet
from poo.graphics.world import REGIONS
from poo.characters.jobs import JOBS, WEAPONS


class AssetTests(unittest.TestCase):
    def test_class_layers_and_weapon_attachment_points_are_complete(self):
        for class_id in JOBS:
            for action in (False, True):
                name = 'class_' + class_id + ('_action' if action else '')
                body, hair = sheet(name), sheet(name + '_hair')
                self.assertEqual(body.cell, hair.cell)
                self.assertEqual((body.columns, body.rows), (8, 1) if action else (4, 4))
                self.assertEqual((body.columns, body.rows), (hair.columns, hair.rows))
                hands = manifest()['sprites'][name]['hands']
                self.assertEqual(len(hands), body.columns * body.rows)
                self.assertEqual(len(body.anchors), len(hands))
                for x, y, angle in hands:
                    self.assertTrue(0 <= x < body.cell[0], name)
                    self.assertTrue(0 <= y < body.cell[1], name)
                    self.assertTrue(-180 <= angle <= 180)
        for weapon in WEAPONS:
            name = 'weapon_' + weapon
            specification = sheet(name)
            x, y = manifest()['sprites'][name]['grip']
            self.assertTrue(0 < x < specification.cell[0])
            self.assertTrue(0 < y < specification.cell[1])

    def test_png_dimensions_match_manifest(self):
        self.assertEqual(manifest()['version'], 1)
        for name in manifest()['sprites']:
            specification = sheet(name)
            with specification.path.open('rb') as image:
                header = image.read(29)
            self.assertEqual(header[:8], b'\x89PNG\r\n\x1a\n', name)
            width, height, depth, color, _, _, interlaced = struct.unpack('>IIBBBBB', header[16:29])
            self.assertEqual((width, height), (specification.cell[0] * specification.columns,
                                             specification.cell[1] * specification.rows), name)
            self.assertEqual((depth, color, interlaced), (8, 6, 0), name)
            self.assertTrue(all(value > 0 for value in specification.display_size))
            self.assertTrue(specification.path.is_relative_to(ASSET_ROOT))

    def test_all_world_objects_have_assets(self):
        actors = {'mira', 'merchant', 'traveler', 'wolf', 'flan', 'boss'}
        for region in REGIONS.values():
            for obj in region.objects:
                specification = sheet(obj.kind)
                self.assertTrue(specification.path.is_file(), obj.kind)
                if obj.kind in actors:
                    self.assertGreaterEqual(specification.columns, 4)
        self.assertGreaterEqual(sheet('gate').columns, 2)
        self.assertEqual(sheet('terrain').display_size, (48, 48))
        terrain_codes = {code for region in REGIONS.values() for row in region.terrain for code in row}
        self.assertTrue(terrain_codes <= set(manifest()['sprites']['terrain']['terrain_order']))

    def test_hero_layers_have_matching_animation_grid(self):
        body, hair = sheet('hero_body'), sheet('hero_hair')
        self.assertEqual(body.cell, hair.cell)
        self.assertEqual((body.columns, body.rows), (4, 4))
        self.assertEqual((body.columns, body.rows), (hair.columns, hair.rows))
        self.assertEqual(body.display_size, hair.display_size)
        self.assertEqual(body.display_size, (64, 80))
        self.assertEqual(body.directions, DIRECTIONS)
        self.assertEqual(body.directions, hair.directions)

    def test_animation_coordinates_never_escape_the_image(self):
        for name in manifest()['sprites']:
            specification = sheet(name)
            x, y, width, height = specification.rectangle(specification.columns - 1, specification.rows - 1)
            self.assertEqual(x + width, width * specification.columns)
            self.assertEqual(y + height, height * specification.rows)
            with self.assertRaises(ValueError):
                specification.rectangle(specification.columns)
            with self.assertRaises(ValueError):
                specification.rectangle(-1)

    def test_resources_do_not_depend_on_working_directory(self):
        self.assertTrue(ASSET_ROOT.is_absolute())
        self.assertEqual(ASSET_ROOT, Path(__file__).resolve().parents[1] / 'assets')
        self.assertTrue((ASSET_ROOT / 'manifest.json').is_file())

    def test_attack_sheets_have_eight_poses_and_explicit_anchors(self):
        for name in ('hero_sword', 'hero_sword_hair', 'wolf_claw', 'slime_jump'):
            specification = sheet(name)
            self.assertEqual(specification.columns * specification.rows, 8)
            self.assertEqual(len(specification.anchors), 8)
            for x, y in specification.anchors:
                self.assertTrue(0 <= x <= specification.cell[0])
                self.assertTrue(0 <= y <= specification.cell[1])
        body, hair = sheet('hero_sword'), sheet('hero_sword_hair')
        self.assertEqual(body.cell, hair.cell)
        self.assertEqual(body.anchors, hair.anchors)
        self.assertEqual(body.display_size, hair.display_size)

    def test_prologue_uses_dedicated_cloud_sephiroth_and_village_assets(self):
        for name in ('cloud', 'sephiroth'):
            specification = sheet(name)
            self.assertEqual(specification.columns * specification.rows, 4)
            self.assertEqual(len(specification.anchors), 4)
        village = sheet('nibelheim')
        self.assertEqual((village.columns, village.rows), (1, 1))
        self.assertGreater(village.cell[0], 1000)

    def test_all_regions_and_battle_use_large_painted_backdrops(self):
        for place in REGIONS:
            specification = sheet('map_' + place)
            self.assertEqual((specification.columns, specification.rows), (1, 1))
            self.assertGreaterEqual(specification.cell[0], 1200)
            self.assertEqual(specification.display_size, (912, 576))
        self.assertEqual(sheet('map_gate_open').display_size, sheet('map_gate').display_size)
        self.assertEqual(sheet('battle_dalmasca').display_size, (912, 442))
