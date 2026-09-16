# -*- coding: utf-8 -*-
"""封面背景图：保比例缩放到网页尺寸，输出 assets/cover/cover.jpg 与 cover-sm.jpg

用法：
    cd "C:/Users/28014/Documents/个人网页_江衍睿"
    bash "更新封面图.sh"

换封面：把下面 SRC 改成你的新图路径（或直接把新图覆盖到该路径），再跑一次即可。
脚本只做等比缩放，不裁剪、不加水印（封面是整页背景，按你的要求未叠水印）。
"""
import os
from PIL import Image, ImageOps

# ★ 换封面就改这一行
SRC = r'C:\Users\28014\AppData\Roaming\Hermes\composer-images\composer_2026-09-16_08-57-45-602_d1c11d.jpg'

PROJ = r'C:\Users\28014\Documents\个人网页_江衍睿'
OUT = os.path.join(PROJ, 'assets', 'cover')
os.makedirs(OUT, exist_ok=True)

if not os.path.exists(SRC):
    raise SystemExit('找不到封面源图：%s\n请把 SRC 改成你的新图路径。' % SRC)

im = ImageOps.exif_transpose(Image.open(SRC)).convert('RGB')
W, H = im.size
print('源图 %dx%d  %.1f MB' % (W, H, os.path.getsize(SRC) / 1e6))

for tag, edge, q in (('cover', 2400, 82), ('cover-sm', 1200, 80)):
    s = edge / max(W, H)
    nw, nh = max(1, round(W * s)), max(1, round(H * s))
    im2 = im.resize((nw, nh), Image.LANCZOS)
    p = os.path.join(OUT, tag + '.jpg')
    im2.save(p, 'JPEG', quality=q, optimize=True, progressive=True)
    print('  %-9s %dx%d  %.0f KB' % (tag, nw, nh, os.path.getsize(p) / 1024))

print()
print('完成。若源图明暗分布变了（文字压到亮部），可能要在 assets/site.css 的 .cover-scrim 里调遮罩深浅。')
