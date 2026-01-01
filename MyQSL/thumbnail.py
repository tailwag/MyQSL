import os
from wand.image import Image

from MyQSL.config import get_config

back_path = get_config("Settings/QSLCard/BackdropPath")
thumb_path = get_config("Settings/QSLCard/ThumbnailPath")

def thumbnail_check():
    backdrops = os.listdir(back_path)
    thumbnails = os.listdir(thumb_path)

    for backdrop in backdrops:
        if backdrop not in thumbnails:
            with Image(filename=back_path+backdrop) as img:
                img.resize(int(img.width*0.1), int(img.height*0.1))
                img.save(filename=thumb_path+backdrop)


thumbnail_check()
