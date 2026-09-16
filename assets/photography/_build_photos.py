# -*- coding: utf-8 -*-
"""更新摄影图库 —— 一条命令跑完：读说明文档 → 处理照片 → 重建图库 HTML。

用法（在 git-bash 里）：
    cd "C:/Users/28014/Documents/个人网页_江衍睿"
    bash "更新摄影图库.sh"

它做四件事：
  1. 从 I:\网页所需图片\照片索引说明.docx 读出每条说明（日期 / 地点 / 描述 / 器材）
  2. 把 I:\网页所需图片 下的 jpg 按「保持原始比例」缩放，并在右下角烙上加过暗影的水印
     · assets/photography/gallery/  长边 900，图库列表用
     · assets/photography/full/     长边 1800，点开看大图用
  3. 重建 index.html 里 <!-- GALLERY:START --> 与 <!-- GALLERY:END --> 之间的所有照片块
  4. 打印对账结果与需要你处理的提醒

新增照片的步骤：
  · 把 jpg 放进 I:\网页所需图片
  · 在 照片索引说明.docx 里加一行说明，格式：文件名: 年.月: 地点：描述；拍摄器材：机身 + 镜头
  · 英文说明写进 assets/photography/captions-en.json（格式见文件内已有条目；缺了会退回中文并提醒）
  · 跑一次本脚本
"""
import os, re, io, json, zipfile, html
from PIL import Image, ImageOps, ImageFilter, ImageStat

SRC      = r'I:\网页所需图片'
DOCX     = os.path.join(SRC, '照片索引说明.docx')
LOGO     = os.path.join(SRC, 'weixin logo.png')
PROJ     = os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
PROJ     = r'C:\Users\28014\Documents\个人网页_江衍睿'
PHOTODIR = os.path.join(PROJ, 'assets', 'photography')
GAL      = os.path.join(PHOTODIR, 'gallery')
FUL      = os.path.join(PHOTODIR, 'full')
ENJSON   = os.path.join(PHOTODIR, 'captions-en.json')
INDEX    = os.path.join(PROJ, 'site.html')   # 图库在三 tab 应用页里（封面是 index.html）

THRESH   = 110          # 水印所在区域平均亮度高于此值 → 用深色线稿（白线在亮底上会被吃掉）
GAL_EDGE, GAL_Q = 900, 80
FUL_EDGE, FUL_Q = 1800, 84

os.makedirs(GAL, exist_ok=True)
os.makedirs(FUL, exist_ok=True)

# ---------------------------------------------------------------- 1. 读说明文档
def read_docx_lines(path):
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8')
    out = []
    for pm in re.finditer(r'<w:p[ >].*?</w:p>', xml, re.S):
        t = ''.join(x for x in re.findall(r'<w:t[^>]*>(.*?)</w:t>', pm.group(0), re.S))
        t = (t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
              .replace('&quot;', '"').replace('&#39;', "'"))
        if t.strip():
            out.append(t.strip())
    return out

def parse(line):
    gear = ''
    m = re.search(r'[；;、\s]*拍摄器材[：:]\s*(.+?)\s*$', line)
    if m:
        gear = m.group(1).strip(); head = line[:m.start()].strip()
    else:
        head = line.strip()
    mm = re.match(r'^(.+?)\s*[：:]\s*(.*)$', head)
    if not mm:
        return None
    key, rest = mm.group(1).strip(), mm.group(2).strip()
    d = re.match(r'^\s*(\d{4})\s*[.,，]\s*(\d{1,2})\s*[：:,，]\s*(.*)$', rest)
    if d:
        date = '%s.%s' % (d.group(1), d.group(2)); rest = d.group(3).strip()
    else:
        date = ''
    p = re.match(r'^(.+?)\s*[：:，,]\s*(.+)$', rest)
    place, desc = (p.group(1).strip(), p.group(2).strip()) if p else ('', rest)
    return dict(key=key, date=date, place=place, desc=desc.rstrip('：:，,、 '), gear=gear)

# ---------------------------------------------------------------- 2. 处理照片
logo = Image.open(LOGO).convert('RGBA')
logo = logo.crop(logo.getchannel('A').getbbox())

def build_wm(width, dark_glyph):
    w = max(1, int(width)); h = max(1, round(logo.height * w / logo.width))
    l = logo.resize((w, h), Image.LANCZOS)
    a = l.getchannel('A')
    a2 = a.filter(ImageFilter.MaxFilter(min(max(3, (int(w * 0.09) | 1)), 9)))
    a2 = a2.filter(ImageFilter.GaussianBlur(max(1.0, w * 0.036)))
    a2 = a2.point(lambda v: min(255, int(v * 1.85)))
    if dark_glyph:
        gr, go, hr, ho = (16, 16, 19), 0.90, (255, 255, 255), 0.60
    else:
        gr, go, hr, ho = (255, 255, 255), 0.95, (0, 0, 0), 0.74
    halo = Image.new('RGBA', l.size, hr + (0,))
    halo.putalpha(a2.point(lambda v: int(v * ho)))
    glyph = Image.new('RGBA', l.size, gr + (0,))
    glyph.putalpha(a.point(lambda v: int(v * go)))
    return halo, glyph, l.size

