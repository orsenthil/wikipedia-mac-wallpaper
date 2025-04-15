from setuptools import setup

APP = ['wiki-wallpaper.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,  # Makes the app run in background
        'CFBundleName': 'Wikipedia Wallpaper',
        'CFBundleDisplayName': 'Wikipedia Wallpaper',
        'CFBundleIdentifier': 'com.senthil.wikipediawallpaper',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
    },
    'packages': ['PIL', 'requests', 'bs4'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
