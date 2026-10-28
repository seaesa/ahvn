#!/usr/bin/env python3
"""Build the static Cavani clone from captured research artifacts."""
import json, os, re, copy, shutil, unicodedata
from bs4 import BeautifulSoup, NavigableString

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

HOME_SRC = 'docs/research/rendered-home.html'
PRODUCTS = json.load(open('data/products.json', encoding='utf-8'))

FLATSOME_VARS = r'''var flatsomeVars = {"theme":{"version":"3.17.6"},"ajaxurl":"#","rtl":"","sticky_height":"70","stickyHeaderHeight":"0","scrollPaddingTop":"0","assets_url":"assets/","lightbox":{"close_markup":"\u003Cbutton title=\"%title%\" type=\"button\" class=\"mfp-close\"\u003E\u003Csvg xmlns=\"http://www.w3.org/2000/svg\" width=\"28\" height=\"28\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-x\"\u003E\u003Cline x1=\"18\" y1=\"6\" x2=\"6\" y2=\"18\"\u003E\u003C/line\u003E\u003Cline x1=\"6\" y1=\"6\" x2=\"18\" y2=\"18\"\u003E\u003C/line\u003E\u003C/svg\u003E\u003C/button\u003E","close_btn_inside":false},"user":{"can_edit_pages":false},"i18n":{"mainMenu":"Main Menu","toggleButton":"Toggle"},"options":{},"is_mini_cart_reveal":"1"};'''

# ---------------------------------------------------------------- helpers
def read_home():
    return BeautifulSoup(open(HOME_SRC, encoding='utf-8').read(), 'lxml')

def strip_slider_runtime(soup):
    for slider in soup.select('.slider'):
        vp = slider.find('div', class_='flickity-viewport', recursive=False)
        if vp:
            track = vp.find('div', class_='flickity-slider', recursive=False)
            if track:
                cells = list(track.children)
                for cell in cells:
                    if getattr(cell, 'attrs', None) is None:
                        continue
                    cell.attrs.pop('style', None)
                    cell.attrs.pop('aria-selected', None)
                    cell.attrs.pop('aria-label', None)
                    if 'is-selected' in (cell.get('class') or []):
                        cell['class'] = [c for c in cell['class'] if c != 'is-selected']
                for cell in cells:
                    vp.insert_before(cell.extract())
                vp.decompose()
        for cls in ('flickity-enabled', 'is-draggable', 'flickity-resize'):
            if cls in (slider.get('class') or []):
                slider['class'] = [c for c in slider['class'] if c != cls]
        slider.attrs.pop('tabindex', None)
        slider.attrs.pop('aria-label', None)
        for b in slider.select('.flickity-button, .flickity-page-dots'):
            b.decompose()
    # banners/cells that Flickity marked
    for el in soup.select('.is-selected'):
        el['class'] = [c for c in (el.get('class') or []) if c != 'is-selected']
    # animation replay
    for el in soup.select('[data-animated]'):
        del el['data-animated']
    for el in soup.select('[data-lazyloaded]'):
        del el['data-lazyloaded']
    for el in soup.select('[data-flickity-lazyload]'):
        del el['data-flickity-lazyload']

UPLOAD_RE = re.compile(r'https?://cavani\.vn/wp-content/uploads/[^\s"\'<>)]+')
THEME_RE = re.compile(r'https?://cavani\.vn/wp-content/themes/flatsome/assets/[^\s"\'<>)]+')

def localize_url(u):
    if not u:
        return u
    if 'icon-call-nh.png' in u:
        return 'assets/img/icon-call-nh.png'
    if 'cavani.vn/wp-content/uploads/' in u:
        name = u.split('/')[-1].split('?')[0]
        if name.startswith('cropped-logo-favicon'):
            return 'assets/img/favicon/' + name
        return 'assets/img/' + name
    if 'wp-content/themes/flatsome/assets/css/icons/' in u:
        return 'assets/fonts/' + u.split('/')[-1].split('?')[0]
    return u

def localize(soup):
    for tag in soup.find_all(True):
        for attr in ('src', 'data-src', 'data-bg', 'poster', 'href', 'data-large_image'):
            v = tag.get(attr)
            if isinstance(v, str) and 'icon-call-nh.png' in v:
                tag[attr] = 'assets/img/icon-call-nh.png'
            elif isinstance(v, str) and 'cavani.vn/wp-content/uploads/' in v:
                tag[attr] = localize_url(v)
        if tag.get('srcset'):
            del tag['srcset']
        if tag.get('sizes'):
            del tag['sizes']
        st = tag.get('style')
        if st and 'cavani.vn' in st:
            tag['style'] = UPLOAD_RE.sub(lambda m: localize_url(m.group(0)), st)
    for st_tag in soup.find_all('style'):
        if st_tag.string and 'cavani.vn' in st_tag.string:
            st_tag.string = UPLOAD_RE.sub(lambda m: localize_url(m.group(0)), st_tag.string)
    # never let a form fall back to submitting to the live site
    for form in soup.find_all('form'):
        action = form.get('action') or ''
        if 'cavani.vn' in action:
            form['action'] = '/'
    # fl-icons @font-face
    for st_tag in soup.find_all('style'):
        if st_tag.string and 'fl-icons' in st_tag.string:
            st_tag.string = re.sub(r'https?://cavani\.vn/wp-content/themes/flatsome/assets/css/icons/fl-icons\.(woff2|woff|ttf|eot|svg)(\?v=[^)\s]*)?',
                                   lambda m: 'assets/fonts/fl-icons.' + m.group(1), st_tag.string)

def rewrite_internal_links(soup):
    exact = {
        '/': 'index.html',
        '/den-trang-tri/': 'den-trang-tri.html',
        '/den-chieu-sang/': 'den-chieu-sang.html',
        '/luxury-decor/': 'luxury-decor.html',
        '/den-chum-co-dien/': 'den-chum-co-dien.html',
        '/den-chum-pha-le/': 'den-chum-pha-le.html',
        '/den-chum-hien-dai/': 'den-chum-hien-dai.html',
        '/danh-muc-san-pham/den-chum/den-chum-co-dien/': 'den-chum-co-dien.html',
        '/danh-muc-san-pham/den-chum/den-chum-pha-le/': 'den-chum-pha-le.html',
        '/danh-muc-san-pham/den-chum/den-chum-hien-dai/': 'den-chum-hien-dai.html',
        '/cart/': 'cart.html',
        '/lien-he/': 'lien-he.html',
        '/ve-chung-toi/': 've-chung-toi.html',
        '/du-an-tieu-bieu/': 'du-an-tieu-bieu.html',
        '/thiet-ke-den-trang-tri/': 'thiet-ke-den-trang-tri.html',
        '/thiet-ke-chieu-sang/': 'thiet-ke-chieu-sang.html',
        '/thiet-ke-doc-ban/': 'thiet-ke-doc-ban.html',
        '/category/tin-tuc-cavani/': 'category/tin-tuc-cavani.html',
        '/thanh-toan-va-bao-hanh/': 'thanh-toan-va-bao-hanh.html',
    }
    for a in soup.find_all('a', href=True):
        h = a['href']
        if h.startswith('https://cavani.vn'):
            path = h[len('https://cavani.vn'):] or '/'
        elif h.startswith('http://cavani.vn'):
            path = h[len('http://cavani.vn'):] or '/'
        elif h.startswith('/') and not h.startswith('//'):
            path = h
        else:
            continue
        if path in exact:
            a['href'] = exact[path]
            continue
        # product pages and other deep links: send to the matching collection
        for prefix, dest in [
            ('/den-chum-co-dien/', 'den-chum-co-dien.html'),
            ('/den-chum-pha-le/', 'den-chum-pha-le.html'),
            ('/den-chum-hien-dai/', 'den-chum-hien-dai.html'),
            ('/den-chum/', 'den-trang-tri.html'),
            ('/den-trang-tri/', 'den-trang-tri.html'),
            ('/den-chieu-sang/', 'den-chieu-sang.html'),
            ('/luxury-decor/', 'luxury-decor.html'),
            ('/den-tuong/', 'den-trang-tri.html'),
            ('/den-ban/', 'den-trang-tri.html'),
            ('/den-op/', 'den-trang-tri.html'),
        ]:
            if path.startswith(prefix):
                a['href'] = dest
                break
        else:
            if '/du-an' in path or '/video/' in path:
                a['href'] = 'du-an-tieu-bieu.html'
            elif '/tin-tuc' in path or '/blog' in path or path.count('/') >= 4:
                a['href'] = 'category/tin-tuc-cavani.html'
            else:
                a['href'] = 'index.html'

