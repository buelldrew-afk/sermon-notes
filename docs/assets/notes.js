// Sermon notes: blanks, notes, reveal, share, text size, photo viewer.
// Everything a person types stays on their own phone (localStorage).
(function () {
  "use strict";
  var page = document.body.dataset.page || location.pathname;
  var KEY = "ccc-notes:" + page;
  var store = load();

  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) {} }
  function norm(s) { return (s || "").toLowerCase().replace(/[’']/g, "'").replace(/[^a-z0-9']+/g, " ").trim(); }

  // ---------- Blanks ----------
  var blanks = Array.prototype.slice.call(document.querySelectorAll(".blank"));
  var countEl = document.querySelector("[data-count]");
  function answers(b) { return b.dataset.answer.split("|").map(norm); }
  function check(b, typed) {
    var input = b.querySelector("input");
    var ok = answers(b).indexOf(norm(input.value)) !== -1;
    if (ok) {
      b.classList.add("correct");
      input.value = b.dataset.answer.split("|")[0];
      if (typed) input.blur();
    } else {
      b.classList.remove("correct");
    }
    return ok;
  }
  function reveal(b) {
    var input = b.querySelector("input");
    input.value = b.dataset.answer.split("|")[0];
    b.classList.add("revealed");
    store["b" + b.dataset.i] = input.value;
    save();
    updateCount();
  }
  function updateCount() {
    if (!countEl) return;
    var done = blanks.filter(function (b) { return b.classList.contains("correct") || b.classList.contains("revealed"); }).length;
    countEl.textContent = done + "/" + blanks.length;
  }
  blanks.forEach(function (b, i) {
    b.dataset.i = i;
    var input = b.querySelector("input");
    var saved = store["b" + i];
    if (saved) { input.value = saved; if (!check(b)) b.classList.remove("revealed"); }
    input.addEventListener("input", function () {
      store["b" + i] = input.value; save();
      check(b, true); updateCount();
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); var n = blanks[i + 1]; if (n) n.querySelector("input").focus(); else input.blur(); }
    });
    b.querySelector(".peek").addEventListener("click", function () { reveal(b); });
  });
  updateCount();

  // ---------- Notes ----------
  var areas = Array.prototype.slice.call(document.querySelectorAll(".notes textarea"));
  function grow(t) { t.style.height = "auto"; t.style.height = t.scrollHeight + 2 + "px"; }
  areas.forEach(function (t, i) {
    if (store["n" + i]) t.value = store["n" + i];
    grow(t);
    t.addEventListener("input", function () { store["n" + i] = t.value; save(); grow(t); });
  });

  // ---------- Scripture reading: collapse long passages ----------
  document.querySelectorAll(".reading").forEach(function (r) {
    var body = r.querySelector(".body");
    if (body.scrollHeight > 720) {
      r.classList.add("collapsible", "collapsed");
      var btn = r.querySelector(".more");
      btn.addEventListener("click", function () {
        var c = r.classList.toggle("collapsed");
        btn.textContent = c ? "Read the whole passage" : "Show less";
      });
    }
  });

  // ---------- "How it works" tip ----------
  var how = document.querySelector(".how");
  if (how) {
    try { if (localStorage.getItem("ccc-notes:tip-hidden")) how.remove(); } catch (e) {}
    var x = how.querySelector(".x");
    if (x) x.addEventListener("click", function () { how.remove(); try { localStorage.setItem("ccc-notes:tip-hidden", "1"); } catch (e) {} });
  }

  // ---------- Toast ----------
  var toastEl = document.createElement("div");
  toastEl.className = "toast"; toastEl.setAttribute("role", "status");
  document.body.appendChild(toastEl);
  var toastTimer;
  function toast(msg) {
    toastEl.textContent = msg; toastEl.classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, 2200);
  }

  // ---------- Toolbar ----------
  function on(action, fn) { var el = document.querySelector('[data-action="' + action + '"]'); if (el) el.addEventListener("click", fn); }

  on("reveal", function () {
    var left = blanks.filter(function (b) { return !b.classList.contains("correct") && !b.classList.contains("revealed"); });
    if (!left.length) { toast("All blanks are filled in"); return; }
    left.forEach(reveal);
    toast("Answers filled in");
  });

  var sizes = [1, 1.12, 1.25];
  var sizeIdx = 0;
  try { sizeIdx = +localStorage.getItem("ccc-notes:size") || 0; } catch (e) {}
  function applySize() {
    document.documentElement.style.setProperty("--scale", sizes[sizeIdx]);
    areas.forEach(grow);
  }
  applySize();
  on("size", function () {
    sizeIdx = (sizeIdx + 1) % sizes.length;
    try { localStorage.setItem("ccc-notes:size", sizeIdx); } catch (e) {}
    applySize();
    toast(["Normal text", "Larger text", "Largest text"][sizeIdx]);
  });

  function plainText() {
    var out = [];
    var d = document.body.dataset;
    out.push(d.title, [d.passage, d.date].filter(Boolean).join(" · "), "");
    document.querySelectorAll("main .intro, main .point").forEach(function (sec) {
      var h = sec.querySelector("h2");
      if (h) {
        var num = sec.querySelector(".num");
        out.push((num ? num.textContent + ". " : "") + textWithBlanks(h) + (sec.querySelector(".verses") ? " (" + sec.querySelector(".verses").textContent + ")" : ""));
      }
      sec.querySelectorAll("p.fill, li.fill").forEach(function (p) { out.push("  " + textWithBlanks(p)); });
      sec.querySelectorAll(".notes textarea").forEach(function (t) { if (t.value.trim()) out.push("  Notes: " + t.value.trim().replace(/\n/g, "\n  ")); });
      if (h) out.push("");
    });
    out.push(location.href);
    return out.join("\n").replace(/\n{3,}/g, "\n\n");
  }
  function textWithBlanks(el) {
    var c = el.cloneNode(true);
    c.querySelectorAll(".blank").forEach(function (b, i) {
      var live = el.querySelectorAll(".blank")[i].querySelector("input").value;
      b.replaceWith(live ? live : "_____");
    });
    return c.textContent.replace(/\s+/g, " ").trim();
  }
  on("share", function () {
    var text = plainText();
    if (navigator.share) {
      navigator.share({ title: document.title, text: text }).catch(function () {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function () { toast("Your notes are copied"); }, function () { toast("Couldn’t copy"); });
    }
  });

  on("clear", function () {
    if (!confirm("Clear your blanks and notes on this page?")) return;
    store = {}; save();
    blanks.forEach(function (b) { b.classList.remove("correct", "revealed"); b.querySelector("input").value = ""; });
    areas.forEach(function (t) { t.value = ""; grow(t); });
    updateCount();
    toast("Cleared");
  });

  // ---------- Photo viewer ----------
  var dlg = document.querySelector("dialog.lightbox");
  var figs = Array.prototype.slice.call(document.querySelectorAll(".gallery button"));
  var cur = 0;
  function show(i) {
    cur = (i + figs.length) % figs.length;
    var img = figs[cur].querySelector("img");
    var stageImg = dlg.querySelector(".lb-stage img");
    stageImg.src = img.currentSrc || img.src; stageImg.alt = img.alt;
    var cap = figs[cur].parentNode.querySelector("figcaption");
    dlg.querySelector(".lb-cap").textContent = cap ? cap.textContent : "";
    dlg.querySelector(".lb-count").textContent = figs.length > 1 ? (cur + 1) + " of " + figs.length : "";
    dlg.querySelectorAll(".lb-nav").forEach(function (n) { n.hidden = figs.length < 2; });
  }
  if (dlg && figs.length) {
    figs.forEach(function (f, i) { f.addEventListener("click", function () { show(i); dlg.showModal(); }); });
    dlg.querySelector(".lb-close").addEventListener("click", function () { dlg.close(); });
    dlg.querySelector(".lb-prev").addEventListener("click", function () { show(cur - 1); });
    dlg.querySelector(".lb-next").addEventListener("click", function () { show(cur + 1); });
    dlg.addEventListener("keydown", function (e) { if (e.key === "ArrowLeft") show(cur - 1); if (e.key === "ArrowRight") show(cur + 1); });
    dlg.querySelector(".lb-stage").addEventListener("click", function (e) { if (e.target === e.currentTarget) dlg.close(); });
    var sx = null, sy = null;
    dlg.addEventListener("touchstart", function (e) { if (e.touches.length === 1) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; } else sx = null; }, { passive: true });
    dlg.addEventListener("touchend", function (e) {
      if (sx === null || (window.visualViewport && window.visualViewport.scale > 1.05)) return;
      var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) show(cur + (dx < 0 ? 1 : -1));
      else if (dy > 90 && Math.abs(dy) > Math.abs(dx)) dlg.close();
      sx = null;
    }, { passive: true });
  }
})();
