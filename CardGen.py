from wand.image import Image
from wand.drawing import Drawing

def genCard(qslInfo):
    blankCard = "./QSL.jpg"
    rowSpace = 140
    col1Left = 335
    col2Left = 800


    with Image(filename=blankCard) as img:
        with Drawing() as ctx:
            ctx.font_family = 'JetBrainsMono Nerd Font'
            ctx.font_style = 'normal'
            ctx.font_size = 120
            ctx.gravity = 'south_west'
            ctx.fill_color = 'white'

            i = 0
            baseline = 0
            for k, v in qslInfo.items():
                baseline = 1100 - i * rowSpace
                img.annotate(k + ":", ctx, left=col1Left, baseline=baseline)
                img.annotate(v, ctx, left=col2Left, baseline=baseline)
                i = i + 1

            ctx.font_family = 'Adwaita Sans'
            ctx.font_style = 'italic'
            ctx.gravity = 'south_east'

            img.annotate("73s from Michigan!", ctx, left=col1Left, baseline=rowSpace * 2)

        with Image(filename='./mi.png') as overlay:
            overlay.resize(int(overlay.width * 0.7), int(overlay.height * 0.7))
            ovLeft = int(img.width - overlay.width - col1Left)
            ovTop = int(img.height - overlay.height - rowSpace * 4)
            img.composite(
                overlay,
                left=ovLeft,
                top=ovTop,
                operator='over'
            )

        img.save(filename='qslcard.jpg')
