import os
from wand.image import Image

from MyQSL.config import get_config

back_path = get_config("Settings/QSLCard/BackdropPath")
thumb_path = get_config("Settings/QSLCard/ThumbnailPath")


def check_dirs():
    if not os.path.isdir(back_path):
        os.makedirs(back_path)

    if not os.path.isdir(back_path):
        raise RuntimeError("Backdrop path does not exist, and the program was not able to create it.")

    if not os.path.isdir(thumb_path):
        os.makedirs(thumb_path)

    if not os.path.isdir(thumb_path):
        raise RuntimeError("Thumbnail path does not exist, and the program was not able to create it.")


def thumbnail_check():
    check_dirs()

    backdrops = os.listdir(back_path)
    thumbnails = os.listdir(thumb_path)

    for backdrop in backdrops:
        if backdrop not in thumbnails:
            with Image(filename=back_path+backdrop) as img:
                img.resize(int(img.width*0.1), int(img.height*0.1))
                img.save(filename=thumb_path+backdrop)


thumbnail_check()
