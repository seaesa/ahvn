import os, json, re, urllib.request, concurrent.futures, hashlib
from bs4 import BeautifulSoup

UA={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36'}
SRC=[('/tmp/cat.html','tan-co-dien','Đèn Tân Cổ Điển'),
     ('/tmp/den-chum-hien-dai_.html','serip','SERIP Lighting'),
     ('/tmp/den-chum-pha-le_.html','baccarat','Baccarat Lighting')]

def dl(url,dest):
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest)>1000: return os.path.getsize(dest)
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=90) as r, open(dest,'wb') as f: f.write(r.read())
    return os.path.getsize(dest)

products=[]; jobs={}
for path,cat,catname in SRC:
    soup=BeautifulSoup(open(path,encoding='utf-8').read(),'lxml')
    seen=set()
    for p in soup.select('.product-small'):
        t=p.select_one('.product-title')
        if not t: continue
        name=t.get_text(' ',strip=True)
        if name in seen: continue
        seen.add(name)
        img=p.select_one('img')
        if not img: continue
        src=img.get('data-src') or img.get('src') or ''
        if not src.startswith('http'): continue
        base=src.split('/')[-1].split('?')[0]
        dest=f'assets/img/products/{base}'
        jobs[src]=dest
        pid=f'{cat}-{len(products)+1}'
        products.append({'id':pid,'name':name,'cat':cat,'catName':catname,'img':f'assets/img/products/{base}','price':0,'desc':''})
print('products',len(products),'images',len(jobs))
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    futs={ex.submit(dl,u,d):(u,d) for u,d in jobs.items()}
    for f in concurrent.futures.as_completed(futs):
        u,d=futs[f]
        try: print(f.result(),d)
        except Exception as e: print('ERR',u,e)

# deterministic demo prices (VND)
import random
random.seed(42)
for p in products:
    p['price']=random.choice([8900000,12500000,15900000,18500000,22900000,27500000,32900000,38500000,45900000,52900000])
    p['desc']=f"{p['name']} – tuyệt tác ánh sáng nhập khẩu Châu Âu, chế tác thủ công từ đồng mạ vàng và pha lê cao cấp. Thiết kế {('hiện đại, phóng khoáng' if p['cat']=='serip' else 'pha lê lấp lánh sang trọng' if p['cat']=='baccarat' else 'cổ điển, tân cổ điển quý phái')}, phù hợp biệt thự, penthouse và không gian sang trọng."
json.dump(products,open('data/products.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('saved data/products.json')
