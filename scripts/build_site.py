#!/usr/bin/env python3
"""Build the static Cavani clone from captured research artifacts."""
import json, os, re, copy
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
    # fl-icons @font-face
    for st_tag in soup.find_all('style'):
        if st_tag.string and 'fl-icons' in st_tag.string:
            st_tag.string = re.sub(r'https?://cavani\.vn/wp-content/themes/flatsome/assets/css/icons/fl-icons\.(woff2|woff|ttf|eot|svg)(\?v=[^)\s]*)?',
                                   lambda m: 'assets/fonts/fl-icons.' + m.group(1), st_tag.string)

def rewrite_internal_links(soup):
    mapping = {
        r'^https?://cavani\.vn/?$': 'index.html',
        r'^https?://cavani\.vn/den-trang-tri/?$': 'den-tan-co-dien.html',
        r'^https?://cavani\.vn/den-chum-co-dien/?$': 'den-tan-co-dien.html',
        r'^https?://cavani\.vn/danh-muc-san-pham/den-chum/den-chum-co-dien/?$': 'den-tan-co-dien.html',
        r'^https?://cavani\.vn/den-chum-pha-le/?$': 'baccarat-lighting.html',
        r'^https?://cavani\.vn/danh-muc-san-pham/den-chum/den-chum-pha-le/?$': 'baccarat-lighting.html',
        r'^https?://cavani\.vn/den-chum-hien-dai/?$': 'serip-lighting.html',
        r'^https?://cavani\.vn/danh-muc-san-pham/den-chum/den-chum-hien-dai/?$': 'serip-lighting.html',
        r'^https?://cavani\.vn/cart/?$': 'cart.html',
        r'^https?://cavani\.vn/lien-he/?$': 'contact.html',
        r'^https?://cavani\.vn/ve-chung-toi/?$': 'about.html',
        r'^https?://cavani\.vn/du-an-tieu-bieu/?$': 'projects.html',
        r'^https?://cavani\.vn/thiet-ke-den-trang-tri/?$': 'services.html',
        r'^https?://cavani\.vn/thiet-ke-chieu-sang/?$': 'services.html',
        r'^https?://cavani\.vn/thiet-ke-doc-ban/?$': 'services.html',
        r'^https?://cavani\.vn/category/tin-tuc-cavani/?$': 'news.html',
        r'^https?://cavani\.vn/thanh-toan-va-bao-hanh/?$': 'news.html',
        r'^https?://cavani\.vn/den-chieu-sang/?$': 'serip-lighting.html',
        r'^https?://cavani\.vn/luxury-decor/?$': 'baccarat-lighting.html',
    }
    for a in soup.find_all('a', href=True):
        h = a['href']
        done = False
        for pat, dest in mapping.items():
            if re.match(pat, h):
                a['href'] = dest
                done = True
                break
        if done:
            continue
        if h.startswith('https://cavani.vn/'):
            if '/video/' in h or '/du-an' in h:
                a['href'] = 'projects.html'
            elif '/den-chum' in h or '/den-trang-tri' in h:
                a['href'] = 'den-tan-co-dien.html'
            elif h.rstrip('/').split('/')[-1] in ('den-chum-chau-au-cao-cap',):
                a['href'] = 'news.html'
            elif h.count('/') >= 5:
                a['href'] = 'news.html'
            else:
                a['href'] = '#'

