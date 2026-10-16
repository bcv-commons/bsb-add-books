window.NAV = {"ch-de-be/ch-de-be_BSB": {"name": "Bern German (Berndeutsch)", "books": [["gen", "Ds erschte Buech Mose", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]], ["exo", "Ds zwöite Buech Mose", [1]], ["rut", "Ds Buech Rut", [1, 2, 3, 4]], ["jon", "Ds Buech Jona", [1, 2, 3, 4]], ["jhn", "Ds Johannes-Evangelium", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]], ["eph", "D Brief a d Epheser", [1, 2, 3, 4, 5, 6]]]}, "dan/dan_BSB": {"name": "Danish (dansk)", "books": [["gen", "1 Mosebog", [20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]], ["jos", "Josvabogen", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]], ["dan", "Daniels Bog", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]]]}, "jam/jam_BSB": {"name": "Jamaican Creole English", "books": [["gen", "Genesis", [1]]]}, "kvg/kvg_BSB": {"name": "Kuni (Kuni-Boazi, Papua New Guinea)", "books": [["gen", "Iqandengaz (Genesis)", [31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]]]}};
// The reader's selectors: language, book, chapter (scripts/build_site.py writes window.NAV below).
(function () {
  var N = window.NAV, H = window.HERE, root = document.currentScript.src.replace(/nav\.js.*$/, "");
  function opt(sel, v, t, on) { var o = document.createElement("option"); o.value = v; o.textContent = t; o.selected = on; sel.appendChild(o); }
  var L = document.querySelector('[data-pick="lang"]'), B = document.querySelector('[data-pick="book"]'), C = document.querySelector('[data-pick="ch"]');
  if (!L) return;
  Object.keys(N).forEach(function (p) { opt(L, p, N[p].name, p === H.p); });
  N[H.p].books.forEach(function (b) { opt(B, b[0], b[1], b[0] === H.b); });
  function chs() { C.innerHTML = ""; var b = N[H.p].books.filter(function (x) { return x[0] === B.value; })[0];
    b[2].forEach(function (n) { opt(C, n, n, B.value === H.b && n === H.c); }); }
  chs();
  function go(p, b, c) { location.href = root + p + "/read/" + (b ? b + "/" + String(c).padStart(3, "0") + ".html" : "index.html"); }
  L.onchange = function () { var b = N[L.value].books[0]; go(L.value, b[0], b[2][0]); };
  B.onchange = function () { chs(); go(H.p, B.value, C.value); };
  C.onchange = function () { go(H.p, B.value, C.value); };
})();
// The view switch: text, BHSA clauses, MACULA/UHB clauses; no reload, the choice remembered across pages.
(function () {
  var bs = document.querySelectorAll(".modes button"), vs = document.querySelectorAll(".view");
  if (!bs.length) return;
  function get() { try { return localStorage.getItem("view") || "std"; } catch (e) { return "std"; } }
  function set(m) { try { localStorage.setItem("view", m); } catch (e) {} }
  function show(m, keep) {
    var b = document.querySelector('.modes button[data-mode="' + m + '"]');
    if (!b || b.disabled) m = "std";
    bs.forEach(function (x) { x.classList.toggle("on", x.dataset.mode === m); x.setAttribute("aria-selected", x.dataset.mode === m); });
    vs.forEach(function (v) { v.hidden = v.dataset.view !== m; });
    if (!keep) set(m);
  }
  bs.forEach(function (b) { b.onclick = function () { show(b.dataset.mode); }; });
  show(get(), true);
})();