def fix_nav(soup):
    """Rewrite the main menu and mobile menu to match the live Cavani structure."""
    nav_map = {
        'SẢN PHẨM': ('/den-trang-tri/', [
            ('ĐÈN TRANG TRÍ', '/den-trang-tri/'),
            ('ĐÈN CHIẾU SÁNG', '/den-chieu-sang/'),
            ('LUXURY DECOR', '/luxury-decor/'),
        ]),
        'DỊCH VỤ': ('/thiet-ke-chieu-sang/', [
            ('THIẾT KẾ ĐÈN TRANG TRÍ', '/thiet-ke-den-trang-tri/'),
            ('THIẾT KẾ CHIẾU SÁNG', '/thiet-ke-chieu-sang/'),
            ('THIẾT KẾ ĐỘC BẢN', '/thiet-ke-doc-ban/'),
        ]),
        'TIN TỨC': ('/category/tin-tuc-cavani/', [
            ('THANH TOÁN VÀ BẢO HÀNH', '/thanh-toan-va-bao-hanh/'),
            ('VỀ CHÚNG TÔI', '/ve-chung-toi/'),
        ]),
    }
    for li in soup.select('#main-menu li.menu-item-has-children, ul.header-nav li.menu-item-has-children'):
        a = li.find('a', recursive=False)
        if not a:
            continue
        label = a.get_text(' ', strip=True).upper()
        for key, (href, children) in nav_map.items():
            if key in label:
                a['href'] = href
                sub = li.find('ul', class_='sub-menu')
                if sub:
                    for child, (clabel, chref) in zip(sub.find_all('li', recursive=False), children):
                        ca = child.find('a')
                        if ca:
                            ca['href'] = chref
                            ca.string = clabel
                break
    # Simple top-level items (desktop + mobile)
    for li in soup.select('#main-menu > .sidebar-menu > ul > li, ul.header-nav > li'):
        a = li.find('a', recursive=False)
        if not a:
            continue
        label = a.get_text(' ', strip=True).upper()
        if 'TRANG CH' in label:
            a['href'] = '/'
        elif label == 'DỰ ÁN':
            a['href'] = '/du-an-tieu-bieu/'
        elif label == 'LIÊN HỆ':
            a['href'] = '/lien-he/'
        elif 'ĐĂNG NHẬP' in label:
            a['href'] = '/lien-he/'
    # Flatsome injects the submenu toggle at runtime; captured DOM already has it -> drop all
    for btn in soup.select('#main-menu button.toggle'):
        btn.decompose()

def fix_home_content(soup):
    # Keep original section ID: inline CSS is keyed to #section_1088443042.

    cards = soup.select('#section_1784693606 .col.codien')
    if len(cards) >= 3:
        data = [
            ('assets/img/Den-chum-hien-dai-Chau-Au-sang-trong-2-scaled.jpg', 'SERIP Lighting', '/den-chum-hien-dai/', 'SERIP LIGHTING'),
            ('assets/img/phale.jpg', 'Baccarat Lighting', '/den-chum-pha-le/', 'BACCARAT LIGHTING'),
            ('assets/img/codien4.jpg', 'Đèn Tân Cổ Điển', '/den-chum-co-dien/', 'ĐÈN TÂN CỔ ĐIỂN'),
        ]
        for col, (img, alt, href, label) in zip(cards, data):
            im = col.select_one('img')
            if im:
                im['src'] = img
                im['alt'] = alt
                im['title'] = alt
            link = col.select_one('.img > a')
            if link: link['href'] = href
            btn = col.select_one('a.button')
            if btn:
                btn['href'] = href
                span = btn.find('span')
                if span: span.string = label

    # Hero links -> relevant collection
    hero = soup.select_one('#slider-1222362058')
    if hero:
        for a in hero.find_all('a', href=True):
            if a['href'].startswith(('https://cavani.vn/', '/')) and not a['href'].startswith('//'):
                a['href'] = '/den-trang-tri/'

def fix_lazy_images(soup):
    """LiteSpeed/Flatsome lazyload markup leaves placeholder src values behind.
    Promote data-src/data-bg to real attributes so images render without JS."""
    for el in soup.select('[data-src]'):
        ds = el.get('data-src')
        if ds:
            el['src'] = ds
        for a in ('data-src', 'data-lazyloaded', 'loading'):
            if el.has_attr(a):
                del el[a]
    for el in soup.select('[data-bg]'):
        bg = el.get('data-bg')
        if bg and ('/' in bg or bg.startswith('assets/')):
            st = (el.get('style') or '').strip()
            if 'background-image' not in st:
                st = (st + ';' if st else '') + 'background-image:url(%s)' % bg
            el['style'] = st
            classes = el.get('class') or []
            if 'bg' in classes and 'bg-loaded' not in classes:
                el['class'] = classes + ['bg-loaded']
        del el['data-bg']
    for el in soup.select('[data-flickity-lazyload]'):
        ds = el.get('data-flickity-lazyload')
        if ds:
            el['src'] = ds
        del el['data-flickity-lazyload']
    # responsive data attributes are unused by the local Flatsome runtime and
    # still point at the live CDN; the promoted src is already local.
    for el in soup.select('[data-srcset], [data-sizes]'):
        for attr in ('data-srcset', 'data-sizes'):
            if el.has_attr(attr):
                del el[attr]

def strip_unwanted(soup):
    # stale LiteSpeed critical CSS: the live custom CSS has this commented out
    for st in soup.find_all('style', id='litespeed-ccss'):
        if st.string:
            st.string = st.string.replace('.woocommerce-breadcrumb{display:none}', '')
    # scripts / noscript / GTM / litespeed
    for s in soup.find_all('script'):
        s.decompose()
    for n in soup.find_all('noscript'):
        n.decompose()
    for c in soup.find_all(string=lambda t: isinstance(t, NavigableString) and 'litespeed' in str(t).lower()):
        c.extract()
    for link in list(soup.find_all('link')):
        href = link.get('href') or ''
        rel = ' '.join(link.get('rel') or [])
        if 'litespeed/ucss/' in href:
            tags = []
            for href2 in ['assets/css/wc-blocks.css', 'assets/css/all.css', 'assets/css/v4-shims.css',
                          'assets/css/flatsome.css', 'assets/css/flatsome-shop.css', 'assets/css/site.css']:
                l2 = soup.new_tag('link', rel='stylesheet', href=href2)
                tags.append(l2)
            for l2 in reversed(tags):
                link.insert_after(l2)
            link.decompose()
            continue
        if 'stylesheet' in rel:
            if 'fonts.googleapis.com' in href:
                continue
            mapping = {
                'flatsome-shop.css': 'assets/css/flatsome-shop.css',
                'flatsome.css': 'assets/css/flatsome.css',
                'wc-blocks.css': 'assets/css/wc-blocks.css',
                'v4-shims.css': 'assets/css/v4-shims.css',
                '/all.css': 'assets/css/all.css',
                'flatsome-child/style.css': 'assets/css/site.css',
            }
            new = None
            for key, val in mapping.items():
                if key in href:
                    new = val
                    break
            if new:
                link['href'] = new
                for a in ('integrity', 'crossorigin'):
                    if link.has_attr(a): del link[a]
            else:
                link.decompose()
        elif any(x in rel for x in ('prefetch', 'dns-prefetch', 'profile', 'pingback', 'canonical',
                                    'alternate', 'shortlink', 'EditURI', 'https://api.w.org/',
                                    'next', 'prev')):
            link.decompose()
    for meta in soup.find_all('meta'):
        if (meta.get('name') or '') in ('generator',):
            meta.decompose()

