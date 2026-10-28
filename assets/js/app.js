/* Cavani clone – front-end behaviour */
(function () {
  'use strict';
  var BASE = window.CAVANI_BASE || '';
  var HOME = BASE || './';
  var PRODUCTS = window.CAVANI_PRODUCTS || [];
  var CART_KEY = 'cavani_cart_v1';
  var CAT_FILE = {
    'serip': BASE + 'den-chum-hien-dai/',
    'baccarat': BASE + 'den-chum-pha-le/',
    'tan-co-dien': BASE + 'den-chum-co-dien/'
  };
  function asset(u) {
    return /^(?:[a-z]+:|\/\/|\/|#)/i.test(u) ? u : BASE + u;
  }
  function productHref(p) {
    if (p && p.url) return BASE + String(p.url).replace(/^\/+/, '');
    return BASE + 'den-trang-tri/';
  }
  var CAT_LABEL = {
    'serip': 'SERIP LIGHTING',
    'baccarat': 'BACCARAT LIGHTING',
    'tan-co-dien': 'ĐÈN TÂN CỔ ĐIỂN'
  };

  function money(n) {
    return Number(n).toLocaleString('vi-VN') + '₫';
  }
  function getCart() {
    try { return JSON.parse(localStorage.getItem(CART_KEY)) || {}; } catch (e) { return {}; }
  }
  function saveCart(c) { localStorage.setItem(CART_KEY, JSON.stringify(c)); renderCartCount(); renderMiniCart(); renderCartPage(); }
  function cartCount() { var c = getCart(); return Object.keys(c).reduce(function (s, k) { return s + c[k]; }, 0); }
  function cartTotal() {
    var c = getCart(), t = 0;
    Object.keys(c).forEach(function (id) {
      var p = findProduct(id);
      if (p) t += p.price * c[id];
    });
    return t;
  }
  function findProduct(id) {
    for (var i = 0; i < PRODUCTS.length; i++) if (PRODUCTS[i].id === id) return PRODUCTS[i];
    return null;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function renderCartCount() {
    var n = cartCount(), total = cartTotal();
    document.querySelectorAll('.header-cart-link .cart-icon strong').forEach(function (el) { el.textContent = n; });
    document.querySelectorAll('.header-cart-link .cart-price').forEach(function (el) {
      el.innerHTML = '<span class="woocommerce-Price-amount amount"><bdi>' + money(total) + '</bdi></span>';
    });
  }

  function renderMiniCart() {
    var cart = getCart(), ids = Object.keys(cart);
    document.querySelectorAll('.widget_shopping_cart_content').forEach(function (el) {
      if (!ids.length) {
        el.innerHTML = '<p class="woocommerce-mini-cart__empty-message">Chưa có sản phẩm trong giỏ hàng.</p>';
        return;
      }
      var html = '<ul class="woocommerce-mini-cart cart_list product_list_widget">';
      ids.forEach(function (id) {
        var p = findProduct(id); if (!p) return;
        html += '<li class="woocommerce-mini-cart-item mini_cart_item">' +
          '<a href="' + productHref(p) + '"><img src="' + esc(asset(p.img)) + '" alt="' + esc(p.name) + '"/>' + esc(p.name) + '</a>' +
          '<span class="quantity">' + cart[id] + ' × <span class="woocommerce-Price-amount amount"><bdi>' + money(p.price) + '</bdi></span></span>' +
          '<a href="#" class="remove" data-remove="' + esc(id) + '" aria-label="Xóa">×</a></li>';
      });
      html += '</ul><p class="woocommerce-mini-cart__total total"><strong>Tổng:</strong> <span class="woocommerce-Price-amount amount"><bdi>' + money(cartTotal()) + '</bdi></span></p>' +
        '<p class="woocommerce-mini-cart__buttons buttons"><a href="' + BASE + 'cart/" class="button wc-forward">Xem giỏ hàng</a><a href="' + BASE + 'cart/" class="button checkout wc-forward">Thanh toán</a></p>';
      el.innerHTML = html;
    });
  }

  function productCard(p) {
    var href = productHref(p);
    return '<div class="product-small col has-hover product type-product status-publish instock product_cat-' + p.cat + ' has-post-thumbnail shipping-taxable purchasable product-type-simple">' +
      '<div class="col-inner"><div class="badge-container absolute left top z-1"></div>' +
      '<div class="product-small box"><div class="box-image"><div class="image-zoom">' +
      '<a aria-label="' + esc(p.name) + '" href="' + href + '"><img alt="' + esc(p.name) + '" class="attachment-woocommerce_thumbnail size-woocommerce_thumbnail" loading="lazy" src="' + esc(asset(p.img)) + '" width="1000" height="1000"/></a></div>' +
      '<div class="image-tools grid-tools text-center hide-for-small bottom hover-slide-in show-on-hover">' +
      '<a aria-label="Thêm vào giỏ hàng: ' + esc(p.name) + '" class="add-to-cart-grid no-padding is-transparent product_type_simple add_to_cart_button ajax_add_to_cart" data-product_id="' + esc(p.id) + '" data-quantity="1" href="' + href + '" rel="nofollow" role="button"><div class="cart-icon tooltip is-small" title="Thêm vào giỏ hàng"><strong>+</strong></div></a>' +
      '<a class="quick-view" data-prod="' + esc(p.id) + '" href="' + href + '">Quick View</a></div></div>' +
      '<div class="box-text box-text-products text-center grid-style-2"><div class="title-wrapper">' +
      '<p class="category uppercase is-smaller no-text-overflow product-cat op-7">' + esc(p.catName) + '</p>' +
      '<p class="name product-title woocommerce-loop-product__title"><a class="woocommerce-LoopProduct-link woocommerce-loop-product__link" href="' + href + '">' + esc(p.name) + '</a></p></div>' +
      '<div class="price-wrapper"><span class="price"><span class="woocommerce-Price-amount amount"><bdi>' + money(p.price) + '</bdi></span></span></div></div>' +
      '</div></div></div>';
  }

  /* ---------------------------------------------------------------- product page */
  function initProductPage() {
    var titleEl = document.getElementById('pdp-title');
    if (!titleEl) return;
    var params = new URLSearchParams(window.location.search);
    var bodyId = document.body.getAttribute('data-product-id');
    var p = findProduct(bodyId) || findProduct(params.get('id')) || PRODUCTS[0];
    if (!p) return;
    var catHref = CAT_FILE[p.cat] || HOME;
    var material = p.cat === 'baccarat' ? 'Pha lê Baccarat, đồng mạ vàng 24K' :
      (p.cat === 'serip' ? 'Kim loại mạ vàng, pha lê nghệ thuật' : 'Đồng mạ vàng, pha lê Asfour');
    var origin = p.cat === 'serip' ? 'Ý (Italy)' : (p.cat === 'baccarat' ? 'Pháp / Ý' : 'Tây Ban Nha / Ý');

    document.title = p.name + ' | Cavani Lighting';
    titleEl.textContent = p.name;
    var img = document.getElementById('pdp-img');
    var thumb = document.getElementById('pdp-thumb');
    var imgLink = document.getElementById('pdp-img-link');
    if (img) { img.src = asset(p.img); img.alt = p.name; }
    if (thumb) { thumb.src = asset(p.img); thumb.alt = p.name; }
    if (imgLink) imgLink.href = asset(p.img);
    var priceTxt = money(p.price);
    ['pdp-price', 'pdp-price2'].forEach(function (id) { var el = document.getElementById(id); if (el) el.textContent = priceTxt; });
    var catLink = document.getElementById('pdp-cat-link');
    if (catLink) { catLink.href = catHref; catLink.textContent = CAT_LABEL[p.cat] || p.catName; }
    var sku = document.getElementById('pdp-sku');
    if (sku) sku.textContent = 'CV-' + p.id.replace(/[^a-z0-9]/gi, '').toUpperCase();
    var matEl = document.getElementById('pdp-material'); if (matEl) matEl.textContent = material;
    var sizeEl = document.getElementById('pdp-size'); if (sizeEl) sizeEl.textContent = 'Ø 800 × H 700 mm (tham khảo)';
    var originEl = document.getElementById('pdp-origin'); if (originEl) originEl.textContent = origin;
    var desc = document.getElementById('pdp-desc'); if (desc) desc.textContent = p.desc;
    var descTitle = document.getElementById('pdp-desc-title'); if (descTitle) descTitle.textContent = p.name.toUpperCase() + ' – BIỂU TƯỢNG SANG TRỌNG';
    var descLong = document.getElementById('pdp-desc-long');
    if (descLong) descLong.textContent = p.desc + ' Sản phẩm được nhập khẩu chính hãng, bảo hành 24 tháng và được đội ngũ Cavani tư vấn lắp đặt tận nơi.';
    var add = document.getElementById('pdp-add');
    if (add) add.setAttribute('data-product-id', p.id);
    var attrCat = document.getElementById('pdp-attr-cat'); if (attrCat) attrCat.textContent = p.catName;
    var attrMat = document.getElementById('pdp-attr-material'); if (attrMat) attrMat.textContent = material;
    var attrOrigin = document.getElementById('pdp-attr-origin'); if (attrOrigin) attrOrigin.textContent = origin;
    var sideActive = document.querySelector('#product-sidebar .product-categories a[data-cat="' + p.cat + '"]') ||
      document.querySelector('#product-sidebar .product-categories a[href="' + catHref + '"]');
    if (sideActive) sideActive.parentElement.classList.add('current-cat');

    var related = PRODUCTS.filter(function (x) { return x.cat === p.cat && x.id !== p.id; }).slice(0, 4);
    var rel = document.getElementById('pdp-related');
    if (rel) rel.innerHTML = related.map(productCard).join('');
  }

  /* ---------------------------------------------------------------- search */
  function initSearch() {
    var inputs = document.querySelectorAll('.search-field');
    if (!inputs.length) return;
    inputs.forEach(function (input) {
      var form = input.closest('form');
      if (form) form.addEventListener('submit', function (e) { e.preventDefault(); });
      input.addEventListener('input', function () {
        var q = input.value.trim().toLowerCase();
        var box = form ? form.querySelector('.live-search-results') : null;
        if (!box) {
          box = document.querySelector('#search-lightbox .live-search-results');
        }
        if (!box) return;
        if (!q) { box.innerHTML = ''; box.style.display = 'none'; return; }
        var hits = PRODUCTS.filter(function (p) {
          return (p.name + ' ' + p.catName + ' ' + p.cat).toLowerCase().indexOf(q) !== -1;
        }).slice(0, 8);
        if (!hits.length) {
          box.innerHTML = '<div class="autocomplete-suggestions"><div class="autocomplete-no-results">Không tìm thấy sản phẩm phù hợp.</div></div>';
        } else {
          box.innerHTML = '<div class="autocomplete-suggestions">' + hits.map(function (p) {
            return '<a class="autocomplete-suggestion" href="' + productHref(p) + '">' +
              '<img src="' + esc(asset(p.img)) + '" alt="' + esc(p.name) + '"/>' +
              '<span class="title">' + esc(p.name) + '</span>' +
              '<span class="price">' + money(p.price) + '</span></a>';
          }).join('') + '</div>';
        }
        box.style.display = 'block';
      });
    });
  }

  /* ---------------------------------------------------------------- cart page */
  function renderCartPage() {
    var page = document.getElementById('cart-page');
    if (!page) return;
    var cart = getCart(), ids = Object.keys(cart);
    var tbody = document.getElementById('cart-items');
    var empty = document.getElementById('cart-empty');
    var wrap = document.getElementById('cart-filled');
    if (!ids.length) {
      if (empty) empty.style.display = 'block';
      if (wrap) wrap.style.display = 'none';
      return;
    }
    if (empty) empty.style.display = 'none';
    if (wrap) wrap.style.display = 'block';
    var html = '';
    ids.forEach(function (id) {
      var p = findProduct(id); if (!p) return;
      var qty = cart[id];
      html += '<tr class="woocommerce-cart-form__cart-item cart_item">' +
        '<td class="product-remove"><a href="#" class="remove" data-remove="' + esc(id) + '" aria-label="Xóa">×</a></td>' +
        '<td class="product-thumbnail"><a href="' + productHref(p) + '"><img src="' + esc(asset(p.img)) + '" alt="' + esc(p.name) + '"/></a></td>' +
        '<td class="product-name" data-title="Sản phẩm"><a href="' + productHref(p) + '">' + esc(p.name) + '</a><p class="product-cat">' + esc(p.catName) + '</p></td>' +
        '<td class="product-price" data-title="Giá"><span class="woocommerce-Price-amount amount"><bdi>' + money(p.price) + '</bdi></span></td>' +
        '<td class="product-quantity" data-title="Số lượng"><div class="quantity buttons_added">' +
        '<input type="button" class="minus button is-form" value="-"/>' +
        '<input type="number" class="input-text qty text cart-qty" data-id="' + esc(id) + '" min="1" value="' + qty + '"/>' +
        '<input type="button" class="plus button is-form" value="+"/></div></td>' +
        '<td class="product-subtotal" data-title="Tạm tính"><span class="woocommerce-Price-amount amount"><bdi>' + money(p.price * qty) + '</bdi></span></td></tr>';
    });
    if (tbody) tbody.innerHTML = html;
    var sub = document.getElementById('cart-subtotal'); if (sub) sub.textContent = money(cartTotal());
    var tot = document.getElementById('cart-total'); if (tot) tot.textContent = money(cartTotal());
  }

  /* ---------------------------------------------------------------- events */
  document.addEventListener('DOMContentLoaded', function () {
    renderCartCount();
    renderMiniCart();
    initProductPage();
    initSearch();
    renderCartPage();

    // add to cart
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-add-to-cart], .add_to_cart_button, #pdp-add');
      if (btn) {
        e.preventDefault();
        var id = btn.getAttribute('data-product-id') || btn.getAttribute('data-product_id');
        if (!id) return;
        var qtyEl = document.getElementById('pdp-qty');
        var qty = (btn.id === 'pdp-add' && qtyEl) ? Math.max(1, parseInt(qtyEl.value, 10) || 1) : 1;
        window.CavaniCart.add(id, qty);
        btn.classList.add('added');
        var old = btn.getAttribute('aria-label') || '';
        btn.setAttribute('aria-label', 'Đã thêm vào giỏ hàng');
        setTimeout(function () { btn.classList.remove('added'); btn.setAttribute('aria-label', old); }, 1600);
        return;
      }
      var rm = e.target.closest('[data-remove]');
      if (rm) { e.preventDefault(); window.CavaniCart.remove(rm.getAttribute('data-remove')); return; }

      // quantity +/-
      var qbtn = e.target.closest('.quantity .plus, .quantity .minus');
      if (qbtn) {
        var input = qbtn.parentElement.querySelector('input.qty');
        if (!input) return;
        var v = Math.max(1, (parseInt(input.value, 10) || 1) + (qbtn.classList.contains('plus') ? 1 : -1));
        input.value = v;
        if (input.classList.contains('cart-qty')) window.CavaniCart.setQty(input.getAttribute('data-id'), v);
        return;
      }
    });

    document.addEventListener('change', function (e) {
      var input = e.target.closest('input.cart-qty');
      if (input) window.CavaniCart.setQty(input.getAttribute('data-id'), Math.max(1, parseInt(input.value, 10) || 1));
    });

    // fallback for product tabs (Flatsome normally handles this)
    document.addEventListener('click', function (e) {
      var tab = e.target.closest('.woocommerce-tabs .tabs a');
      if (!tab) return;
      var target = tab.getAttribute('href');
      if (!target || target.charAt(0) !== '#') return;
      e.preventDefault();
      var wrap = tab.closest('.woocommerce-tabs');
      wrap.querySelectorAll('.tabs li').forEach(function (li) { li.classList.remove('active'); });
      tab.parentElement.classList.add('active');
      wrap.querySelectorAll('.tab-panels > .panel').forEach(function (p) { p.classList.remove('active'); });
      var panel = wrap.querySelector(target);
      if (panel) panel.classList.add('active');
    });

    // checkout demo
    document.addEventListener('click', function (e) {
      var co = e.target.closest('#cart-checkout, .checkout');
      if (co) { e.preventDefault(); alert('Đây là bản demo giao diện Cavani. Chức năng thanh toán chưa được kết nối.'); }
    });
  });

  window.CavaniCart = {
    add: function (id, qty) {
      var c = getCart(); c[id] = (c[id] || 0) + (qty || 1); saveCart(c);
      document.dispatchEvent(new CustomEvent('cavani:cart-updated'));
    },
    remove: function (id) { var c = getCart(); delete c[id]; saveCart(c); document.dispatchEvent(new CustomEvent('cavani:cart-updated')); },
    setQty: function (id, q) { var c = getCart(); if (q <= 0) delete c[id]; else c[id] = q; saveCart(c); document.dispatchEvent(new CustomEvent('cavani:cart-updated')); },
    items: getCart, total: cartTotal, money: money
  };
})();
