import json
import os
import shutil
import struct
import tempfile
import unittest
from unittest import mock

from ark_mod_downloader import ArkModDownloader

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
        downloader.temp_mod_path = self.source_path
        downloader.workingdir = self.destination_path
        return downloader

    def stage_mod(self, modid: str, mod_dir: str = "") -> str:
        mod_dir = mod_dir or os.path.join(self.source_path, modid, "WindowsNoEditor")
        os.makedirs(mod_dir)
        for filename in ("mod.info", "modmeta.info"):
            shutil.copyfile(
                "tests/fixtures/ark_mods/%s/%s" % (modid, filename),
                os.path.join(mod_dir, filename),
            )
        return mod_dir

    def read_mod_file(self, modid: str) -> bytes:
        with open(os.path.join(self.mod_file_dir, modid + ".mod"), "rb") as f:
            return f.read()

    def assert_mod_file_matches_fixture(self, modid: str) -> None:
        with open("tests/fixtures/ark_mods/%s.mod" % modid, "rb") as f:
            expected = f.read()

        self.assertEqual(
            self.read_mod_file(modid), expected, "%s.mod differs from fixture" % modid
        )

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

    def test_should_not_inherit_meta_data_from_previous_mod(self) -> None:
        with_meta_data, without_meta_data = MODS[0][0], MODS[1][0]
        self.stage_mod(with_meta_data)
        mod_dir = self.stage_mod(without_meta_data)
        with open(os.path.join(mod_dir, "modmeta.info"), "wb") as f:
            f.write(struct.pack("i", 0))

        self.new_downloader().create_mod_file(without_meta_data)  # type: ignore
        expected = self.read_mod_file(without_meta_data)

        downloader = self.new_downloader()
        downloader.create_mod_file(with_meta_data)  # type: ignore
        downloader.create_mod_file(without_meta_data)  # type: ignore

        self.assertEqual(self.read_mod_file(without_meta_data), expected)

    def test_should_repair_mod_file_of_up_to_date_mod(self) -> None:
        modid = MODS[1][0]
        self.stage_mod(modid)
        self.new_downloader().create_mod_file(modid)  # type: ignore
        expected = self.read_mod_file(modid)

        self.stage_mod(modid, os.path.join(self.mod_file_dir, modid))
        shutil.copyfile(
            "tests/fixtures/ark_mods/%s.mod" % MODS[0][0],
            os.path.join(self.mod_file_dir, modid + ".mod"),
        )
        with open(
            os.path.join(self.destination_path, "ShooterGame", "mod_state.json"), "w"
        ) as f:
            json.dump({modid: {"timeupdated": 1}}, f)

        with mock.patch.object(
            ArkModDownloader, "remote_time_updated", return_value=1
        ), mock.patch.object(ArkModDownloader, "download_mod") as download_mod:
            ArkModDownloader(
                depotdownloader="unused",
                modids=[modid],
                workingdir=self.destination_path,
                download_dir=self.source_path,
            )

        download_mod.assert_not_called()
        self.assertEqual(self.read_mod_file(modid), expected)