def build_head(soup, title, extra_css=''):
    head = soup.head
    # title
    t = head.find('title')
    if t: t.string = title
    # replace favicons
    for l in list(head.find_all('link')):
        rel = ' '.join(l.get('rel') or [])
        if 'icon' in rel:
            l.decompose()
    for rel, href, sizes in [
        ('icon', 'assets/img/favicon/cropped-logo-favicon-5-32x32.png', '32x32'),
        ('icon', 'assets/img/favicon/cropped-logo-favicon-5-192x192.png', '192x192'),
        ('apple-touch-icon', 'assets/img/favicon/cropped-logo-favicon-5-180x180.png', '180x180')]:
        link = soup.new_tag('link', rel=rel, href=href)
        if sizes: link['sizes'] = sizes
        head.append(link)
    # local css already placed in original cascade order; add only if missing
    if not any((l.get('href') or '').startswith('assets/css/') for l in head.find_all('link')):
        for href in ['assets/css/flatsome.css', 'assets/css/flatsome-shop.css', 'assets/css/wc-blocks.css',
                     'assets/css/all.css', 'assets/css/v4-shims.css', 'assets/css/site.css']:
            link = soup.new_tag('link', rel='stylesheet', href=href)
            head.append(link)
    if extra_css:
        st = soup.new_tag('style')
        st.string = extra_css
        head.append(st)

def script_tags(prefix=''):
    vars_js = FLATSOME_VARS.replace('"assets_url":"assets/"', '"assets_url":"%sassets/"' % prefix)
    return '''
<script>window.CAVANI_BASE='%s';</script>
<script>%s</script>
<script src="%sassets/js/jquery.min.js"></script>
<script src="%sassets/js/jquery-migrate.min.js"></script>
<script src="%sassets/js/jquery.hoverIntent.min.js"></script>
<script src="%sassets/js/flatsome.js"></script>
<script src="%sassets/js/products.js"></script>
<script src="%sassets/js/app.js"></script>
''' % (prefix, vars_js, prefix, prefix, prefix, prefix, prefix, prefix)

LINK_HTML_RE = re.compile(
    r'^(?:\./)?((?:[a-z0-9][a-z0-9-]*/)*[a-z0-9][a-z0-9-]*)\.html((?:\?[^#]*)?(?:#.*)?)$'
)

def clean_urls(soup, prefix=''):
    """Turn flat *.html links into directory URLs and rebase local assets."""
    for a in soup.find_all('a', href=True):
        h = a['href']
        if not h or h.startswith(('http://', 'https://', '//', '/', 'mailto:', 'tel:', 'javascript:', '#')):
            continue
        m = LINK_HTML_RE.match(h)
        if not m:
            continue
        slug, rest = m.group(1), m.group(2) or ''
        if slug == 'index':
            a['href'] = (prefix if prefix else './') + rest
        else:
            a['href'] = prefix + slug + '/' + rest

    for tag in soup.find_all(True):
        for attr, v in list(tag.attrs.items()):
            if attr == 'srcset':
                continue
            if isinstance(v, str) and v.startswith('assets/'):
                tag[attr] = prefix + v
        st = tag.get('style')
        if st and 'assets/' in st:
            tag['style'] = re.sub(r'url\(\s*(["\']?)assets/',
                                  lambda m: 'url(' + m.group(1) + prefix + 'assets/', st, flags=re.I)
        ss = tag.get('srcset')
        if ss and prefix and 'assets/' in ss:
            tag['srcset'] = re.sub(r'(^|,\s*)(assets/)',
                                   lambda m: m.group(1) + prefix + m.group(2), ss)
    for st_tag in soup.find_all('style'):
        if st_tag.string and 'assets/' in st_tag.string:
            st_tag.string = re.sub(r'url\(\s*(["\']?)assets/',
                                   lambda m: 'url(' + m.group(1) + prefix + 'assets/',
                                   st_tag.string, flags=re.I)

def fix_content_links(soup):
    footer_map = {
        'Đèn tường Châu Âu': 'den-trang-tri.html',
        'Đèn bàn Châu Âu': 'den-trang-tri.html',
        'Đèn ốp Châu Âu': 'den-trang-tri.html',
    }
    for a in soup.find_all('a'):
        t = a.get_text(' ', strip=True)
        is_blog = (
            a.find_parent(class_='box-blog-post')
            or a.find_parent(class_='blog-post')
            or a.find_parent(class_='image-cover')
        )
        if is_blog and a.get('href') in (None, '#', './', 'index.html'):
            a['href'] = 'category/tin-tuc-cavani.html'
        elif a.get('href') == '#':
            if t == 'Possoni – Ý':
                a['href'] = 've-chung-toi.html'
            elif t in footer_map:
                a['href'] = footer_map[t]
            elif t == 'Đăng nhập':
                a['href'] = 'lien-he.html'
    for img in soup.find_all('img'):
        src = img.get('src') or ''
        if 'nguyenhung.net' in src:
            img['src'] = 'assets/img/icon-call-nh.png'

NAV_TARGETS = {
    'index.html': '/',
    'den-trang-tri.html': '/den-trang-tri/',
    'den-chieu-sang.html': '/den-chieu-sang/',
    'luxury-decor.html': '/luxury-decor/',
    'den-chum-hien-dai.html': '/den-trang-tri/',
    'den-chum-pha-le.html': '/den-trang-tri/',
    'den-chum-co-dien.html': '/den-trang-tri/',
    'thiet-ke-den-trang-tri.html': '/thiet-ke-den-trang-tri/',
    'thiet-ke-chieu-sang.html': '/thiet-ke-chieu-sang/',
    'thiet-ke-doc-ban.html': '/thiet-ke-doc-ban/',
    'du-an-tieu-bieu.html': '/du-an-tieu-bieu/',
    'category/tin-tuc-cavani.html': '/category/tin-tuc-cavani/',
    'thanh-toan-va-bao-hanh.html': '/thanh-toan-va-bao-hanh/',
    've-chung-toi.html': '/ve-chung-toi/',
    'lien-he.html': '/lien-he/',
}

NAV_ACTIVE_CLASSES = {
    'current-menu-item', 'current-menu-ancestor', 'current-menu-parent',
    'current_page_item', 'current_page_parent', 'current_page_ancestor', 'active',
}

def _nav_norm(h):
    if not h:
        return ''
    h = h.strip()
    if h.startswith('#'):
        return ''
    for dom in ('https://cavani.vn', 'http://cavani.vn'):
        if h.startswith(dom):
            h = h[len(dom):] or '/'
            break
    h = h.split('#')[0].split('?')[0]
    if not h.startswith('/'):
        h = '/' + h.lstrip('./')
    return h.rstrip('/') or '/'

def _nav_add(li, *classes):
    cls = li.get('class') or []
    for c in classes:
        if c not in cls:
            cls.append(c)
    li['class'] = cls