def fix_nav(soup):
    """Rewrite the main menu and mobile menu to the three requested collections."""
    # Desktop + mobile share menu item ids; update every SẢN PHẨM submenu.
    for li in soup.select('li.menu-item-has-children'):
        a = li.find('a', recursive=False)
        if not a:
            continue
        label = a.get_text(' ', strip=True).upper()
        sub = li.find('ul', class_='sub-menu')
        if not sub:
            continue
        if 'SẢN PHẨM' in label:
            for i, child in enumerate(sub.find_all('li', recursive=False)):
                ca = child.find('a')
                if not ca:
                    continue
                if i == 0:
                    ca['href'] = 'serip-lighting.html'; ca.string = 'SERIP LIGHTING'
                elif i == 1:
                    ca['href'] = 'baccarat-lighting.html'; ca.string = 'BACCARAT LIGHTING'
                elif i == 2:
                    ca['href'] = 'den-tan-co-dien.html'; ca.string = 'ĐÈN TÂN CỔ ĐIỂN'
            a['href'] = 'serip-lighting.html'
        elif 'DỊCH VỤ' in label:
            a['href'] = 'services.html'
            for child in sub.find_all('li', recursive=False):
                ca = child.find('a')
                if ca: ca['href'] = 'services.html'
        elif 'TIN TỨC' in label:
            a['href'] = 'news.html'
            for child in sub.find_all('li', recursive=False):
                ca = child.find('a')
                if not ca: continue
                if 'VỀ CHÚNG TÔI' in ca.get_text(' ', strip=True).upper():
                    ca['href'] = 'about.html'
                else:
                    ca['href'] = 'news.html'
    # Flatsome injects the submenu toggle at runtime; captured DOM already has it -> drop all
    for btn in soup.select('#main-menu button.toggle'):
        btn.decompose()

def fix_home_content(soup):
    # Keep original section ID: inline CSS is keyed to #section_1088443042.

    cards = soup.select('#section_1784693606 .col.codien')
    if len(cards) >= 3:
        data = [
            ('assets/img/Den-chum-hien-dai-Chau-Au-sang-trong-2-scaled.jpg', 'SERIP Lighting', 'serip-lighting.html', 'SERIP LIGHTING'),
            ('assets/img/phale.jpg', 'Baccarat Lighting', 'baccarat-lighting.html', 'BACCARAT LIGHTING'),
            ('assets/img/codien4.jpg', 'Đèn Tân Cổ Điển', 'den-tan-co-dien.html', 'ĐÈN TÂN CỔ ĐIỂN'),
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
            if a['href'].startswith('https://cavani.vn/'):
                a['href'] = 'den-tan-co-dien.html'

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

LINK_HTML_RE = re.compile(r'^(?:\./)?([a-z0-9][a-z0-9-]*)\.html((?:\?[^#]*)?(?:#.*)?)$')

def clean_urls(soup, prefix=''):
    """Turn flat *.html links into directory URLs and rebase local assets."""
    for a in soup.find_all('a', href=True):
        h = a['href']
        if not h or h.startswith(('http://', 'https://', '//', 'mailto:', 'tel:', 'javascript:', '#')):
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
        'Đèn tường Châu Âu': 'serip-lighting.html',
        'Đèn bàn Châu Âu': 'baccarat-lighting.html',
        'Đèn ốp Châu Âu': 'serip-lighting.html',
    }
    for a in soup.find_all('a', href='#'):
        t = a.get_text(' ', strip=True)
        if a.find_parent(class_='blog-post') or a.find_parent(class_='image-cover'):
            a['href'] = 'news.html'
        elif t == 'Possoni – Ý':
            a['href'] = 'about.html'
        elif t in footer_map:
            a['href'] = footer_map[t]
        elif t == 'Đăng nhập':
            a['href'] = 'contact.html'
    for img in soup.find_all('img'):
        src = img.get('src') or ''
        if 'nguyenhung.net' in src:
            img['src'] = 'assets/img/icon-call-nh.png'

def page_output(path):
    if path == 'index.html':
        return path
    slug = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(slug, 'index.html')

def write_doc(soup, path, title):
    prefix = '' if path == 'index.html' else '../'
    fix_content_links(soup)
    fix_lazy_images(soup)
    build_head(soup, title)
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
    out_path = page_output(path)
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
    # cart link text + count
    for a in soup.select('a.header-cart-link'):
        a['href'] = 'cart.html'
    # remove login popup (no backend)
    lp = soup.select_one('#login-form-popup')
    if lp: lp.decompose()
    write_doc(soup, 'index.html', 'Đèn trang trí Châu Âu cao cấp | Cavani Lighting')


