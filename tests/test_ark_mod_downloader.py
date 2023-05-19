import os
import shutil
import tempfile
import unittest

from ark_mod_downloader import ArkModDownloader
from collections import OrderedDict


class TestArk(unittest.TestCase):
    def compare_mod_file(self, modid: str, mod_name: str) -> None:
        with tempfile.TemporaryDirectory() as source_path, tempfile.TemporaryDirectory() as destination_path:
            mod_info_dir = os.path.join(source_path, modid, "WindowsNoEditor")
            os.makedirs(mod_info_dir)
            shutil.copyfile(
                "tests/fixtures/ark_mods/%s/mod.info" % modid,
                mod_info_dir + "/mod.info",
            )
            shutil.copyfile(
                "tests/fixtures/ark_mods/%s/modmeta.info" % modid,
                mod_info_dir + "/modmeta.info",
            )

            mod_file_dir = os.path.join(
                destination_path, "ShooterGame", "Content", "Mods"
            )
            os.makedirs(mod_file_dir)

            ArkModDownloader.__init__ = lambda self: None  # type: ignore
            downloader = ArkModDownloader()  # type: ignore
            downloader.map_names = []
            downloader.meta_data = OrderedDict([])
            downloader.temp_mod_path = source_path
            downloader.workingdir = destination_path
            downloader.create_mod_file(modid, mod_name=mod_name)  # type: ignore

            with open(os.path.join(mod_file_dir, modid + ".mod"), "rb") as f:
                actual = f.read()

            with open("tests/fixtures/ark_mods/%s.mod" % modid, "rb") as f:
                expected = f.read()

            assert actual == expected

    def test_should_write_mod_files(self) -> None:
        # The ARK client includes actual mod name in the .mod file, the server seem to work without it,
        # but if we get problems in the future we could look into getting it using steam API
        self.compare_mod_file("632898827", "Dino Colors Plus")
        self.compare_mod_file("679529026", "Ark Steampunk Mod")
        self.compare_mod_file("1984936918", "MarniiMods: Wildlife")
        self.compare_mod_file("2069758213", "Metallic Dodos Mod")
        self.compare_mod_file("2777653985", "RR-StarRainbowDinos")