def set_active_nav(soup, path):
    """Apply the live Cavani active-menu classes for the page being written."""
    target = NAV_TARGETS.get(path)
    if target is None:
        if path.startswith('category/tin-tuc-cavani'):
            target = '/category/tin-tuc-cavani/'
        else:
            first = path.split('/', 1)[0]
            if first in ('den-chum-hien-dai', 'den-chum-pha-le', 'den-chum-co-dien') and '/' in path:
                target = '/den-trang-tri/'
    if target:
        target = _nav_norm(target)
    current = '/' if path == 'index.html' else _nav_norm(path[:-5] + '/' if path.endswith('.html') else path)

    for nav in (soup.select_one('#main-menu'), soup.select_one('ul.header-nav')):
        if not nav:
            continue
        for li in nav.select('li'):
            li['class'] = [c for c in (li.get('class') or []) if c not in NAV_ACTIVE_CLASSES]
        for a in nav.select('a[aria-current]'):
            del a['aria-current']
        if not target:
            continue
        for li in nav.select('li'):
            if 'account-item' in (li.get('class') or []):
                continue
            a = li.find('a', recursive=False)
            if not a:
                continue
            if _nav_norm(a.get('href')) != target:
                continue
            _nav_add(li, 'active')
            if _nav_norm(a.get('href')) == current:
                _nav_add(li, 'current-menu-item')
            if 'menu-item-type-post_type' in (li.get('class') or []) and _nav_norm(a.get('href')) == current:
                _nav_add(li, 'page_item', 'current_page_item')
            if path == 'index.html':
                _nav_add(li, 'current_page_item')
            if _nav_norm(a.get('href')) == current:
                a['aria-current'] = 'page'
            sub = li.find_parent('ul', class_='sub-menu')
            if sub:
                parent = sub.find_parent('li')
                if parent:
                    _nav_add(parent, 'current-menu-ancestor', 'current-menu-parent', 'active')
                    pa = parent.find('a', recursive=False)
                    if pa and _nav_norm(pa.get('href')) == current:
                        _nav_add(parent, 'current-menu-item')

    if path == 'cart.html':
        for a in soup.select('a.header-cart-link'):
            cls = a.get('class') or []
            if 'active' not in cls:
                cls.append('active')
            a['class'] = cls
            a['aria-current'] = 'page'

def page_output(path):
    if path == 'index.html':
        return path
    d = os.path.dirname(path)
    base = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(d, base, 'index.html')

def write_doc(soup, path, title):
    out_path = page_output(path)
    depth = out_path.count(os.sep)
    prefix = '../' * depth
    fix_content_links(soup)
    fix_lazy_images(soup)
    build_head(soup, title)
    set_active_nav(soup, path)
    # remove all old script tags then append ours
    for s in soup.find_all('script'):
        s.decompose()
    body = soup.body
    body.append(BeautifulSoup(script_tags(prefix), 'html.parser'))
    clean_urls(soup, prefix)
    # strip helper classes from html
    html = soup.html
    html['class'] = ['js']
    out = '<!DOCTYPE html>\n' + str(soup)
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    open(out_path, 'w', encoding='utf-8').write(out)
    print('wrote', out_path, len(out))

# ---------------------------------------------------------------- homepage
def build_home():
    soup = read_home()
    strip_unwanted(soup)
    strip_slider_runtime(soup)
    localize(soup)
    rewrite_internal_links(soup)
    fix_nav(soup)
    fix_home_content(soup)
    fix_content_links(soup)
    # cart link text + count
    for a in soup.select('a.header-cart-link'):
        a['href'] = 'cart.html'
    # remove login popup (no backend)
    lp = soup.select_one('#login-form-popup')
    if lp: lp.decompose()
    write_doc(soup, 'index.html', 'Đèn trang trí Châu Âu cao cấp | Cavani Lighting')


# ---------------------------------------------------------------- category pages
COLLECTIONS = {
    'serip': {
        'file': 'den-chum-hien-dai.html',
        'slug': 'den-chum-hien-dai',
        'cats': ['serip'],
        'title': 'Đèn chùm hiện đại cao cấp | Cavani Lighting',
        'name': 'SERIP LIGHTING',
        'h1': 'SERIP LIGHTING – NGHỆ THUẬT ÁNH SÁNG Ý',
        'intro': [
            'SERIP Lighting là thương hiệu đèn nghệ thuật đến từ Ý, nổi tiếng với những thiết kế điêu khắc ánh sáng lấy cảm hứng từ thiên nhiên, hoa lá và chuyển động. Mỗi tác phẩm là sự kết hợp tinh xảo giữa kim loại mạ vàng, pha lê và kỹ thuật chế tác thủ công của các nghệ nhân Ý.',
            'Tại Cavani, bộ sưu tập SERIP Lighting mang đến giải pháp ánh sáng độc bản cho biệt thự, penthouse, khách sạn và không gian nghệ thuật – nơi mỗi chiếc đèn không chỉ chiếu sáng mà còn là một tác phẩm điêu khắc.',
        ],
        'desc': 'SERIP Lighting – kiệt tác đèn nghệ thuật Ý, thiết kế độc bản, chế tác thủ công cho không gian thượng lưu.',
    },
    'baccarat': {
        'file': 'den-chum-pha-le.html',
        'slug': 'den-chum-pha-le',
        'cats': ['baccarat'],
        'title': 'Đèn chùm pha lê cao cấp | Cavani Lighting',
        'name': 'BACCARAT LIGHTING',
        'h1': 'BACCARAT LIGHTING – PHA LÊ CAO CẤP',
        'intro': [
            'BACCARAT Lighting là biểu tượng của sự xa hoa với những chiếc đèn chùm pha lê được chế tác tỉ mỉ, mang vẻ đẹp lấp lánh và đẳng cấp vượt thời gian. Từng viên pha lê được cắt gọt nhiều mặt, tán xạ ánh sáng thành những tia sáng tinh tế khắp không gian.',
            'Bộ sưu tập BACCARAT Lighting tại Cavani dành cho những không gian cần sự sang trọng tuyệt đối: sảnh biệt thự, phòng khách lớn, phòng tiệc, khách sạn 5 sao và showroom cao cấp.',
        ],
        'desc': 'BACCARAT Lighting – đèn chùm pha lê cao cấp, lấp lánh và đẳng cấp cho không gian xa hoa.',
    },
    'tan-co-dien': {
        'file': 'den-chum-co-dien.html',
        'slug': 'den-chum-co-dien',
        'cats': ['tan-co-dien'],
        'title': 'Đèn chùm cổ điển cao cấp | Cavani Lighting',
        'name': 'ĐÈN TÂN CỔ ĐIỂN',
        'h1': 'ĐÈN TÂN CỔ ĐIỂN CAO CẤP',
        'intro': [
            'Đèn Tân Cổ Điển là sự giao thoa hoàn hảo giữa nét cổ điển sang trọng và tinh thần hiện đại. Những đường nét uốn lượn, chất liệu đồng mạ vàng, pha lê và thủy tinh màu tạo nên vẻ đẹp quý phái nhưng vẫn phù hợp với kiến trúc đương đại.',
            'Bộ sưu tập Đèn Tân Cổ Điển của Cavani được tuyển chọn từ các thương hiệu Possoni, BC Sanmichele, Stillux – Ý và Copenlamp – Tây Ban Nha, mang đến giải pháp hoàn thiện cho biệt thự, dinh thự và không gian nội thất cao cấp.',
        ],
        'desc': 'Đèn Tân Cổ Điển cao cấp – sự giao thoa giữa nét cổ điển sang trọng và tinh thần hiện đại.',
    },
}