# ---------------------------------------------------------------- category pages
CATS = {
    'serip': {
        'file': 'serip-lighting.html',
        'title': 'SERIP LIGHTING – Đèn nghệ thuật Ý cao cấp | Cavani Lighting',
        'name': 'SERIP LIGHTING',
        'h1': 'SERIP LIGHTING – NGHỆ THUẬT ÁNH SÁNG Ý',
        'intro': [
            'SERIP Lighting là thương hiệu đèn nghệ thuật đến từ Ý, nổi tiếng với những thiết kế điêu khắc ánh sáng lấy cảm hứng từ thiên nhiên, hoa lá và chuyển động. Mỗi tác phẩm là sự kết hợp tinh xảo giữa kim loại mạ vàng, pha lê và kỹ thuật chế tác thủ công của các nghệ nhân Ý.',
            'Tại Cavani, bộ sưu tập SERIP Lighting mang đến giải pháp ánh sáng độc bản cho biệt thự, penthouse, khách sạn và không gian nghệ thuật – nơi mỗi chiếc đèn không chỉ chiếu sáng mà còn là một tác phẩm điêu khắc.',
        ],
        'desc': 'SERIP Lighting – kiệt tác đèn nghệ thuật Ý, thiết kế độc bản, chế tác thủ công cho không gian thượng lưu.',
    },
    'baccarat': {
        'file': 'baccarat-lighting.html',
        'title': 'BACCARAT LIGHTING – Đèn chùm pha lê cao cấp | Cavani Lighting',
        'name': 'BACCARAT LIGHTING',
        'h1': 'BACCARAT LIGHTING – PHA LÊ CAO CẤP',
        'intro': [
            'BACCARAT Lighting là biểu tượng của sự xa hoa với những chiếc đèn chùm pha lê được chế tác tỉ mỉ, mang vẻ đẹp lấp lánh và đẳng cấp vượt thời gian. Từng viên pha lê được cắt gọt nhiều mặt, tán xạ ánh sáng thành những tia sáng tinh tế khắp không gian.',
            'Bộ sưu tập BACCARAT Lighting tại Cavani dành cho những không gian cần sự sang trọng tuyệt đối: sảnh biệt thự, phòng khách lớn, phòng tiệc, khách sạn 5 sao và showroom cao cấp.',
        ],
        'desc': 'BACCARAT Lighting – đèn chùm pha lê cao cấp, lấp lánh và đẳng cấp cho không gian xa hoa.',
    },
    'tan-co-dien': {
        'file': 'den-tan-co-dien.html',
        'title': 'Đèn Tân Cổ Điển cao cấp | Cavani Lighting',
        'name': 'ĐÈN TÂN CỔ ĐIỂN',
        'h1': 'ĐÈN TÂN CỔ ĐIỂN CAO CẤP',
        'intro': [
            'Đèn Tân Cổ Điển là sự giao thoa hoàn hảo giữa nét cổ điển sang trọng và tinh thần hiện đại. Những đường nét uốn lượn, chất liệu đồng mạ vàng, pha lê và thủy tinh màu tạo nên vẻ đẹp quý phái nhưng vẫn phù hợp với kiến trúc đương đại.',
            'Bộ sưu tập Đèn Tân Cổ Điển của Cavani được tuyển chọn từ các thương hiệu Possoni, BC Sanmichele, Stillux – Ý và Copenlamp – Tây Ban Nha, mang đến giải pháp hoàn thiện cho biệt thự, dinh thự và không gian nội thất cao cấp.',
        ],
        'desc': 'Đèn Tân Cổ Điển cao cấp – sự giao thoa giữa nét cổ điển sang trọng và tinh thần hiện đại.',
    },
}

def fmt_price(n):
    return f"{int(n):,}".replace(',', '.') + '₫'

def product_card(p):
    pid = p['id']
    href = f"product.html?id={pid}"
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
    import json
    cfg = CATS[cat_key]
    products = [p for p in json.load(open('data/products.json', encoding='utf-8')) if p['cat'] == cat_key]
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

