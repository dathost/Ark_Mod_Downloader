**ARK Mod Downloader**
------------------------------
Steam workshop downloads of ARK mods are not directly usable by a server.  The individual files come archived as .z files and the server needs a generated .mod file.

This tool downloads the mod via [DepotDownloader](https://github.com/SteamRE/DepotDownloader), extracts the .z files and writes the .mod file.

**Usage**

***Commandline Args***

**--workingdir** - This is the home directory of your ARK server

**--modids** - The IDs of the mod you wish to download.  Space separated list of Mod IDs to download

**--depotdownloader** - Path to the DepotDownloader binary

**--download-dir** - Directory the mods are downloaded to before installation

**Credits**
<a href="https://github.com/project-umbrella/arkit.py" target="_blank">arkit.py</a> - Used to extract the .z files
