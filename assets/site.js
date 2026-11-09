(function () {
  "use strict";
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  // mobile menu
  var top = document.querySelector(".top");
  var menuBtn = document.querySelector(".menu-btn");
  if (menuBtn && top) {
    menuBtn.addEventListener("click", function () {
      var open = top.getAttribute("data-open") === "true";
      top.setAttribute("data-open", open ? "false" : "true");
      menuBtn.setAttribute("aria-expanded", open ? "false" : "true");
      menuBtn.setAttribute("aria-label", open ? "Menu" : "Close menu");
    });
  }

  // close the menu after picking a link (matters for same-page links like Updates)
  document.querySelectorAll(".nav a").forEach(function (a) {
    a.addEventListener("click", function () {
      if (top && top.getAttribute("data-open") === "true" && menuBtn) menuBtn.click();
    });
  });

  // home: large name shrinks into the header, intro fades as you scroll
  var home = document.querySelector(".page");
  if (home) {
    var nameEl = home.querySelector(".name");
    var ticking = false;
    var update = function () {
      ticking = false;
      if (!home.classList.contains("home")) { nameEl.style.setProperty("--name-scale", "1"); return; }
      // the intro only fades when it sits above the photo
      var intro = home.classList.contains("intro-top") ? home.querySelector(".intro") : null;
      var p = Math.min(1, Math.max(0, window.scrollY / 140));
      nameEl.style.setProperty("--name-scale", (1.5 - 0.5 * p).toFixed(3));
      if (intro) intro.style.setProperty("--intro-fade", (1 - p).toFixed(3));
    };
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
    window.hkUpdateHome = update;
  }

  // landing slideshow: crossfade every 6s; dots jump to a photo
  document.querySelectorAll(".bleed[data-slides]").forEach(function (show) {
    var slides = show.querySelectorAll(".slide");
    var dots = show.querySelectorAll(".dots button");
    if (slides.length < 2) return;
    var i = 0, timer = null;
    var still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var go = function (n) {
      i = (n + slides.length) % slides.length;
      slides.forEach(function (s, k) {
        s.classList.toggle("on", k === i);
        if (k === i) s.removeAttribute("aria-hidden"); else s.setAttribute("aria-hidden", "true");
      });
      dots.forEach(function (d, k) { if (k === i) d.setAttribute("aria-current", "true"); else d.removeAttribute("aria-current"); });
    };
    var start = function () {
      if (still) return;
      clearInterval(timer);
      timer = setInterval(function () { if (!document.hidden) go(i + 1); }, 6000);
    };
    dots.forEach(function (d, k) { d.addEventListener("click", function () { go(k); start(); }); });
    // open on the photo that matches the theme: the night shot in night mode
    var isNight = function () {
      return getComputedStyle(document.documentElement).getPropertyValue("--night").trim() === "1";
    };
    var openOnTheme = function () {
      var want = 0;
      if (isNight()) slides.forEach(function (s, k) { if (s.getAttribute("data-mode") === "night") want = k; });
      show.classList.add("instant");
      go(want);
      requestAnimationFrame(function () { requestAnimationFrame(function () { show.classList.remove("instant"); }); });
    };
    openOnTheme();
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      if (mq.addEventListener) mq.addEventListener("change", function () { openOnTheme(); start(); });
    }
    start();
  });

  // grid / list + scale
  document.querySelectorAll("[data-view]").forEach(function (index) {
    var grid = index.querySelector(".grid");
    var buttons = index.querySelectorAll("[data-set-view]");
    var range = index.querySelector(".scale input");
    var setView = function (v) {
      index.setAttribute("data-view", v);
      buttons.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-set-view") === v ? "true" : "false"); });
      store.set("hk-view", v);
    };
    var setCols = function (n) {
      grid.style.setProperty("--cols", n);
      if (range) range.value = n;
      store.set("hk-cols", n);
    };
    buttons.forEach(function (b) { b.addEventListener("click", function () { setView(b.getAttribute("data-set-view")); }); });
    if (range) range.addEventListener("input", function () { setCols(range.value); });
    setView(store.get("hk-view") || "grid");
    setCols(store.get("hk-cols") || (range ? range.value : 3));
  });

  // lightbox
  var items = [], title = null;
  var lb, img, count, cap, k = 0, returnTo = null;

  function show() {
    img.src = items[k].src;
    img.alt = items[k].cap || (title ? title.textContent : "");
    count.textContent = (k + 1) + " / " + items.length;
    cap.textContent = items[k].cap;
  }
  function go(d) { k = (k + d + items.length) % items.length; show(); }
  function onKey(e) {
    if (e.key === "Escape") close();
    else if (e.key === "ArrowRight") go(1);
    else if (e.key === "ArrowLeft") go(-1);
  }
  function close() {
    lb.remove(); lb = null;
    document.removeEventListener("keydown", onKey);
    document.body.style.overflow = "";
    if (returnTo) returnTo.focus();
  }
  function open(btn) {
    var group = btn.closest(".images");
    var btns = Array.prototype.slice.call(group.querySelectorAll("[data-full]"));
    items = btns.map(function (b) { return { src: b.getAttribute("data-full"), cap: b.getAttribute("data-cap") || "" }; });
    var scope = group.closest("[data-page]") || document;
    title = scope.querySelector(".project-head h1");
    k = btns.indexOf(btn); returnTo = document.activeElement;
    lb = document.createElement("div");
    lb.className = "lightbox";
    lb.setAttribute("role", "dialog");
    lb.setAttribute("aria-modal", "true");
    lb.innerHTML =
      '<div class="lb-top"><span>' + (title ? title.textContent : "") + '</span><button type="button" class="lb-close">Close</button></div>' +
      '<div class="lb-stage"><img alt=""></div>' +
      '<div class="lb-bottom"><button type="button" class="lb-prev">Previous</button><span class="lb-cap"></span><span class="lb-count"></span><button type="button" class="lb-next">Next</button></div>' +
      '<div class="lb-hit l" aria-hidden="true"></div><div class="lb-hit r" aria-hidden="true"></div>';
    img = lb.querySelector("img"); count = lb.querySelector(".lb-count"); cap = lb.querySelector(".lb-cap");
    lb.querySelector(".lb-close").onclick = close;
    lb.querySelector(".lb-prev").onclick = function () { go(-1); };
    lb.querySelector(".lb-next").onclick = function () { go(1); };
    lb.querySelector(".lb-hit.l").onclick = function () { go(-1); };
    lb.querySelector(".lb-hit.r").onclick = function () { go(1); };
    var x0 = null;
    lb.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    lb.addEventListener("touchend", function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
      x0 = null;
    });
    document.addEventListener("keydown", onKey);
    document.body.appendChild(lb);
    document.body.style.overflow = "hidden";
    show();
    lb.querySelector(".lb-close").focus();
  }
  document.querySelectorAll(".images [data-full]").forEach(function (b) {
    b.addEventListener("click", function () { open(b); });
  });
})();
