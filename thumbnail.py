import os
from wand.image import Image
import xml.etree.ElementTree as ET

configpath = "resource/config.xml"
tree = ET.parse(configpath)
root = tree.getroot()

settings = root.find("Settings")
if settings is None:
    raise RuntimeError("BAD CONFIG: missing Settings block")

qslcard = settings.find("QSLCard")
if qslcard is None:
    raise RuntimeError("BAD CONFIG: missing QSLCard block")

backPath = qslcard.findtext("BackdropPath")
if not backPath:
    raise RuntimeError("BAD CONFIG: missing BackdropPath tag")

thumbPath = qslcard.findtext("ThumbnailPath")
if not thumbPath:
    raise RuntimeError("BAD CONFIG: missing ThumbnailPath tag")


def thumbnail_check():
    backdrops = os.listdir(backPath)
    thumbnails = os.listdir(thumbPath)

    for backdrop in backdrops:
        if backdrop not in thumbnails:
            with Image(filename=backPath+backdrop) as img:
                img.resize(int(img.width*0.1), int(img.height*0.1))
                img.save(filename=thumbPath+backdrop)


thumbnail_check()