def build_product():
    soup = BeautifulSoup(open('/tmp/cat.html', encoding='utf-8').read(), 'html.parser')
    strip_unwanted(soup)
    localize(soup)
    rewrite_internal_links(soup)
    fix_nav(soup)
    make_header_opaque(soup)
    # remove category page title
    pt = soup.select_one('.shop-page-title')
    if pt: pt.decompose()
    main = soup.find('main', id='main')
    if main:
        main.clear()
        main['class'] = ['shop-container']
        main.append(BeautifulSoup(PRODUCT_HTML, 'html.parser'))
    if soup.body:
        soup.body['class'] = [c for c in (soup.body.get('class') or []) if not c.startswith('term-')]
        soup.body['class'] += ['single-product', 'woocommerce']
    write_doc(soup, 'product.html', 'Sản phẩm | Cavani Lighting')


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
def build_content(filename, title, h1, subtitle, body_html, body_class=''):
    soup = BeautifulSoup(open('/tmp/cat.html', encoding='utf-8').read(), 'html.parser')
    strip_unwanted(soup); localize(soup); rewrite_internal_links(soup); fix_nav(soup)
    make_header_opaque(soup)
    pt = soup.select_one('.shop-page-title')
    if pt: pt.decompose()
    main = soup.find('main', id='main')
    if main:
        main.clear(); main['class'] = ['shop-container']
        main.append(BeautifulSoup(
            '<div class="cavani-page"><div class="container">'
            '<div class="page-hero"><div class="subtitle">' + subtitle + '</div><h1>' + h1 + '</h1></div>'
            + body_html + '</div></div>', 'html.parser'))
    if soup.body:
        soup.body['class'] = [c for c in (soup.body.get('class') or []) if not c.startswith('term-')]
        if body_class: soup.body['class'] += [body_class]
    write_doc(soup, filename, title)

