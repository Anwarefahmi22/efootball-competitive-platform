/* eFootball Arena — Eyes Loader (shared component)
   Requires /shared/eyes-loader.css. Exposes:
     EyesLoader.splash()              full-screen intro, one 9.6s cycle,
                                      once per session, tap/Enter/Space
                                      or the cycle end dismisses it.
     EyesLoader.wait(target, options) looping eyes while work is in
                                      flight. target = null → fixed
                                      overlay; target = element → inline
                                      render inside it. options.label
                                      sets a caption under the eyes.
                                      Returns { hide() }.
   Under prefers-reduced-motion the splash is skipped entirely and the
   wait mode renders one static frame (CSS handles the still state). */
(function () {
  if (window.EyesLoader) return;

  var uid = 0;
  var EYE_PATH = "M8 88 L58 34 Q150 -6 242 34 L292 88 L240 128 Q150 162 60 128 Z";

  function eyeSVG(flip) {
    uid += 1;
    var g = "elxIris" + uid, c = "elxClip" + uid, t = "elxTomoe" + uid;
    return '' +
    '<svg class="elx-eye' + (flip ? " elx-flip" : "") + '" viewBox="0 0 300 170" aria-hidden="true">' +
      '<defs>' +
        '<radialGradient id="' + g + '" cx="50%" cy="50%" r="50%">' +
          '<stop offset="0%" stop-color="#a3ff12"/>' +
          '<stop offset="55%" stop-color="#93e00d"/>' +
          '<stop offset="100%" stop-color="#6dcc0a"/>' +
        '</radialGradient>' +
        '<clipPath id="' + c + '"><path d="' + EYE_PATH + '"/></clipPath>' +
        '<path id="' + t + '" d="M0 -21 A21 21 0 1 0 21 0 A10.5 10.5 0 1 1 0 -21 Z"/>' +
      '</defs>' +
      '<g class="elx-lid">' +
        '<path d="' + EYE_PATH + '" fill="#050a07"/>' +
        '<g clip-path="url(#' + c + ')">' +
          '<g class="elx-rings">' +
            '<circle cx="150" cy="82" r="56" fill="#050a07"/>' +
            '<circle cx="150" cy="82" r="49" fill="none" stroke="#a3ff12" stroke-width="3.5"/>' +
            '<circle cx="150" cy="82" r="37" fill="none" stroke="#a3ff12" stroke-width="7"/>' +
            '<circle cx="150" cy="82" r="26" fill="none" stroke="#a3ff12" stroke-width="3.5"/>' +
            '<circle cx="150" cy="82" r="15" fill="none" stroke="#a3ff12" stroke-width="3"/>' +
            '<circle cx="150" cy="82" r="7.5" fill="#a3ff12"/>' +
            '<circle cx="131" cy="61" r="4.5" fill="#a3ff12" opacity=".55"/>' +
          '</g>' +
          '<g class="elx-tomoe">' +
            '<circle cx="150" cy="82" r="56" fill="url(#' + g + ')"/>' +
            '<g fill="#050a07">' +
              '<use href="#' + t + '" transform="translate(150 82) rotate(0) translate(0 -31)"/>' +
              '<use href="#' + t + '" transform="translate(150 82) rotate(120) translate(0 -31)"/>' +
              '<use href="#' + t + '" transform="translate(150 82) rotate(240) translate(0 -31)"/>' +
            '</g>' +
            '<circle cx="150" cy="82" r="13" fill="#050a07"/>' +
            '<circle cx="131" cy="61" r="4.5" fill="#a3ff12" opacity=".55"/>' +
          '</g>' +
          '<ellipse cx="128" cy="58" rx="13" ry="8" fill="#a3ff12" opacity=".16" transform="rotate(-24 128 58)"/>' +
        '</g>' +
      '</g>' +
    '</svg>';
  }

  function eyesHTML() {
    return '<div class="elx-eyes" aria-hidden="true">' + eyeSVG(false) + eyeSVG(true) + "</div>";
  }

  var PITCH_SVG =
    '<svg viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">' +
    '<g fill="none" stroke="#1f4a33" stroke-width="2">' +
    '<line x1="720" y1="0" x2="720" y2="900"/><circle cx="720" cy="450" r="150"/>' +
    '<path d="M0 300 H220 V600 H0"/><path d="M1440 300 H1220 V600 H1440"/>' +
    '<path d="M0 380 H90 V520 H0"/><path d="M1440 380 H1350 V520 H1440"/></g>' +
    '<circle cx="720" cy="450" r="4" fill="#1f4a33"/></svg>';

  var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------- Splash ---------------- */
  var CYCLE = 9600, DONE = 7296, BAR_FADE = 900;

  function splash() {
    var noop = { hide: function () {} };
    if (reducedMotion) return noop;
    try {
      if (sessionStorage.getItem("elx-splash-seen")) return noop;
      sessionStorage.setItem("elx-splash-seen", "1");
    } catch (e) { /* private mode: just play it */ }

    var root = document.createElement("div");
    root.className = "elx elx-splash elx-once";
    root.setAttribute("role", "status");
    root.setAttribute("aria-label", "جارٍ التحميل");
    root.innerHTML =
      '<div class="elx-pitch">' + PITCH_SVG + "</div>" +
      '<div class="elx-title" dir="ltr"><span class="elx-l1">Loading</span><span class="elx-l2">Animation</span></div>' +
      '<div class="elx-center"><div class="elx-glow" aria-hidden="true"></div>' +
        eyesHTML() +
        '<div class="elx-welcome" dir="ltr"><span>Welcome</span></div>' +
        '<div class="elx-progress" dir="ltr" aria-hidden="true"><div class="elx-track"><div class="elx-fill"></div></div><span class="elx-pct">0%</span></div>' +
      "</div>" +
      '<p class="elx-wordmark" dir="ltr">eFootball Arena</p>';
    document.body.appendChild(root);
    document.body.style.overflow = "hidden";

    var fill = root.querySelector(".elx-fill");
    var pct = root.querySelector(".elx-pct");
    var progress = root.querySelector(".elx-progress");
    var start = performance.now(), lastPct = -1, raf = 0, gone = false;

    function dismiss() {
      if (gone) return;
      gone = true;
      cancelAnimationFrame(raf);
      root.classList.add("elx-dismissing");
      document.body.style.overflow = "";
      setTimeout(function () { root.remove(); }, 550);
    }
    function easeOutCubic(x) { return 1 - Math.pow(1 - x, 3); }
    function tick(now) {
      if (gone) return;
      var t = now - start, p, op;
      if (t <= DONE) { p = easeOutCubic(Math.min(1, t / DONE)); op = 1; }
      else { p = 1; op = Math.max(0, 1 - (t - DONE) / BAR_FADE); }
      fill.style.transform = "scaleX(" + p + ")";
      var n = Math.round(p * 100);
      if (n !== lastPct) { pct.textContent = n + "%"; lastPct = n; }
      progress.style.opacity = op.toFixed(3);
      if (t < DONE + BAR_FADE + 1400) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    setTimeout(dismiss, DONE + BAR_FADE + 1450); /* ≈9.65s hard cap */
    root.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", function onKey(e) {
      if (e.key === "Enter" || e.key === " " || e.key === "Escape") {
        dismiss();
        document.removeEventListener("keydown", onKey);
      }
    });
    return { hide: dismiss };
  }

  /* ---------------- Wait ---------------- */
  function wait(target, options) {
    options = options || {};
    var root = document.createElement("div");
    root.className = "elx elx-waiting " + (target ? "elx-inline" : "elx-wait-overlay");
    root.setAttribute("role", "status");
    root.innerHTML = eyesHTML() +
      (options.label ? '<div class="elx-label">' + options.label + "</div>" : "");
    if (target) { target.innerHTML = ""; target.appendChild(root); }
    else document.body.appendChild(root);

    var gone = false;
    return {
      hide: function () {
        if (gone) return;
        gone = true;
        if (target) { root.remove(); return; }
        root.classList.add("elx-dismissing");
        setTimeout(function () { root.remove(); }, 280);
      },
    };
  }

  window.EyesLoader = { splash: splash, wait: wait };
})();