TOP_CATS = {
    'den-trang-tri': {
        'file': 'den-trang-tri.html',
        'slug': 'den-trang-tri',
        'cats': ['serip', 'baccarat', 'tan-co-dien'],
        'title': 'Đèn trang trí cao cấp Cavani - Nơi hội tụ tinh hoa Châu Âu',
        'name': 'ĐÈN TRANG TRÍ',
        'h1': 'ĐÈN TRANG TRÍ CAO CẤP',
        'intro': [
            'Đèn trang trí không chỉ là nguồn sáng mà còn là điểm nhấn nghệ thuật, tô điểm cho không gian sống và thể hiện gu thẩm mỹ của gia chủ. Mỗi bộ sưu tập tại Cavani được tuyển chọn từ những thương hiệu đèn cao cấp nhất Châu Âu.',
            'Từ đèn chùm cổ điển, tân cổ điển đến những thiết kế hiện đại điêu khắc ánh sáng, Cavani mang đến giải pháp hoàn thiện cho biệt thự, dinh thự, khách sạn và không gian thượng lưu.',
        ],
        'desc': 'Đèn trang trí cao cấp Cavani – nơi hội tụ tinh hoa đèn nghệ thuật Châu Âu.',
    },
    'den-chieu-sang': {
        'file': 'den-chieu-sang.html',
        'slug': 'den-chieu-sang',
        'cats': ['serip'],
        'title': 'Đèn Chiếu Sáng - Cavani.vn - Đèn Trang Trí Cao Cấp Châu Âu',
        'name': 'ĐÈN CHIẾU SÁNG',
        'h1': 'ĐÈN CHIẾU SÁNG CAO CẤP',
        'intro': [
            'Đèn chiếu sáng là yếu tố quyết định đến tính thẩm mỹ và công năng của mỗi không gian. Cavani cung cấp giải pháp chiếu sáng đồng bộ, kết hợp hài hòa giữa ánh sáng công năng và ánh sáng trang trí.',
            'Các bộ sưu tập đèn chiếu sáng của Cavani được lựa chọn từ những thương hiệu Châu Âu, đáp ứng tiêu chuẩn khắt khe về độ bền, hiệu suất và vẻ đẹp thẩm mỹ.',
        ],
        'desc': 'Đèn chiếu sáng cao cấp – giải pháp ánh sáng đồng bộ cho biệt thự, khách sạn và không gian thương mại.',
    },
    'luxury-decor': {
        'file': 'luxury-decor.html',
        'slug': 'luxury-decor',
        'cats': ['baccarat'],
        'title': 'LUXURY DECOR - Cavani.vn - Đèn Trang Trí Cao Cấp Châu Âu',
        'name': 'LUXURY DECOR',
        'h1': 'LUXURY DECOR',
        'intro': [
            'LUXURY DECOR là bộ sưu tập dành cho những không gian cần sự sang trọng tuyệt đối. Những tác phẩm đèn pha lê, đồng mạ vàng và thủy tinh nghệ thuật được chế tác tỉ mỉ, tạo nên vẻ đẹp lấp lánh và đẳng cấp vượt thời gian.',
            'Cavani tuyển chọn những thiết kế độc đáo từ các thương hiệu Châu Âu, mang đến điểm nhấn xa hoa cho sảnh biệt thự, phòng khách lớn, phòng tiệc và khách sạn 5 sao.',
        ],
        'desc': 'LUXURY DECOR – bộ sưu tập đèn trang trí xa hoa, đẳng cấp cho không gian thượng lưu.',
    },
}

CATS = {**COLLECTIONS, **TOP_CATS}

def fmt_price(n):
    return f"{int(n):,}".replace(',', '.') + '₫'

def slugify(text):
    text = text.lower().replace('đ', 'd')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text or 'san-pham'

def prepare_products():
    seen = set()
    for p in PRODUCTS:
        cfg = COLLECTIONS[p['cat']]
        base = slugify(p['name'])
        slug = base
        n = 2
        while (p['cat'], slug) in seen:
            slug = '%s-%d' % (base, n)
            n += 1
        seen.add((p['cat'], slug))
        p['slug'] = slug
        p['catSlug'] = cfg['slug']
        p['url'] = '/%s/%s/' % (cfg['slug'], slug)
        p['path'] = '%s/%s.html' % (cfg['slug'], slug)
    with open('data/products.json', 'w', encoding='utf-8') as f:
        json.dump(PRODUCTS, f, ensure_ascii=False, indent=2)
    with open('assets/js/products.js', 'w', encoding='utf-8') as f:
        f.write('window.CAVANI_PRODUCTS = ' + json.dumps(PRODUCTS, ensure_ascii=False) + ';\n')
    print('prepared', len(PRODUCTS), 'products')

def product_card(p):
    pid = p['id']
    href = p['url']
    name = p['name'].replace('&', '&amp;')
    return f'''<div class="product-small col has-hover product type-product status-publish instock product_cat-{p['cat']} has-post-thumbnail shipping-taxable purchasable product-type-simple">
<div class="col-inner"><div class="badge-container absolute left top z-1"></div>
<div class="product-small box"><div class="box-image"><div class="image-zoom">
<a aria-label="{name}" href="{href}"><img alt="{name}" class="attachment-woocommerce_thumbnail size-woocommerce_thumbnail" decoding="async" loading="lazy" src="{p['img']}" width="1000" height="1000"/></a></div>
<div class="image-tools is-small top right show-on-hover"></div>
<div class="image-tools grid-tools text-center hide-for-small bottom hover-slide-in show-on-hover">
<a aria-label="Thêm vào giỏ hàng: {name}" class="add-to-cart-grid no-padding is-transparent product_type_simple add_to_cart_button ajax_add_to_cart" data-product_id="{pid}" data-product_sku="" data-quantity="1" href="{href}" rel="nofollow" role="button"><div class="cart-icon tooltip is-small" title="Thêm vào giỏ hàng"><strong>+</strong></div></a>
<a class="quick-view" data-prod="{pid}" href="{href}">Quick View</a></div></div>
<div class="box-text box-text-products text-center grid-style-2"><div class="title-wrapper">
<p class="category uppercase is-smaller no-text-overflow product-cat op-7">{p['catName']}</p>
<p class="name product-title woocommerce-loop-product__title"><a class="woocommerce-LoopProduct-link woocommerce-loop-product__link" href="{href}">{name}</a></p></div>
<div class="price-wrapper"><span class="price"><span class="woocommerce-Price-amount amount"><bdi>{fmt_price(p['price'])}<span class="woocommerce-Price-currencySymbol">₫</span></bdi></span></span></div></div>
</div></div></div>'''