def build_content_pages():
    build_content('about.html', 'Về chúng tôi | Cavani Lighting', 'VỀ CHÚNG TÔI', 'CAVANI LIGHTING',
        '<div class="two-col">'
        '<img class="content-img" src="assets/img/POSSONI-173-1400x625.jpg" alt="Showroom Cavani"/>'
        '<div><h2>SHOWROOM CAVANI</h2>'
        '<p class="lead">Cavani là thương hiệu đèn trang trí Châu Âu cao cấp, mang đến không gian sống đẳng cấp với những tuyệt tác ánh sáng từ Ý, Tây Ban Nha và Pháp.</p>'
        '<p>Chúng tôi tuyển chọn và nhập khẩu chính hãng các bộ sưu tập đèn chùm, đèn tường, đèn bàn, đèn ốp và đồ bày trí từ Possoni, BC Sanmichele, Copenlamp, Lumistar, Stillux. Mỗi sản phẩm là sự kết hợp giữa kỹ thuật chế tác thủ công, chất liệu cao cấp và gu thẩm mỹ tinh tế.</p>'
        '<p>Với showroom tại Hà Nội và TP. Hồ Chí Minh, Cavani đồng hành cùng kiến trúc sư, chủ đầu tư và gia chủ trong việc kiến tạo những không gian sống sang trọng, tinh tế và giàu cảm xúc.</p>'
        '<a class="btn-dark" href="contact.html">Liên hệ tư vấn</a></div></div>'
        '<h2>Thương hiệu đồng hành</h2><div class="three-col">'
        '<div class="info-card"><h3>Possoni – Ý</h3><p>Đèn chùm cổ điển, tân cổ điển chế tác thủ công từ đồng mạ vàng và pha lê.</p></div>'
        '<div class="info-card"><h3>BC Sanmichele – Ý</h3><p>Đèn nghệ thuật độc bản, kết hợp kim loại và pha lê Murano.</p></div>'
        '<div class="info-card"><h3>Copenlamp – Tây Ban Nha</h3><p>Đèn trang trí sang trọng cho biệt thự, khách sạn và dinh thự.</p></div>'
        '<div class="info-card"><h3>Lumistar – Tây Ban Nha</h3><p>Giải pháp chiếu sáng cao cấp, tinh tế và hiện đại.</p></div>'
        '<div class="info-card"><h3>Stillux – Ý</h3><p>Đèn thiết kế đương đại, dấu ấn nghệ thuật trong từng chi tiết.</p></div>'
        '<div class="info-card"><h3>Cavani</h3><p>Đơn vị tư vấn, thiết kế và thi công giải pháp ánh sáng trọn gói.</p></div>'
        '</div>')

    build_content('contact.html', 'Liên hệ | Cavani Lighting', 'LIÊN HỆ', 'CAVANI LIGHTING',
        '<div class="contact-grid">'
        '<div><h2>Showroom Hà Nội</h2><p>160 Thái Hà, Đống Đa, Hà Nội</p><p>Hotline: 0937.6688.34</p>'
        '<h2>Showroom TP. Hồ Chí Minh</h2><p>42 Nguyễn Cơ Thạch, Khu Sala, TP. HCM</p><p>Hotline: 0937.6688.34</p>'
        '<h2>Fanpage</h2><p>Cavani Lighting</p><p>Website: www.cavani.vn</p></div>'
        '<div><h2>Gửi yêu cầu tư vấn</h2><form class="contact-form" onsubmit="event.preventDefault(); this.querySelector(\'button\').textContent=\'Đã gửi yêu cầu\'; this.reset();">'
        '<input type="text" placeholder="Họ và tên" required/>'
        '<input type="email" placeholder="Email" required/>'
        '<input type="tel" placeholder="Số điện thoại"/>'
        '<textarea placeholder="Nội dung cần tư vấn"></textarea>'
        '<button type="submit">Gửi yêu cầu</button></form></div></div>')

    build_content('projects.html', 'Dự án tiêu biểu | Cavani Lighting', 'DỰ ÁN TIÊU BIỂU', 'CAVANI LIGHTING',
        '<p class="lead" style="text-align:center;max-width:760px;margin:0 auto 34px;">Mỗi công trình là một câu chuyện ánh sáng riêng – nơi Cavani đồng hành cùng kiến trúc sư và chủ đầu tư để kiến tạo không gian sống đẳng cấp.</p>'
        '<div class="project-grid">'
        '<a class="project-card" href="projects.html"><img src="assets/img/z4437276384749_7c9ecad410ebf3242be1b05d5f70edf9.jpg" alt="Dự án biệt thự"/><div class="caption">Biệt thự tân cổ điển – Hà Nội</div></a>'
        '<a class="project-card" href="projects.html"><img src="assets/img/Du-an-den-bespoke-nghe-thuat-anh-dai-dien-scaled.jpg" alt="Dự án bespoke"/><div class="caption">Đèn bespoke nghệ thuật</div></a>'
        '<a class="project-card" href="projects.html"><img src="assets/img/CONG-TRINH-CHI-HIEP-2-scaled.jpg" alt="Công trình chị Hiệp"/><div class="caption">Công trình chị Hiệp</div></a>'
        '<a class="project-card" href="projects.html"><img src="assets/img/CL1-scaled.jpg" alt="Dự án CL1"/><div class="caption">Biệt thự CL1</div></a>'
        '<a class="project-card" href="projects.html"><img src="assets/img/CONG-TRINH-ANH-TOAN-1-scaled.jpg" alt="Công trình anh Toàn"/><div class="caption">Công trình anh Toàn</div></a>'
        '<a class="project-card" href="projects.html"><img src="assets/img/CONG-TRINH-CHI-NGUYET0-scaled.jpg" alt="Công trình chị Nguyệt"/><div class="caption">Công trình chị Nguyệt</div></a>'
        '</div>')

    build_content('news.html', 'Tin tức | Cavani Lighting', 'TIN TỨC', 'CẨM NANG ÁNH SÁNG',
        '<p class="lead" style="text-align:center;max-width:760px;margin:0 auto 34px;">Cẩm nang đèn chùm Châu Âu – kiến thức, xu hướng và kinh nghiệm chọn đèn cho không gian sống thượng lưu.</p>'
        '<div class="news-grid">'
        '<a class="news-card" href="news.html"><img src="assets/img/Den-chum-co-dien-Possoni-096-12-6-3-662x400.jpg" alt="Đèn chùm cổ điển Possoni"/><h3>Đèn chùm cổ điển Possoni – biểu tượng của sự sang trọng</h3><p>Khám phá vẻ đẹp vượt thời gian của đèn chùm Possoni trong không gian biệt thự.</p></a>'
        '<a class="news-card" href="news.html"><img src="assets/img/211-618x400.jpg" alt="Đèn chùm pha lê"/><h3>Bí quyết chọn đèn chùm pha lê cho phòng khách</h3><p>Kích thước, chất liệu và ánh sáng – ba yếu tố quyết định vẻ đẹp của đèn chùm.</p></a>'
        '<a class="news-card" href="news.html"><img src="assets/img/PHUONG-AN-DEN-TRANG-TRI-MRS-CHI-BAC-GIANG-4-566x400.jpg" alt="Phương án đèn trang trí"/><h3>Phương án đèn trang trí cho không gian tân cổ điển</h3><p>Gợi ý bố trí ánh sáng cho biệt thự và dinh thự theo phong cách Châu Âu.</p></a>'
        '<a class="news-card" href="news.html"><img src="assets/img/THE-NAO-LA-DEN-CHUM-CAO-CAP-scaled.jpg" alt="Đèn chùm cao cấp"/><h3>Thế nào là một chiếc đèn chùm cao cấp?</h3><p>Phân biệt đèn chùm cao cấp và đèn trang trí thông thường qua chất liệu, chế tác.</p></a>'
        '<a class="news-card" href="news.html"><img src="assets/img/Thuong-hieu-den-trang-tri-cao-cap-Y-Stillux-3.jpg" alt="Stillux"/><h3>Stillux – dấu ấn đèn thiết kế Ý</h3><p>Thương hiệu đèn nghệ thuật được các kiến trúc sư hàng đầu lựa chọn.</p></a>'
        '<a class="news-card" href="news.html"><img src="assets/img/BC-Sanmichele-Den-trang-tri-nghe-thuat-doc-ban.jpg" alt="BC Sanmichele"/><h3>BC Sanmichele – nghệ thuật độc bản</h3><p>Những tác phẩm đèn thủ công mang đậm tinh thần nghệ thuật nước Ý.</p></a>'
        '</div>')

    build_content('services.html', 'Dịch vụ | Cavani Lighting', 'DỊCH VỤ', 'CAVANI LIGHTING',
        '<div class="three-col">'
        '<div class="info-card"><h3>Thiết kế đèn trang trí</h3><p>Tư vấn và thiết kế giải pháp đèn trang trí phù hợp kiến trúc, phong cách và công năng từng không gian.</p><a class="btn-dark" href="contact.html">Tư vấn</a></div>'
        '<div class="info-card"><h3>Thiết kế chiếu sáng</h3><p>Quy hoạch ánh sáng tổng thể cho biệt thự, khách sạn, showroom với tiêu chuẩn Châu Âu.</p><a class="btn-dark" href="contact.html">Tư vấn</a></div>'
        '<div class="info-card"><h3>Thiết kế độc bản</h3><p>Chế tác đèn bespoke theo yêu cầu, cá nhân hóa từ chất liệu, kích thước đến chi tiết hoàn thiện.</p><a class="btn-dark" href="contact.html">Tư vấn</a></div>'
        '</div>'
        '<div class="two-col" style="margin-top:40px;">'
        '<img class="content-img" src="assets/img/kts5.jpg" alt="Không gian đèn Cavani"/>'
        '<div><h2>Giải pháp ánh sáng trọn gói</h2><p>Từ khảo sát, tư vấn, thiết kế đến thi công và bảo hành – Cavani mang đến quy trình chuyên nghiệp, đồng bộ cho mọi công trình.</p>'
        '<p>Đội ngũ chuyên gia của chúng tôi làm việc trực tiếp với kiến trúc sư, nhà thầu và gia chủ để đảm bảo từng chi tiết ánh sáng hài hòa với tổng thể kiến trúc.</p>'
        '<a class="btn-dark" href="contact.html">Đặt lịch tư vấn</a></div></div>')

LEGACY_PAGES = [
    'serip-lighting.html', 'baccarat-lighting.html', 'den-tan-co-dien.html',
    'product.html', 'cart.html', 'about.html', 'contact.html',
    'projects.html', 'news.html', 'services.html',
]

def cleanup_legacy_pages():
    for name in LEGACY_PAGES:
        if os.path.exists(name):
            os.remove(name)
            print('removed legacy', name)

if __name__ == '__main__':
    build_home()
    for _cat in CATS:
        build_category(_cat)
    build_product()
    build_cart()
    build_content_pages()
    cleanup_legacy_pages()
