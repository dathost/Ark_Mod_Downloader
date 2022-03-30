import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

from collections import OrderedDict

from ark_mod_downloader import arkit
from steamfiles import acf


class ArkModDownloader:
    def __init__(
        self,
        steamcmd: str,
        modids,
        workingdir,
        steamapps,
    ):
        self.workingdir = workingdir
        self.steamcmd = steamcmd  # Path to SteamCMD exe
        self.steamapps = steamapps
        self.map_names = []  # Stores map names from mod.info
        self.meta_data = OrderedDict([])  # Stores key value from modmeta.info
        self.temp_mod_path = os.path.join(
            self.steamapps, "workshop", "content", "346110"
        )

        # If any issues happen in download and extract chain this returns false
        if modids:
            os.makedirs(os.path.join(self.steamapps, "workshop"), exist_ok=True)
            try:
                shutil.copyfile(
                    os.path.join(
                        self.workingdir, "ShooterGame", "appworkshop_346110.acf"
                    ),
                    os.path.join(self.steamapps, "workshop", "appworkshop_346110.acf"),
                )
            except FileNotFoundError:
                pass

            for mod in modids:
                if self.update_needed(mod):
                    if self.download_mod(mod):
                        print("[+] Mod {} Installation Finished".format(str(mod)))
                    else:
                        print(
                            "[+] There was as problem downloading mod {}.  See above errors".format(
                                str(mod)
                            )
                        )
                else:
                    print("[+] Mod {} is already up to date".format(str(mod)))

            try:
                shutil.copyfile(
                    os.path.join(self.steamapps, "workshop", "appworkshop_346110.acf"),
                    os.path.join(
                        self.workingdir, "ShooterGame", "appworkshop_346110.acf"
                    ),
                )
            except FileNotFoundError:
                pass

    def update_needed(self, modid):
        local_updated_timestamp = None
        remote_updated_timestamp = None

        try:
            with open(
                os.path.join(self.steamapps, "workshop", "appworkshop_346110.acf"),
            ) as f:
                for existing_modid, existing_mod in acf.load(f)["AppWorkshop"][
                    "WorkshopItemsInstalled"
                ].items():
                    if modid == existing_modid:
                        local_updated_timestamp = int(existing_mod["timeupdated"])

                        with urllib.request.urlopen(
                            "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
                            data=urllib.parse.urlencode(
                                {"itemcount": "1", "publishedfileids[0]": modid}
                            ).encode("utf-8"),
                        ) as r:
                            data = json.load(r)
                            remote_updated_timestamp = data["response"][
                                "publishedfiledetails"
                            ][0]["time_updated"]

        except FileNotFoundError:
            pass

        except Exception as e:
            print("[+] Got error {} when checking for update".format(str(e)))

        return (
            not local_updated_timestamp
            or not remote_updated_timestamp
            or local_updated_timestamp != remote_updated_timestamp
        )

    def download_mod(self, modid):
        """
        Launch SteamCMD to download ModID
        :return:
        """
        print("[+] Starting Download of Mod " + str(modid))
        args = []
        args.append(self.steamcmd)
        args.append("+login")
        args.append("anonymous")
        args.append("+workshop_download_item")
        args.append("346110")
        args.append(modid)
        args.append("+quit")
        subprocess.call(args)

        return True if self.extract_mod(modid) else False

    def extract_mod(self, modid):
        """
        Extract the .z files using the arkit lib.
        If any file fails to download this whole script will abort
        :return: None
        """

        print("[+] Extracting .z Files.")

        try:
            for curdir, subdirs, files in os.walk(
                os.path.join(self.temp_mod_path, modid, "WindowsNoEditor")
            ):
                for file in files:
                    name, ext = os.path.splitext(file)
                    if ext == ".z":
                        src = os.path.join(curdir, file)
                        dst = os.path.join(curdir, name)
                        uncompressed = os.path.join(curdir, file + ".uncompressed_size")
                        arkit.unpack(src, dst)
                        # print("[+] Extracted " + file)
                        os.remove(src)
                        if os.path.isfile(uncompressed):
                            os.remove(uncompressed)

        except (
            arkit.UnpackException,
            arkit.SignatureUnpackException,
            arkit.CorruptUnpackException,
        ) as e:
            print("[x] Unpacking .z files failed, aborting mod install")
            return False

        if self.create_mod_file(modid):
            if self.move_mod(modid):
                return True
            else:
                return False

    def move_mod(self, modid):
        """
        Move mod from SteamCMD download location to the ARK server.
        It will delete an existing mod with the same ID
        :return:
        """

        ark_mod_folder = os.path.join(self.workingdir, "ShooterGame", "Content", "Mods")
        output_dir = os.path.join(ark_mod_folder, str(modid))
        source_dir = os.path.join(self.temp_mod_path, modid, "WindowsNoEditor")

        # TODO Need to handle exceptions here
        if not os.path.isdir(ark_mod_folder):
            print("[+] Creating Directory: " + ark_mod_folder)
            os.mkdir(ark_mod_folder)

        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)

        print("[+] Moving Mod Files To: " + output_dir)
        shutil.copytree(source_dir, output_dir)

        return True

    def create_mod_file(self, modid, mod_name="ModName"):
        """
        Create the .mod file.
        This code is an adaptation of the code from Ark Server Launcher.  All credit goes to Face Wound on Steam
        :return:
        """
        if not self.parse_base_info(modid) or not self.parse_meta_data(modid):
            return False

        print("[+] Writing .mod File")
        with open(
            os.path.join(
                self.workingdir, "ShooterGame", "Content", "Mods", modid + ".mod"
            ),
            "w+b",
        ) as f:

            modid = int(modid)
            f.write(struct.pack("Ixxxx", modid))  # Needs 4 pad bits
            self.write_ue4_string(mod_name, f)
            self.write_ue4_string(f"../../../ShooterGame/Content/Mods/{modid}", f)

            map_count = len(self.map_names)
            f.write(struct.pack("i", map_count))

            for m in self.map_names:
                self.write_ue4_string(m, f)

            # Not sure of the reason for this
            num2 = 4280483635
            f.write(struct.pack("I", num2))
            num3 = 2
            f.write(struct.pack("i", num3))

            if "ModType" in self.meta_data:
                mod_type = 1
            else:
                mod_type = 0

            f.write(struct.pack("B", mod_type))
            meta_length = len(self.meta_data)
            f.write(struct.pack("i", meta_length))

            for k, v in self.meta_data.items():
                self.write_ue4_string(k, f)
                self.write_ue4_string(v, f)

        return True

    def read_ue4_string(self, file):
        count = struct.unpack("i", file.read(4))[0]
        flag = False
        if count < 0:
            flag = True
            count -= 1

        if flag or count <= 0:
            return ""

        return file.read(count)[:-1].decode()

    def write_ue4_string(self, string_to_write, file):
        string_length = len(string_to_write) + 1
        file.write(struct.pack("i", string_length))
        barray = bytearray(string_to_write, "utf-8")
        file.write(barray)
        file.write(struct.pack("p", b"0"))

    def parse_meta_data(self, modid):
        """
        Parse the modmeta.info files and extract the key value pairs need to for the .mod file.
        How To Parse modmeta.info:
            1. Read 4 bytes to tell how many key value pairs are in the file
            2. Read next 4 bytes tell us how many bytes to read ahead to get the key
            3. Read ahead by the number of bytes retrieved from step 2
            4. Read next 4 bytes to tell how many bytes to read ahead to get value
            5. Read ahead by the number of bytes retrieved from step 4
            6. Start at step 2 again
        :return: Dict
        """

        print("[+] Collecting Mod Meta Data From modmeta.info")
        print("[+] Located The Following Meta Data:")

        mod_meta = os.path.join(
            self.temp_mod_path, modid, "WindowsNoEditor", "modmeta.info"
        )
        if not os.path.isfile(mod_meta):
            print(
                "[x] Failed To Locate modmeta.info. Cannot continue without it.  Aborting"
            )
            return False

        with open(mod_meta, "rb") as f:

            total_pairs = struct.unpack("i", f.read(4))[0]

            for i in range(total_pairs):

                key, value = "", ""

                key_bytes = struct.unpack("i", f.read(4))[0]
                key_flag = False
                if key_bytes < 0:
                    key_flag = True
                    key_bytes -= 1

                if not key_flag and key_bytes > 0:

                    raw = f.read(key_bytes)
                    key = raw[:-1].decode()

                value_bytes = struct.unpack("i", f.read(4))[0]
                value_flag = False
                if value_bytes < 0:
                    value_flag = True
                    value_bytes -= 1

                if not value_flag and value_bytes > 0:
                    raw = f.read(value_bytes)
                    value = raw[:-1].decode()

                # TODO This is a potential issue if there is a key but no value
                if key and value:
                    print("[!] " + key + ":" + value)
                    self.meta_data[key] = value

        return True

    def parse_base_info(self, modid):

        print("[+] Collecting Mod Details From mod.info")

        mod_info = os.path.join(
            self.temp_mod_path, modid, "WindowsNoEditor", "mod.info"
        )

        if not os.path.isfile(mod_info):
            print("[x] Failed to locate mod.info. Cannot Continue.  Aborting")
            return False

        with open(mod_info, "rb") as f:
            self.read_ue4_string(f)
            map_count = struct.unpack("i", f.read(4))[0]

            for i in range(map_count):
                cur_map = self.read_ue4_string(f)
                if cur_map:
                    self.map_names.append(cur_map)

        return True


def main():
    parser = argparse.ArgumentParser(
        description="A utility to download ARK Mods via SteamCMD"
    )
    parser.add_argument(
        "--workingdir", dest="workingdir", help="Game server home directory."
    )
    parser.add_argument(
        "--modids", nargs="+", default=None, dest="modids", help="ID of Mod To Download"
    )
    parser.add_argument("--steamcmd", dest="steamcmd", help="Path to SteamCMD")
    parser.add_argument("--steamapps", dest="steamapps", help="Path to steamapps")

    args = parser.parse_args()

    if not args.modids:
        print("[x] No Mod IDs Provided.  Aborting")
        sys.exit(0)

    ArkModDownloader(
        steamcmd=args.steamcmd,
        modids=args.modids,
        workingdir=args.workingdir,
        steamapps=args.steamapps,
    )


if __name__ == "__main__":
    main()