def build_category(cat_key):
    cfg = CATS[cat_key]
    products = [p for p in json.load(open('data/products.json', encoding='utf-8')) if p['cat'] in cfg['cats']]
    soup = BeautifulSoup(open('/tmp/cat.html', encoding='utf-8').read(), 'html.parser')
    if soup.body:
        soup.body['class'] = (soup.body.get('class') or []) + ['cavani-cat']
    strip_unwanted(soup)
    localize(soup)
    rewrite_internal_links(soup)
    fix_nav(soup)

    # page title / breadcrumb / count
    bc = soup.select_one('.woocommerce-breadcrumb')
    if bc:
        bc.clear(); bc.append(cfg['name'])
    count = soup.select_one('.woocommerce-result-count')
    if count:
        count.string = f"Hiển thị 1–{len(products)} của {len(products)} kết quả"

    # term description: replace heading + intro, drop category-card row
    td = soup.select_one('.term-description')
    if td:
        first_row = td.select_one('.row')
        if first_row:
            col_inner = first_row.select_one('.col-inner')
            if col_inner:
                col_inner.clear()
                text_div = soup.new_tag('div', **{'class': 'text'})
                h1 = soup.new_tag('h1')
                h1['style'] = 'font-weight:bold;'
                h1.string = cfg['h1']
                text_div.append(h1)
                col_inner.append(text_div)
                for para in cfg['intro']:
                    p = soup.new_tag('p')
                    p['style'] = 'text-align:justify;'
                    p.string = para
                    col_inner.append(p)
        # replace category cards row with the three requested collections
        rows = td.select('.row')
        if len(rows) > 1:
            rows[1].decompose()
        if first_row:
            cards_html = '<div class="row row-small row-full-width align-middle align-center" id="row-cat-cards"><div class="col small-12 large-12"><div class="col-inner"><div class="row large-columns-3 medium-columns-3 small-columns-2 row-small row-full-width">'
            for key, label, img in [
                ('serip', 'SERIP LIGHTING', 'assets/img/Den-chum-hien-dai-Chau-Au-sang-trong-2-scaled.jpg'),
                ('baccarat', 'BACCARAT LIGHTING', 'assets/img/phale.jpg'),
                ('tan-co-dien', 'ĐÈN TÂN CỔ ĐIỂN', 'assets/img/codien4.jpg')]:
                cards_html += f'<div class="product-category col"><div class="col-inner"><a aria-label="Truy cập danh mục sản phẩm {label}" href="{CATS[key]["file"]}"><div class="box box-category has-hover box-shade dark"><div class="box-image"><div class=""><img alt="{label}" height="300" src="{img}" width="300"/><div class="shade"></div></div></div><div class="box-text text-center"><div class="box-text-inner"><h5 class="uppercase header-title">{label}</h5></div></div></div></a></div></div>'
            cards_html += '</div></div></div></div>'
            first_row.insert_after(BeautifulSoup(cards_html, 'html.parser'))

    # product grid
    grid = soup.select_one('.products')
    if grid:
        grid.clear()
        grid['class'] = ['products', 'row', 'row-small', 'large-columns-3', 'medium-columns-3', 'small-columns-2', 'equalize-box']
        for p in products:
            grid.append(BeautifulSoup(product_card(p), 'html.parser'))

    # pagination container
    pag = soup.select_one('.shop-container > .container')
    if pag:
        pag.decompose()

    # sidebar: replace menu + counts
    side = soup.select_one('#shop-sidebar')
    if side:
        title = side.select_one('.widget_nav_menu .widget-title')
        if title:
            title.string = 'BỘ SƯU TẬP'
        menu = side.select_one('.widget_nav_menu ul.menu')
        if menu:
            menu.clear()
            for key, label in [('serip', 'SERIP LIGHTING'), ('baccarat', 'BACCARAT LIGHTING'), ('tan-co-dien', 'ĐÈN TÂN CỔ ĐIỂN')]:
                li = soup.new_tag('li', **{'class': 'menu-item'})
                if key == cat_key:
                    li['class'] = ['menu-item', 'current-menu-item']
                a = soup.new_tag('a', href=CATS[key]['file'])
                a.string = label
                li.append(a)
                menu.append(li)
        # brand counts stay decorative; link them to current category
        for a in side.select('.cavani-brand-filter a'):
            a['href'] = cfg['file']

    # SEO section heading
    seo = soup.select_one('.shop-container > section.section')
    if seo:
        h2 = seo.find('h2')
        if h2:
            h2.string = cfg['h1'] + ' – TÔN VINH KHÔNG GIAN SỐNG'

    # meta description
    md = soup.find('meta', attrs={'name': 'description'})
    if md:
        md['content'] = cfg['desc']

    # body class marker
    if soup.body:
        soup.body['class'] = [c for c in (soup.body.get('class') or []) if not c.startswith('term-')]
        soup.body['class'] += ['term-' + cat_key]

    write_doc(soup, cfg['file'], cfg['title'])



# ---------------------------------------------------------------- product page
PRODUCT_HTML = r'''
<div class="shop-container">
  <div class="container"><div class="woocommerce-notices-wrapper"></div></div>
  <div id="product-1" class="product type-product status-publish first instock has-post-thumbnail shipping-taxable purchasable product-type-simple">
    <div class="product-container">
      <div class="product-main">
        <div class="row content-row mb-0">
          <div class="col large-2 hide-for-medium product-sidebar-small" id="product-sidebar">
            <aside class="widget woocommerce widget_product_categories">
              <span class="widget-title shop-sidebar">DANH MỤC</span><div class="is-divider small"></div>
              <ul class="product-categories">
                <li class="cat-item"><a href="serip-lighting.html">SERIP LIGHTING</a></li>
                <li class="cat-item"><a href="baccarat-lighting.html">BACCARAT LIGHTING</a></li>
                <li class="cat-item"><a href="den-tan-co-dien.html">ĐÈN TÂN CỔ ĐIỂN</a></li>
              </ul>
            </aside>
          </div>
          <div class="product-gallery large-7 col">
            <div class="row row-small">
              <div class="col large-10">
                <div class="woocommerce-product-gallery woocommerce-product-gallery--with-images woocommerce-product-gallery--columns-4 images relative mb-half has-hover" data-columns="4">
                  <div class="badge-container is-larger absolute left top z-1"></div>
                  <div class="image-tools absolute top show-on-hover right z-3"></div>
                  <div class="woocommerce-product-gallery__wrapper product-gallery-slider slider slider-nav-small mb-0 has-image-zoom" data-flickity-options='{"cellAlign":"center","wrapAround":true,"autoPlay":false,"prevNextButtons":true,"adaptiveHeight":true,"imagesLoaded":true,"lazyLoad":1,"dragThreshold":15,"pageDots":false,"rightToLeft":false}'>
                    <div class="woocommerce-product-gallery__image slide first">
                      <a id="pdp-img-link" href="#"><img id="pdp-img" alt="" class="wp-post-image skip-lazy" src="assets/img/codien4.jpg" width="1000" height="1000"/></a>
                    </div>
                  </div>
                  <div class="image-tools absolute bottom left z-3"><a class="zoom-button button is-outline circle icon tooltip hide-for-small" href="#product-zoom" title="Zoom"><i class="icon-expand"></i></a></div>
                </div>
              </div>
              <div class="col large-2 product-thumbnails">
                <div class="product-thumbnails thumbnails slider-no-arrows slider row row-small row-slider slider-nav-small small-columns-4" data-flickity-options='{"cellAlign":"left","wrapAround":false,"autoPlay":false,"prevNextButtons":false,"asNavFor":".product-gallery-slider","percentPosition":true,"imagesLoaded":true,"pageDots":false,"rightToLeft":false,"contain":true}'>
                  <div class="col is-nav-selected first"><a><img id="pdp-thumb" alt="" class="attachment-woocommerce_thumbnail" src="assets/img/codien4.jpg"/></a></div>
                </div>
              </div>
            </div>
          </div>
          <div class="product-info summary col col-fit entry-summary product-summary text-left">
            <nav class="woocommerce-breadcrumb breadcrumbs uppercase"><a href="index.html">Trang chủ</a> <span class="divider">/</span> <a id="pdp-cat-link" href="#">Bộ sưu tập</a></nav>
            <h1 class="product-title product_title entry-title" id="pdp-title">Đang tải…</h1>
            <div class="price-wrapper"><p class="price product-page-price"><span class="woocommerce-Price-amount amount"><bdi id="pdp-price">Liên hệ</bdi></span></p></div>
            <div class="product-short-description">
              <hr/>
              <h4 class="text-xs font-bold uppercase tracking-widest"><span style="font-size:105%;font-family:'Crimson Text';color:#000000;"><strong>DETAILS &amp; DIMENSIONS</strong></span></h4>
              <table class="parameter-list active"><tbody>
                <tr><td class="specname"><strong><span style="color:#000000;"><i class="fas fa-arrows-to-dot"></i>&nbsp; Mã sản phẩm:</span></strong></td><td class="specval"><span id="pdp-sku" style="font-size:90%;color:#808080;">—</span></td></tr>
                <tr><td class="specname"><strong><span style="color:#000000;"><i class="fab fa-magento"></i>&nbsp; Chất liệu:</span></strong></td><td class="specval"><span id="pdp-material" style="font-size:90%;">Đồng mạ vàng, pha lê</span></td></tr>
                <tr><td class="specname"><strong><span style="color:#000000;"><i class="fas fa-circle-notch"></i>&nbsp; Kích thước:</span></strong></td><td class="specval"><span id="pdp-size" style="font-size:90%;">Liên hệ</span></td></tr>
                <tr><td class="specname"><strong><span style="color:#000000;"><i class="fas fa-globe"></i>&nbsp; Xuất xứ:</span></strong></td><td class="specval"><span id="pdp-origin" style="font-size:90%;">Châu Âu</span></td></tr>
                <tr><td class="specname"><strong><span style="color:#000000;">Giá:</span></strong></td><td class="specval"><span id="pdp-price2">Liên hệ</span></td></tr>
              </tbody></table>
              <p id="pdp-desc" class="text-xs font-bold uppercase tracking-widest"></p>
            </div>
            <form class="cart" onsubmit="return false;">
              <div class="quantity buttons_added">
                <input class="minus button is-form" type="button" value="-"/>
                <label class="screen-reader-text" for="pdp-qty">Số lượng</label>
                <input aria-label="Số lượng sản phẩm" autocomplete="off" class="input-text qty text" id="pdp-qty" inputmode="numeric" min="1" name="quantity" step="1" type="number" value="1"/>
                <input class="plus button is-form" type="button" value="+"/>
              </div>
              <button class="single_add_to_cart_button button alt" id="pdp-add" name="add-to-cart" type="button" data-product-id="">Thêm vào giỏ hàng</button>
            </form>
          </div>
        </div>
      </div>
      <div class="product-footer">
        <div class="container">
          <div class="woocommerce-tabs wc-tabs-wrapper container tabbed-content">
            <ul class="tabs wc-tabs product-tabs small-nav-collapse nav nav-uppercase nav-line-grow nav-center" role="tablist">
              <li class="description_tab active"><a href="#tab-description">Mô tả</a></li>
              <li class="additional_information_tab"><a href="#tab-additional_information">Thông tin bổ sung</a></li>
              <li class="reviews_tab"><a href="#tab-reviews">Đánh giá (0)</a></li>
            </ul>
            <div class="tab-panels">
              <div class="woocommerce-Tabs-panel woocommerce-Tabs-panel--description panel entry-content active" id="tab-description">
                <h2 id="pdp-desc-title">Mô tả sản phẩm</h2>
                <p id="pdp-desc-long" style="text-align:justify;"></p>
              </div>
              <div class="woocommerce-Tabs-panel woocommerce-Tabs-panel--additional_information panel entry-content" id="tab-additional_information">
                <table class="woocommerce-product-attributes shop_attributes">
                  <tr><th class="woocommerce-product-attributes-item__label">Bộ sưu tập</th><td class="woocommerce-product-attributes-item__value"><p id="pdp-attr-cat">—</p></td></tr>
                  <tr><th class="woocommerce-product-attributes-item__label">Chất liệu</th><td class="woocommerce-product-attributes-item__value"><p id="pdp-attr-material">—</p></td></tr>
                  <tr><th class="woocommerce-product-attributes-item__label">Xuất xứ</th><td class="woocommerce-product-attributes-item__value"><p id="pdp-attr-origin">—</p></td></tr>
                </table>
              </div>
              <div class="woocommerce-Tabs-panel woocommerce-Tabs-panel--reviews panel entry-content" id="tab-reviews">
                <div class="woocommerce-Reviews row" id="reviews"><div class="col large-12" id="comments"><h3 class="woocommerce-Reviews-title normal">Đánh giá</h3><p class="woocommerce-noreviews">Chưa có đánh giá nào.</p></div></div>
              </div>
            </div>
          </div>
          <div class="related related-products-wrapper product-section">
            <h3 class="product-section-title container-width product-section-title-related pt-half pb-half uppercase">Sản phẩm tương tự</h3>
            <div class="row equalize-box large-columns-4 medium-columns-3 small-columns-2 row-small" id="pdp-related"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
'''


