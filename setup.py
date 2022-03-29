from distutils.core import setup

setup(
    name="ark_mod_downloader",
    packages=["ark_mod_downloader"],
    install_requires=["steamfiles @ git+https://github.com/dathost/steamfiles.git"],
)
