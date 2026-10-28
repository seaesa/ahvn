import os, re, urllib.request, concurrent.futures, json
from bs4 import BeautifulSoup

BASE='https://cavani.vn'
UA={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}

def get(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest)>0: return dest, os.path.getsize(dest)
    req=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r, open(dest,'wb') as f:
        f.write(r.read())
    return dest, os.path.getsize(dest)

html=open('docs/research/rendered-home.html',encoding='utf-8').read()
soup=BeautifulSoup(html,'lxml')
imgs=set()
for tag in soup.find_all(True):
    for attr in ('src','data-src','data-bg','poster'):
        v=tag.get(attr)
        if v and '/wp-content/uploads/' in v: imgs.add(v)
    st=tag.get('style') or ''
    for m in re.findall(r'url\((["\']?)([^)"\']+)\1\)', st):
        if '/wp-content/uploads/' in m[1]: imgs.add(m[1])
for s in soup.find_all('style'):
    for m in re.findall(r'url\((["\']?)([^)"\']+)\1\)', s.string or ''):
        if '/wp-content/uploads/' in m[1]: imgs.add(m[1])

favicons=['https://cavani.vn/wp-content/uploads/2023/11/cropped-logo-favicon-5-32x32.png',
'https://cavani.vn/wp-content/uploads/2023/11/cropped-logo-favicon-5-192x192.png',
'https://cavani.vn/wp-content/uploads/2023/11/cropped-logo-favicon-5-180x180.png']

css=['https://cavani.vn/wp-content/themes/flatsome/assets/css/flatsome.css?ver=3.17.6',
'https://cavani.vn/wp-content/themes/flatsome/assets/css/flatsome-shop.css?ver=3.17.6',
'https://cavani.vn/wp-content/plugins/woocommerce/assets/client/blocks/wc-blocks.css?ver=wc-10.8.1',
'https://use.fontawesome.com/releases/v6.5.1/css/all.css',
'https://use.fontawesome.com/releases/v6.5.1/css/v4-shims.css']
js=['https://cavani.vn/wp-content/themes/flatsome/assets/js/flatsome.js?ver=89ac940c4841291ea8d6',
'https://cavani.vn/wp-content/themes/flatsome/assets/js/chunk.slider.js?ver=3.17.6',
'https://cavani.vn/wp-content/themes/flatsome/assets/js/chunk.popups.js?ver=3.17.6',
'https://cavani.vn/wp-content/themes/flatsome/assets/js/chunk.tooltips.js?ver=3.17.6',
'https://cavani.vn/wp-content/themes/flatsome/assets/js/woocommerce.js?ver=1a392523165907adee6a',
'https://code.jquery.com/jquery-3.7.1.min.js']
fonts=['https://cavani.vn/wp-content/themes/flatsome/assets/css/icons/fl-icons.woff2?v=3.17.6',
'https://cavani.vn/wp-content/themes/flatsome/assets/css/icons/fl-icons.woff?v=3.17.6',
'https://cavani.vn/wp-content/themes/flatsome/assets/css/icons/fl-icons.ttf?v=3.17.6']

jobs=[]
for u in sorted(imgs|set(favicons)):
    name=u.split('/')[-1].split('?')[0]
    sub='img/favicon' if u in favicons else 'img'
    jobs.append((u, f'assets/{sub}/{name}'))
for u in css:
    name=u.split('/')[-1].split('?')[0]
    jobs.append((u, f'assets/css/{name}'))
for u in js:
    name=('jquery.min.js' if 'jquery' in u else u.split('/')[-1].split('?')[0])
    jobs.append((u, f'assets/js/{name}'))
for u in fonts:
    name=u.split('/')[-1].split('?')[0]
    jobs.append((u, f'assets/fonts/{name}'))

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    futs=[ex.submit(get,u,d) for u,d in jobs]
    for f in concurrent.futures.as_completed(futs):
        try:
            p,s=f.result(); print(f'{s:>9} {p}')
        except Exception as e: print('ERR',e)