def make_header_opaque(soup):
    hdr = soup.select_one('#header')
    if hdr:
        hdr['class'] = [c for c in (hdr.get('class') or []) if c not in ('transparent', 'has-transparent')]

def product_meta(p):
    if p['cat'] == 'baccarat':
        return ('Pha lê Baccarat, đồng mạ vàng 24K', 'Pháp / Ý', 'Ø 800 × H 700 mm (tham khảo)')
    if p['cat'] == 'serip':
        return ('Kim loại mạ vàng, pha lê nghệ thuật', 'Ý (Italy)', 'Ø 800 × H 700 mm (tham khảo)')
    return ('Đồng mạ vàng, pha lê Asfour', 'Tây Ban Nha / Ý', 'Ø 800 × H 700 mm (tham khảo)')

def render_product_html(p):
    soup = BeautifulSoup(PRODUCT_HTML, 'html.parser')
    # sidebar collections
    menu = soup.select_one('#product-sidebar .product-categories')
    if menu:
        menu.clear()
        for key, cfg in COLLECTIONS.items():
            li = soup.new_tag('li', **{'class': 'cat-item'})
            if key == p['cat']:
                li['class'] = ['cat-item', 'current-cat']
            a = soup.new_tag('a', href=cfg['file'])
            a['data-cat'] = key
            a.string = cfg['name']
            li.append(a)
            menu.append(li)

    home = soup.select_one('.woocommerce-breadcrumb a')
    if home:
        home['href'] = 'index.html'
    cat = soup.select_one('#pdp-cat-link')
    if cat:
        cat['href'] = '/' + p['catSlug'] + '/'
        cat.string = CATS[p['cat']]['name']

    material, origin, size = product_meta(p)
    title = p['name']
    price = fmt_price(p['price'])
    sku = 'CV-' + re.sub(r'[^a-z0-9]', '', p['id'].lower()).upper()

    img = soup.select_one('#pdp-img')
    if img:
        img['src'] = p['img']; img['alt'] = title
    thumb = soup.select_one('#pdp-thumb')
    if thumb:
        thumb['src'] = p['img']; thumb['alt'] = title
    img_link = soup.select_one('#pdp-img-link')
    if img_link:
        img_link['href'] = p['img']
    for sel, val in [
        ('#pdp-title', title), ('#pdp-price', price), ('#pdp-price2', price),
        ('#pdp-sku', sku), ('#pdp-material', material), ('#pdp-size', size),
        ('#pdp-origin', origin), ('#pdp-desc', p['desc']),
        ('#pdp-desc-title', title.upper() + ' – BIỂU TƯỢNG SANG TRỌNG'),
        ('#pdp-desc-long', p['desc'] + ' Sản phẩm được nhập khẩu chính hãng, bảo hành 24 tháng và được đội ngũ Cavani tư vấn lắp đặt tận nơi.'),
        ('#pdp-attr-cat', CATS[p['cat']]['name']), ('#pdp-attr-material', material),
        ('#pdp-attr-origin', origin),
    ]:
        el = soup.select_one(sel)
        if el:
            el.string = val
    add = soup.select_one('#pdp-add')
    if add:
        add['data-product-id'] = p['id']
    prod = soup.select_one('#product-1')
    if prod:
        prod['id'] = 'product-' + p['id']

    rel = soup.select_one('#pdp-related')
    if rel:
        related = [x for x in PRODUCTS if x['cat'] == p['cat'] and x['id'] != p['id']][:4]
        for r in related:
            rel.append(BeautifulSoup(product_card(r), 'html.parser'))
    return soup

