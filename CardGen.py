######################################################################
## QSL Card Generator - Devin Shoemaker 2025 - devin@shoemaker.info ##
## Resources:                                                       ##
##    - backdrop image (the main image)                             ##
##    - overlay image (what the QSO information is displayed on)    ##
##    - icon image (I use this for your state)                      ##
##                                                                  ##
## Program Flow:                                                    ##
##    1. Place QSO information text on overlay image                ##
##    2. Place overlay image onto backdrop. Position is determined  ##
##       by gravity string in backdrop filename. Must match format: ##
##       somephoto-north_east.jpg                                   ##
##       somephoto-south_west.jpg                                   ##
##    3. State icon placed into south_east corner                   ##
##    4. 73 test placed into south_east corner                      ##
##    5. Write generated card to file                               ##
######################################################################

import xmltodict
from wand.image import Image
from wand.drawing import Drawing

configpath = "resource/config.xml"
xmlconfig = {}
with open(configpath, 'r') as file:
    xmlconfig = xmltodict.parse(file.read())

settings = xmlconfig["MyQSLConfig"]["Settings"]["QSLCard"]

outputPath  = settings["CardOutput"]
overlayPath = settings["OverlayImage"]
iconPath    = settings["IconPath"]

# spacing values for QSO text relative to overlay image
rowSpace = int(settings["QSODetails"]["RowSpace"])
col1Left = int(settings["QSODetails"]["Col1Left"])
col2Left = int(settings["QSODetails"]["Col2Left"])
initBase = int(settings["QSODetails"]["InitBase"])

# state icon positioning
iconMarginBottom = int(settings["Icon"]["MarginBottom"])
iconMarginRight  = int(settings["Icon"]["MarginRight"])

# 73 text positioning
sevenThreeText = settings["Message"]["Text"]
textLeft       = int(settings["Message"]["Left"])
textBase       = int(settings["Message"]["Base"])


def genCard(qslInfo, backdrop):
    # get magick gravity string from filename
    # 'south_west', etc.
    gravity = backdrop.split("-")[-1]
    gravity = gravity.split(".")[0]

    dateTimeClean = qslInfo["Date"].replace(" ", "_")


    with Image(filename=backdrop) as backdrop:
        backdrop.resize(3125, 2125)

        with Image(filename=overlayPath) as overlay:
            with Drawing() as ctx:
                ctx.font_family = 'JetBrainsMono Nerd Font'
                ctx.font_style = 'normal'
                ctx.font_size = 60
                ctx.gravity = 'south_west'
                ctx.fill_color = 'white'

                i = 0
                baseline = 0
                for k, v in qslInfo.items():
                    baseline = initBase - i * rowSpace
                    overlay.annotate(k + ":", ctx, left=col1Left, baseline=baseline)
                    overlay.annotate(v, ctx, left=col2Left, baseline=baseline)
                    i = i + 1

            backdrop.composite(
                overlay,
                gravity=gravity,
                operator='over'
            )

        with Image(filename=iconPath) as icon:
            icon.resize(int(icon.width * 0.35), int(icon.height * 0.35))

            iconTop = backdrop.height - icon.height - iconMarginBottom
            iconLeft = backdrop.width - icon.width - iconMarginRight

            backdrop.composite(
                icon,
                left=iconLeft,
                top=iconTop,
                operator='over'
            )

        with Drawing() as ctx:
            ctx.font_family = 'Adwaita Sans'
            ctx.font_style = 'italic'
            ctx.font_size = 60
            ctx.gravity = 'south_east'
            ctx.fill_color = 'white'

            backdrop.annotate(sevenThreeText, ctx, left=textLeft, baseline=textBase)

        output = outputPath + 'qslcard_' + qslInfo['With'] + '_' + dateTimeClean + '.jpg'
        backdrop.save(filename=output)
        return output
