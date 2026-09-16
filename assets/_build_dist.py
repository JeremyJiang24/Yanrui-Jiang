# -*- coding: utf-8 -*-
"""生成上线包：只复制该公开的文件，并做上线前自检。

用法（在项目目录里）：
    bash "生成上线包.sh"

产出：C:\\Users\\28014\\Documents\\个人网页_江衍睿_上线包\\  （另生成同名 .zip）
"""
import io, os, re, shutil, zipfile, urllib.parse

PROJ = r'C:\Users\28014\Documents\个人网页_江衍睿'
DIST = r'C:\Users\28014\Documents\个人网页_江衍睿_上线包'
ZIP = DIST + '.zip'

# ---------- 白名单：只有这些会被发布 ----------
PUBLIC = [
    'index.html', 'site.html',
    'assets/site.css', 'assets/site.js', 'assets/head.jpg',
    'assets/Yanrui_Jiang_CV_EN.pdf', 'assets/Yanrui_Jiang_CV_ZH.pdf',
    'assets/cover/cover.jpg', 'assets/cover/cover-sm.jpg',
    'projects/liege.html', 'projects/pigeon.html', 'projects/tongji.html',
]
for sub in ('liege', 'pigeon', 'tongji'):
    d = os.path.join(PROJ, 'assets', 'projects', sub)
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.lower().endswith('.webp'):
                PUBLIC.append('assets/projects/%s/%s' % (sub, f))
for sub in ('gallery', 'full'):
    d = os.path.join(PROJ, 'assets', 'photography', sub)
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                PUBLIC.append('assets/photography/%s/%s' % (sub, f))

# ---------- 建包（保留 .git，避免清掉版本库） ----------
if os.path.exists(DIST):
    for name in os.listdir(DIST):
        if name == '.git':
            continue
        p = os.path.join(DIST, name)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
else:
    os.makedirs(DIST)
tot = 0
for rel in PUBLIC:
    src = os.path.join(PROJ, rel.replace('/', os.sep))
    if not os.path.exists(src):
        raise SystemExit('缺少文件：' + rel)
    dst = os.path.join(DIST, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    tot += os.path.getsize(src)
io.open(os.path.join(DIST, '.nojekyll'), 'w').write('')   # GitHub Pages 用

# ---------- 自检 ----------
print('上线包已生成：%s' % DIST)
print('  文件 %d 项 | %.2f MB' % (len(PUBLIC) + 1, tot / 1e6))

PAGES = ['index.html', 'site.html', 'projects/liege.html', 'projects/pigeon.html', 'projects/tongji.html']
missing, ok = [], 0
for rel in PAGES:
    p = os.path.join(DIST, rel.replace('/', os.sep))
    s = io.open(p, encoding='utf-8').read()
    base = os.path.dirname(p)
    refs = re.findall(r'(?:href|src)="([^"]+)"', s) + re.findall(r'data-full="([^"]+)"', s)
    for r in sorted(set(refs)):
        if r.startswith(('http', 'mailto:', 'tel:', 'data:', '#')):
            continue
        t = os.path.normpath(os.path.join(base, urllib.parse.unquote(r.split('#')[0])))
        if os.path.exists(t):
            ok += 1
        else:
            missing.append((rel, r))
css = io.open(os.path.join(DIST, 'assets', 'site.css'), encoding='utf-8').read()
for m in re.finditer(r'url\(([^)]+)\)', css):
    r = m.group(1).strip().strip('"\'')
    t = os.path.join(DIST, 'assets', r)
    if os.path.exists(t):
        ok += 1
    else:
        missing.append(('assets/site.css', r))

leak, nonascii, big = [], [], []
for root, _, fs in os.walk(DIST):
    for f in fs:
        rel = os.path.relpath(os.path.join(root, f), DIST)
        if f.lower().endswith(('.md', '.sh', '.py')) or (f.startswith('_') and f != '.nojekyll'):
            leak.append(rel)
        if any(ord(c) > 127 for c in rel):
            nonascii.append(rel)
        if os.path.getsize(os.path.join(root, f)) > 1_500_000:
            big.append((rel, os.path.getsize(os.path.join(root, f)) / 1e6))

print()
print('  引用完整性      : 可解析 %d 项，缺失 %d' % (ok, len(missing)))
for rel, r in missing:
    print('      ✗ %s -> %s' % (rel, r))
print('  内部文件泄漏    : %s' % (leak if leak else '无'))
print('  非 ASCII 文件名 : %s' % (nonascii if nonascii else '无'))
print('  单个大文件      : %s' % (['%s %.2fMB' % b for b in big] if big else '无'))

# ---------- 打包 zip（排除 .git） ----------
if os.path.exists(ZIP):
    os.remove(ZIP)
n = 0
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for root, dirs, fs in os.walk(DIST):
        dirs[:] = [d for d in dirs if d != '.git']
        for f in fs:
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, DIST).replace(os.sep, '/'))
            n += 1
print()
print('  zip: %s  (%d 项, %.2f MB)' % (ZIP, n, os.path.getsize(ZIP) / 1e6))
print()
print('完成。上传时请上传「上线包」文件夹里的内容，不要上传项目工作目录。')