def build_products():
    for p in PRODUCTS:
        soup = BeautifulSoup(open('/tmp/cat.html', encoding='utf-8').read(), 'html.parser')
        strip_unwanted(soup)
        localize(soup)
        rewrite_internal_links(soup)
        fix_nav(soup)
        make_header_opaque(soup)
        pt = soup.select_one('.shop-page-title')
        if pt:
            pt.decompose()
        main = soup.find('main', id='main')
        if main:
            main.clear()
            main['class'] = ['shop-container']
            main.append(render_product_html(p))
        if soup.body:
            keep = [c for c in (soup.body.get('class') or [])
                    if c not in ('archive', 'tax-product_cat', 'woocommerce-page', 'cavani-cat')
                    and not c.startswith('term-')]
            soup.body['class'] = keep + ['single-product', 'woocommerce']
            soup.body['data-product-id'] = p['id']
        write_doc(soup, p['path'], p['name'] + ' | Cavani Lighting')


# ---------------------------------------------------------------- cart page
CART_HTML = r'''
<div class="shop-container">
  <div class="container"><div class="woocommerce-notices-wrapper"></div></div>
  <div class="cart-container container page-wrapper page-checkout" id="cart-page">
    <div class="row">
      <div class="col large-12">
        <div class="woocommerce">
          <div class="woocommerce-cart-form">
            <h1 class="entry-title">Giỏ hàng của bạn</h1>
            <div id="cart-empty" class="cart-empty woocommerce-info" style="display:none">
              Chưa có sản phẩm trong giỏ hàng. <a href="index.html">Quay lại cửa hàng</a>
            </div>
            <div id="cart-filled" style="display:none">
              <table class="shop_table shop_table_responsive cart woocommerce-cart-form__contents">
                <thead><tr>
                  <th class="product-remove">&nbsp;</th><th class="product-thumbnail">&nbsp;</th>
                  <th class="product-name">Sản phẩm</th><th class="product-price">Giá</th>
                  <th class="product-quantity">Số lượng</th><th class="product-subtotal">Tạm tính</th>
                </tr></thead>
                <tbody id="cart-items"></tbody>
              </table>
              <div class="cart-actions"><a href="index.html" class="button secondary">Tiếp tục mua sắm</a></div>
            </div>
          </div>
          <div class="cart-collaterals">
            <div class="cart_totals">
              <h2>Tổng giỏ hàng</h2>
              <table>
                <tr><th>Tạm tính</th><td id="cart-subtotal">0₫</td></tr>
                <tr><th>Tổng</th><td id="cart-total">0₫</td></tr>
              </table>
              <a href="#" id="cart-checkout" class="checkout-button button alt wc-forward">Tiến hành thanh toán</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
'''

def build_cart():
    soup = BeautifulSoup(open('/tmp/cat.html', encoding='utf-8').read(), 'html.parser')
    strip_unwanted(soup); localize(soup); rewrite_internal_links(soup); fix_nav(soup)
    make_header_opaque(soup)
    pt = soup.select_one('.shop-page-title')
    if pt: pt.decompose()
    main = soup.find('main', id='main')
    if main:
        main.clear(); main['class'] = ['shop-container']
        main.append(BeautifulSoup(CART_HTML, 'html.parser'))
    if soup.body:
        soup.body['class'] = [c for c in (soup.body.get('class') or []) if not c.startswith('term-')]
        soup.body['class'] += ['woocommerce-cart']
    write_doc(soup, 'cart.html', 'Giỏ hàng | Cavani Lighting')


# ---------------------------------------------------------------- content pages
def build_live_content(filename, title, live_path, remove_selectors=()):
    """Rebuild a content page from the captured live page so the section
    structure, spacing and inline styles match cavani.vn exactly."""
    soup = BeautifulSoup(open('/tmp/cat.html', encoding='utf-8').read(), 'html.parser')
    strip_unwanted(soup); localize(soup); rewrite_internal_links(soup); fix_nav(soup)
    make_header_opaque(soup)
    pt = soup.select_one('.shop-page-title')
    if pt: pt.decompose()

    live = BeautifulSoup(open(live_path, encoding='utf-8').read(), 'html.parser')
    strip_unwanted(live); localize(live); rewrite_internal_links(live); fix_lazy_images(live)
    for sel in remove_selectors:
        for el in live.select(sel):
            el.decompose()

    src_main = live.find('main', id='main')
    content = src_main.find(id='content') if src_main else None
    if content is None and src_main:
        content = src_main.find(recursive=False)

    main = soup.find('main', id='main')
    if main:
        main.clear()
        main['class'] = []
        if content is not None:
            main.append(copy.deepcopy(content))
    if soup.body and live.body:
        soup.body['class'] = [c for c in (live.body.get('class') or []) if c != 'woocommerce-js']
    write_doc(soup, filename, title)


def build_content_pages():
    build_live_content(
        've-chung-toi.html',
        'Showroom Cavani - Nhà phân phối các mẫu đèn trang trí Châu Âu',
        '/tmp/live-ve-chung-toi.html')
    build_live_content(
        'lien-he.html',
        'LIÊN HỆ - Cavani.vn - Đèn Trang Trí Cao Cấp Châu Âu',
        '/tmp/live-lien-he.html')
    build_live_content(
        'du-an-tieu-bieu.html',
        'DỰ ÁN TIÊU BIỂU - Cavani.vn - Đèn Trang Trí Cao Cấp Châu Âu',
        '/tmp/live-du-an-tieu-bieu.html')
    build_live_content(
        'category/tin-tuc-cavani.html',
        'Tin tức đèn chùm cao cấp Châu Âu Cavani | Xu hướng & tư vấn',
        '/tmp/live-category-tin-tuc-cavani.html')
    build_live_content(
        'thanh-toan-va-bao-hanh.html',
        'THANH TOÁN VÀ BẢO HÀNH - Cavani.vn - Đèn Trang Trí Cao Cấp Châu Âu',
        '/tmp/live-thanh-toan-va-bao-hanh.html')
    build_live_content(
        'thiet-ke-den-trang-tri.html',
        'THIẾT KẾ ĐÈN TRANG TRÍ - Cavani.vn - Đèn Trang Trí Cao Cấp Châu Âu',
        '/tmp/live-thiet-ke-den-trang-tri.html',
        remove_selectors=('#row-537308071',))
    build_live_content(
        'thiet-ke-chieu-sang.html',
        'THIẾT KẾ CHIẾU SÁNG - Cavani.vn - Đèn Trang Trí Cao Cấp Châu Âu',
        '/tmp/live-thiet-ke-chieu-sang.html')
    build_live_content(
        'thiet-ke-doc-ban.html',
        'THIẾT KẾ ĐỘC BẢN - Cavani.vn - Đèn Trang Trí Cao Cấp Châu Âu',
        '/tmp/live-thiet-ke-doc-ban.html')
LEGACY_PAGES = [
    'serip-lighting.html', 'baccarat-lighting.html', 'den-tan-co-dien.html',
    'product.html', 'cart.html', 'about.html', 'contact.html',
    'projects.html', 'news.html', 'services.html',
]

LEGACY_DIRS = [
    'product', 'about', 'contact', 'projects', 'news', 'services',
    'serip-lighting', 'baccarat-lighting', 'den-tan-co-dien',
]

def cleanup_legacy_pages():
    for name in LEGACY_PAGES:
        if os.path.exists(name):
            os.remove(name)
            print('removed legacy', name)
    for name in LEGACY_DIRS:
        if os.path.isdir(name):
            shutil.rmtree(name)
            print('removed legacy dir', name)

if __name__ == '__main__':
    prepare_products()
    build_home()
    for _cat in CATS:
        build_category(_cat)
    build_products()
    build_cart()
    build_content_pages()
    cleanup_legacy_pages()
