/* 江衍睿 · 个人网页 —— 多页共用脚本
   1) 中英切换：带 data-en / data-zh 的元素互换 innerHTML；data-en-href / data-zh-href 换链接
   2) 顶部 tab：hash 路由（#cv / #research / #photography），可前进后退、可单独分享
   3) 摄影灯箱：点开看大图，键盘 Esc / ← / →
   4) 防下载：图库与灯箱内禁用右键菜单与图片拖拽
   （项目详情页没有 tab 与灯箱，相关逻辑会自动跳过。） */
(function () {
  var LANGS = ['en', 'zh'];
  var els = document.querySelectorAll('[data-en][data-zh]');

  function setLang(l) {
    els.forEach(function (e) {
      var v = e.getAttribute('data-' + l);
      if (v !== null) e.innerHTML = v;
      var h = e.getAttribute('data-' + l + '-href');
      if (h !== null) e.setAttribute('href', h);
    });
    document.querySelectorAll('[data-lang-btn]').forEach(function (b) {
      b.classList.toggle('on', b.getAttribute('data-lang-btn') === l);
    });
    document.documentElement.lang = (l === 'zh') ? 'zh-CN' : 'en';
    var t = document.body.getAttribute('data-title-' + l);
    if (t) document.title = t;
    try { localStorage.setItem('yj_lang', l); } catch (e) {}
  }

  document.querySelectorAll('[data-lang-btn]').forEach(function (b) {
    b.addEventListener('click', function () { setLang(b.getAttribute('data-lang-btn')); });
  });

  var saved = null;
  try { saved = localStorage.getItem('yj_lang'); } catch (e) {}
  if (!saved) {
    saved = (navigator.language || 'en').toLowerCase().indexOf('zh') === 0 ? 'zh' : 'en';
  }
  setLang(saved);

  function curLang() {
    return document.documentElement.lang === 'zh-CN' ? 'zh' : 'en';
  }

  var y = document.getElementById('yr');
  if (y) y.textContent = new Date().getFullYear();

  /* ---------- 图片没到位时显示占位框（项目图文页用） ---------- */
  document.querySelectorAll('figure.shot img').forEach(function (img) {
    function fail() {
      var f = img.closest('figure');
      if (f) f.classList.add('empty');
    }
    if (img.complete && img.naturalWidth === 0) fail();
    img.addEventListener('error', fail);
  });

  /* ---------- 顶部 tab ---------- */
  var tabs = document.querySelectorAll('.tab');
  if (tabs.length && document.getElementById('panel-cv')) {
    var names = Array.prototype.map.call(tabs, function (b) { return b.getAttribute('data-tab'); });

    function showTab(name, updateHash) {
      if (names.indexOf(name) < 0) name = names[0];
      names.forEach(function (n) {
        var p = document.getElementById('panel-' + n);
        if (p) p.hidden = (n !== name);
      });
      tabs.forEach(function (b) {
        b.setAttribute('aria-selected', b.getAttribute('data-tab') === name ? 'true' : 'false');
      });
      try { localStorage.setItem('yj_tab', name); } catch (e) {}
      if (updateHash !== false && location.hash !== '#' + name) {
        history.replaceState(null, '', '#' + name);
      }
    }

    tabs.forEach(function (b) {
      b.addEventListener('click', function () { showTab(b.getAttribute('data-tab')); });
    });
    window.addEventListener('hashchange', function () {
      showTab((location.hash || '').replace('#', ''), false);
    });

    var start = (location.hash || '').replace('#', '');
    if (names.indexOf(start) < 0) {
      try { start = localStorage.getItem('yj_tab') || names[0]; } catch (e) { start = names[0]; }
      if (names.indexOf(start) < 0) start = names[0];
    }
    showTab(start, false);
  }

  /* ---------- 摄影灯箱 ---------- */
  var lb = document.getElementById('lb');
  var figs = document.querySelectorAll('.photo');
  if (lb && figs.length) {
    var lbImg = document.getElementById('lb-img');
    var lbTitle = document.getElementById('lb-title');
    var lbMeta = document.getElementById('lb-meta');
    var cur = -1;

    function capsOf(f, lg) {
      var t = f.querySelector('.cap-title'), m = f.querySelector('.cap-meta');
      return [t ? t.getAttribute('data-' + lg) : '', m ? m.getAttribute('data-' + lg) : ''];
    }

    function fill(f) {
      var lg = curLang();
      var c = capsOf(f, lg);
      lbImg.src = f.getAttribute('data-full');
      lbImg.alt = c[0] || '';
      lbTitle.textContent = c[0];
      lbMeta.textContent = c[1];
    }

    function openLb(i) {
      if (i < 0 || i >= figs.length) return;
      cur = i;
      fill(figs[i]);
      lb.hidden = false;
      document.body.classList.add('lb-open');
      document.getElementById('lb-close').focus();
    }
    function closeLb() {
      lb.hidden = true;
      document.body.classList.remove('lb-open');
      if (cur >= 0 && figs[cur]) figs[cur].focus();
    }

    figs.forEach(function (f, i) {
      f.addEventListener('click', function () { openLb(i); });
      f.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); openLb(i); }
      });
    });
    document.getElementById('lb-close').addEventListener('click', closeLb);
    document.getElementById('lb-prev').addEventListener('click', function (e) {
      e.stopPropagation(); openLb(cur - 1);
    });
    document.getElementById('lb-next').addEventListener('click', function (e) {
      e.stopPropagation(); openLb(cur + 1);
    });
    lb.addEventListener('click', function (e) { if (e.target === lb) closeLb(); });
    document.addEventListener('keydown', function (e) {
      if (lb.hidden) return;
      if (e.key === 'Escape') closeLb();
      else if (e.key === 'ArrowLeft') openLb(cur - 1);
      else if (e.key === 'ArrowRight') openLb(cur + 1);
    });
    // 切语言时同步刷新灯箱里的说明
    document.querySelectorAll('[data-lang-btn]').forEach(function (b) {
      b.addEventListener('click', function () {
        if (!lb.hidden && cur >= 0) fill(figs[cur]);
      });
    });
  }

  /* ---------- 防下载（图库与灯箱内） ---------- */
  document.addEventListener('contextmenu', function (e) {
    if (e.target.closest && e.target.closest('#gallery-grid, #lb')) e.preventDefault();
  });
  document.addEventListener('dragstart', function (e) {
    if (e.target && e.target.tagName === 'IMG') e.preventDefault();
  });
})();