def process(src, slug):
    im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    W, H = im.size; res = {}
    for tag, edge, q in (('gallery', GAL_EDGE, GAL_Q), ('full', FUL_EDGE, FUL_Q)):
        s = edge / max(W, H)
        nw, nh = max(1, round(W * s)), max(1, round(H * s))
        im2 = im.resize((nw, nh), Image.LANCZOS) if s < 1 else im.copy()
        wmw = min(max(nw * 0.078, 58), 190); mgn = min(max(nw * 0.026, 16), 62)
        _, _, (ww, wh) = build_wm(wmw, False)
        x, y = int(nw - ww - mgn), int(nh - wh - mgn)
        box = (max(x - 4, 0), max(y - 4, 0), min(x + ww + 4, nw), min(y + wh + 4, nh))
        lum = ImageStat.Stat(im2.crop(box).convert('L')).mean[0]
        halo, glyph, _ = build_wm(wmw, lum > THRESH)
        base = im2.convert('RGBA')
        base.alpha_composite(halo, (x, y)); base.alpha_composite(glyph, (x, y))
        d = GAL if tag == 'gallery' else FUL
        base.convert('RGB').save(os.path.join(d, slug + '.jpg'), 'JPEG',
                                 quality=q, optimize=True, progressive=True)
        res[tag] = (nw, nh)
    return W, H, res

def norm_gear(g):
    s = re.sub(r'\s*\+\s*', ' + ', g).strip()
    if ' + ' not in s and ', ' in s:
        s = s.replace(', ', ' + ')
    return s

# 说明文档里的已知笔误修正（源文档保持原样，这里统一纠正，重跑不会反复出现）
GEAR_FIX = [('Lumix S8', 'Lumix S5')]

def apply_fixes(g):
    for a, b in GEAR_FIX:
        g = g.replace(a, b)
    return g

# ---------------------------------------------------------------- 主流程
en_map = {}
if os.path.exists(ENJSON):
    en_map = json.load(io.open(ENJSON, encoding='utf-8'))

lines = read_docx_lines(DOCX)
parsed = [x for x in (parse(l) for l in lines) if x]
files = {os.path.splitext(f)[0]: f for f in sorted(os.listdir(SRC)) if f.lower().endswith('.jpg')}

missing_doc = sorted(set(files) - {p['key'] for p in parsed})
missing_img = sorted({p['key'] for p in parsed} - set(files))
if missing_doc:
    print('⚠ 磁盘上有照片但说明文档里没有：', missing_doc)
if missing_img:
    print('⚠ 说明文档里有条目但磁盘上没有照片：', missing_img)

recs, no_en = [], []
for p in parsed:
    f = files.get(p['key'])
    if not f:
        continue
    slug = re.sub(r'[^a-z0-9]+', '-', p['key'].lower()).strip('-')
    W, H, r = process(os.path.join(SRC, f), slug)
    en = en_map.get(p['key'])
    if not en:
        no_en.append(p['key']); en = {'place': p['place'], 'desc': p['desc']}
    gear = apply_fixes(norm_gear(p['gear']))
    recs.append(dict(slug=slug, date=p['date'],
                     place_zh=p['place'], place_en=en['place'],
                     desc_zh=p['desc'], desc_en=en['desc'],
                     gear_zh=gear,
                     gear_en=gear.replace('松下Lumix', 'Panasonic Lumix')
                                 .replace('松下S5', 'Panasonic S5'),
                     w=r['gallery'][0], h=r['gallery'][1]))

io.open(os.path.join(PHOTODIR, 'photos.json'), 'w', encoding='utf-8').write(
    json.dumps(recs, ensure_ascii=False, indent=1))

# ---- 重建 index.html 里的图库段 ----
def esc(x):
    return html.escape(x, quote=True)

figs = []
for r in recs:
    t_zh = '%s — %s' % (r['place_zh'], r['desc_zh'])
    t_en = '%s — %s' % (r['place_en'], r['desc_en'])
    m_zh = '%s · %s' % (r['date'], r['gear_zh'])
    m_en = '%s · %s' % (r['date'], r['gear_en'])
    figs.append(
'''      <figure class="photo" tabindex="0" data-slug="{slug}" data-full="assets/photography/full/{slug}.jpg">
        <div class="ph">
          <img src="assets/photography/gallery/{slug}.jpg" alt="{alt}" width="{w}" height="{h}" draggable="false" loading="lazy" decoding="async">
          <span class="guard" aria-hidden="true"></span>
          <figcaption class="cap">
            <span class="cap-title" data-en="{ten}" data-zh="{tzh}">{ten}</span>
            <span class="cap-meta" data-en="{men}" data-zh="{mzh}">{men}</span>
          </figcaption>
        </div>
      </figure>'''.format(slug=r['slug'], alt=esc(t_en), w=r['w'], h=r['h'],
                          ten=esc(t_en), tzh=esc(t_zh), men=esc(m_en), mzh=esc(m_zh)))

s = io.open(INDEX, encoding='utf-8').read()
A = '<!-- GALLERY:START'
B = '<!-- GALLERY:END -->'
i0 = s.index(A); i1 = s.index(B)
head_marker_end = s.index('-->', i0) + 3
s = s[:head_marker_end] + '\n' + '\n'.join(figs) + '\n      ' + s[i1:]
io.open(INDEX, 'w', encoding='utf-8').write(s)

print('处理照片 %d 张 → gallery/ 与 full/' % len(recs))
print('已重建 %s 的图库段（%d 个照片块）' % (os.path.basename(INDEX), len(figs)))
if no_en:
    print()
    print('⚠ 以下照片缺英文说明，已暂时用中文顶替，请补进 assets/photography/captions-en.json：')
    for k in no_en:
        print('   ', k)
print()
print('完成。摄影 tab 页头只含创作自述，不写照片数量，加照片后无需改页头。')
