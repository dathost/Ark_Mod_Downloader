import os
import shutil
import tempfile
import unittest

from ark_mod_downloader import ArkModDownloader
from collections import OrderedDict

# The ARK client includes actual mod name in the .mod file, the server seem to work without it,
# but if we get problems in the future we could look into getting it using steam API
MODS = [
    ("632898827", "Dino Colors Plus"),
    ("679529026", "Ark Steampunk Mod"),
    ("1984936918", "MarniiMods: Wildlife"),
    ("2069758213", "Metallic Dodos Mod"),
    ("2777653985", "RR-StarRainbowDinos"),
]


class TestArk(unittest.TestCase):
    def setUp(self) -> None:
        source_dir = tempfile.TemporaryDirectory()
        destination_dir = tempfile.TemporaryDirectory()
        self.addCleanup(source_dir.cleanup)
        self.addCleanup(destination_dir.cleanup)
        self.source_path = source_dir.name
        self.destination_path = destination_dir.name
        self.mod_file_dir = os.path.join(
            self.destination_path, "ShooterGame", "Content", "Mods"
        )
        os.makedirs(self.mod_file_dir)

    def new_downloader(self) -> ArkModDownloader:
        downloader = ArkModDownloader.__new__(ArkModDownloader)
        downloader.map_names = []
        downloader.meta_data = OrderedDict([])
        downloader.temp_mod_path = self.source_path
        downloader.workingdir = self.destination_path
        return downloader

    def stage_mod(self, modid: str) -> None:
        mod_info_dir = os.path.join(self.source_path, modid, "WindowsNoEditor")
        os.makedirs(mod_info_dir)
        for filename in ("mod.info", "modmeta.info"):
            shutil.copyfile(
                "tests/fixtures/ark_mods/%s/%s" % (modid, filename),
                os.path.join(mod_info_dir, filename),
            )

    def assert_mod_file_matches_fixture(self, modid: str) -> None:
        with open(os.path.join(self.mod_file_dir, modid + ".mod"), "rb") as f:
            actual = f.read()

        with open("tests/fixtures/ark_mods/%s.mod" % modid, "rb") as f:
            expected = f.read()

        self.assertEqual(actual, expected, "%s.mod differs from fixture" % modid)

    def test_should_write_mod_files(self) -> None:
        for modid, mod_name in MODS:
            self.stage_mod(modid)
            self.new_downloader().create_mod_file(modid, mod_name=mod_name)  # type: ignore
            self.assert_mod_file_matches_fixture(modid)

    def test_should_only_list_own_maps_when_installing_several_mods(self) -> None:
        downloader = self.new_downloader()
        for modid, mod_name in MODS:
            self.stage_mod(modid)
            downloader.create_mod_file(modid, mod_name=mod_name)  # type: ignore

        for modid, _ in MODS:
            self.assert_mod_file_matches_fixture(modid)
