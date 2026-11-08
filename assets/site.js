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
  var home = document.querySelector(".page.home");
  if (home) {
    var nameEl = home.querySelector(".name");
    var intro = home.querySelector(".intro");
    var ticking = false;
    var update = function () {
      ticking = false;
      var p = Math.min(1, Math.max(0, window.scrollY / 140));
      nameEl.style.setProperty("--name-scale", (1.5 - 0.5 * p).toFixed(3));
      if (intro) intro.style.setProperty("--intro-fade", (1 - p).toFixed(3));
    };
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  // grid / list + scale
  var index = document.querySelector("[data-view]");
  if (index) {
    var grid = index.querySelector(".grid");
    var buttons = index.querySelectorAll("[data-set-view]");
    var range = index.querySelector("#scale");
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
  }

  // lightbox
  var figs = Array.prototype.slice.call(document.querySelectorAll(".images [data-full]"));
  if (!figs.length) return;
  var items = figs.map(function (b) {
    return { src: b.getAttribute("data-full"), cap: b.getAttribute("data-cap") || "" };
  });
  var title = document.querySelector(".project-head h1");
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
  function open(start) {
    k = start; returnTo = document.activeElement;
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
  figs.forEach(function (b, i) { b.addEventListener("click", function () { open(i); }); });
})();
