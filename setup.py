from distutils.core import setup

setup(
    name="ark_mod_downloader",
    packages=["ark_mod_downloader"],
    install_requires=[
        "steamfiles @ git+https://github.com/dathost/steamfiles.git@af354648fa9c47747ea1e34f1e9ce07e1be7e330"
    ],
)
