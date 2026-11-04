/* eFootball Arena — navigation.
   Logged-in users get the Liquid Navigation (owner-approved model,
   2026-11-04): on desktop the liquid bar fills the top strip with all
   seven destinations and a neon indicator hanging from its bottom
   edge; on phones a slim top bar (brand, المجتمع, التصنيف, language,
   logout) plus the floating liquid dock at the bottom with the five
   core destinations. Guests keep the classic navbar below. */

const LQ_ICONS = {
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9.5 21v-6h5v6"/></svg>',
  trophy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 21h8M12 17v4M7 4h10v6a5 5 0 0 1-10 0V4Z"/><path d="M7 6H4a2 2 0 0 0 0 4h3M17 6h3a2 2 0 0 1 0 4h-3"/></svg>',
  star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 2.7 5.6 6.1.8-4.5 4.3 1.1 6.1L12 17l-5.4 2.8 1.1-6.1L3.2 9.4l6.1-.8L12 3Z"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8"/><path d="M10.3 21a2 2 0 0 0 3.4 0"/></svg>',
  people: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c1-3.2 3.4-4.5 6.5-4.5s5.5 1.3 6.5 4.5"/><circle cx="17.5" cy="9" r="2.6"/><path d="M16 15.7c2.3.2 4 1.4 4.8 4"/></svg>',
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/></svg>',
  user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-3.6 4.5-5 8-5s6.5 1.4 8 5"/></svg>',
};

const LQ_ITEMS = [
  { key: "dashboard", href: "/app/dashboard.html", label: "لوحتي", icon: "home" },
  { key: "tournaments", href: "/app/tournaments.html", label: "البطولات", icon: "trophy" },
  { key: "arena-star", href: "/app/arena-star.html", label: "أرينا ستار", icon: "star" },
  { key: "invites", href: "/app/invites.html", label: "الدعوات", icon: "bell", badge: true },
  { key: "community", href: "/app/community.html", label: "المجتمع", icon: "people" },
  { key: "ratings", href: "/app/ratings.html", label: "التصنيف", icon: "chart" },
  { key: "profile", href: "/app/profile.html", label: "حسابي", icon: "user" },
];
const LQ_DOCK_KEYS = ["dashboard", "tournaments", "arena-star", "invites", "profile"];

function lqActiveKey() {
  const p = location.pathname;
  if (p.endsWith("/dashboard.html")) return "dashboard";
  if (p.endsWith("/tournaments.html") || p.endsWith("/tournament.html") || p.endsWith("/match.html")) return "tournaments";
  if (p.endsWith("/arena-star.html")) return "arena-star";
  if (p.endsWith("/invites.html")) return "invites";
  if (p.endsWith("/community.html")) return "community";
  if (p.endsWith("/ratings.html")) return "ratings";
  if (p.endsWith("/profile.html")) return "profile";
  return null;
}

function lqItemHtml(item, activeKey) {
  const badge = item.badge ? '<span class="lq-badge nav-invite-badge" hidden></span>' : "";
  return `<li class="${item.key === activeKey ? "active" : ""}" data-key="${item.key}">
    <a href="${item.href}">
      <span class="lq-icon">${LQ_ICONS[item.icon]}${badge}</span>
      <span class="lq-text">${item.label}</span>
    </a></li>`;
}

function lqLanguageHtml() {
  return `<label class="language-picker" title="اللغة">
      <span class="lang-globe" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg></span>
      <span class="sr-only">اللغة</span>
      <select class="nav-language" aria-label="اللغة">
        <option value="ar">AR</option>
        <option value="fr">FR</option>
        <option value="en">EN</option>
      </select>
    </label>`;
}

function lqWireIndicator(zone, hoverable) {
  const indicator = zone.querySelector(".lq-indicator");
  const list = zone.querySelector("ul");
  const items = Array.from(zone.querySelectorAll("li"));
  const activeLi = zone.querySelector("li.active");
  const xFor = (li) => li.offsetLeft + li.offsetWidth / 2 - 35;
  const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* Desktop hover-follow is driven by a requestAnimationFrame spring
     (each frame closes 30% of the remaining distance) instead of a
     CSS transition: a transition restarts its full duration and
     easing on every mouseenter, so sweeping across items made the
     circle perpetually chase the cursor and stutter. The spring's
     velocity is continuous — target changes mid-flight just bend
     the path — and it settles in ~250ms with no restart artifacts. */
  let curX = null, targetX = null, rafId = 0;
  function apply(x) { indicator.style.transform = "translateX(" + x + "px)"; }
  function snap(li) {
    cancelAnimationFrame(rafId); rafId = 0;
    if (!li) { indicator.style.opacity = "0"; curX = targetX = null; return; }
    indicator.style.opacity = "1";
    curX = targetX = xFor(li);
    indicator.classList.add("lq-noanim");
    apply(curX);
    void indicator.offsetWidth;
    indicator.classList.remove("lq-noanim");
  }
  function glide(li) {
    if (!li) { indicator.style.opacity = "0"; return; }
    indicator.style.opacity = "1";
    targetX = xFor(li);
    if (curX === null || reduced) { snap(li); return; }
    if (rafId) return;
    const step = () => {
      curX += (targetX - curX) * 0.3;
      if (Math.abs(targetX - curX) < 0.5) { curX = targetX; apply(curX); rafId = 0; return; }
      apply(curX);
      rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
  }
  function place(li, animate) {
    if (hoverable && animate) glide(li);
    else snap(li);
  }
  place(activeLi, false);
  window.addEventListener("resize", () => place(zone.querySelector("li.active"), false));
  /* Late-arriving resources (the brand logo image, the Orbitron /
     IBM Plex webfonts) can still nudge the zone's geometry after the
     first placement. Correct once they settle — a short glide on
     desktop, a snap on the dock — so the indicator never sits wrong
     while the page finishes loading. The logo's box is
     aspect-ratio-reserved in CSS, so in practice the font swap is
     the only mover. Skipped mid-hover: never yank the circle away
     from a preview. */
  const correct = () => {
    if (!zone.classList.contains("lq-previewing")) place(zone.querySelector("li.active"), true);
  };
  window.addEventListener("load", correct);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(correct);
  if (hoverable) {
    items.forEach((li) => li.addEventListener("mouseenter", () => {
      items.forEach((x) => x.classList.remove("lq-preview"));
      li.classList.add("lq-preview");
      zone.classList.add("lq-previewing");
      place(li, true);
    }));
    list.addEventListener("mouseleave", () => {
      items.forEach((x) => x.classList.remove("lq-preview"));
      zone.classList.remove("lq-previewing");
      place(zone.querySelector("li.active"), true);
    });
  }
}


/* ================================================================
   Day/Night theme — bulb toggle (owner-approved 2026-11-04).
   The stored choice lives in localStorage "efa_theme" ("day" |
   "night"); pages also carry a tiny <head> snippet that applies
   it before first paint. The bulb: pull the cord (or click) to
   flip; on release the cord alone pendulum-swings (damped) while
   the bulb body stays fixed — exactly the owner's spec.
   ================================================================ */
const EFA_THEME_KEY = "efa_theme";
function efaTheme() {
  try { return localStorage.getItem(EFA_THEME_KEY) === "day" ? "day" : "night"; }
  catch (e) { return "night"; }
}
function efaApplyTheme() { document.documentElement.dataset.theme = efaTheme(); }
function efaSetTheme(t) {
  try { localStorage.setItem(EFA_THEME_KEY, t); } catch (e) {}
  efaApplyTheme();
}
efaApplyTheme();

let efaBulbSeq = 0;
function bulbToggleHtml(mini) {
  efaBulbSeq += 1;
  const gid = "efaBulbGlow" + efaBulbSeq;
  return `<button class="efa-bulb${mini ? " efa-bulb--mini" : ""}" type="button" aria-label="الوضع النهاري / الليلي" title="الوضع النهاري / الليلي">
    <svg viewBox="0 0 44 64" aria-hidden="true">
      <defs><radialGradient id="${gid}"><stop offset="0%" stop-color="#ffd75e" stop-opacity=".75"/><stop offset="100%" stop-color="#ffd75e" stop-opacity="0"/></radialGradient></defs>
      <circle class="efa-bulb-glow" cx="22" cy="16" r="21" fill="url(#${gid})"/>
      <g>
        <path class="efa-bulb-glass" d="M22 2.5a10.5 10.5 0 1 1-7.4 17.9c1 .8 1.9 1.9 1.9 3.1h11c0-1.2.9-2.3 1.9-3.1A10.5 10.5 0 0 1 22 2.5Z"/>
        <path class="efa-bulb-filament" d="M17.5 23.5v-5l2.2 3 2.3-4 2.3 4 2.2-3v5"/>
        <rect class="efa-bulb-base" x="16.5" y="25" width="11" height="2.6" rx="1.1"/>
        <rect class="efa-bulb-base" x="16.5" y="28.4" width="11" height="2.6" rx="1.1"/>
        <rect class="efa-bulb-base" x="19" y="31.8" width="6" height="2.4" rx="1.1"/>
      </g>
      <g class="efa-cord-swing">
        <line class="efa-bulb-cord" x1="22" y1="34" x2="22" y2="54"/>
        <g class="efa-bulb-bead-g"><circle class="efa-bulb-bead" cx="22" cy="57.5" r="3"/></g>
      </g>
    </svg>
  </button>`;
}

function wireBulb(btn) {
  let startY = null, pulled = 0, dragged = false, swingRaf = null;
  function startSwing(amplitude) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (swingRaf) cancelAnimationFrame(swingRaf);
    const t0 = performance.now();
    const omega = (2 * Math.PI) / 450;
    const lambda = 0.0021;
    function frame(now) {
      const t = now - t0;
      const angle = amplitude * Math.exp(-lambda * t) * Math.sin(omega * t);
      btn.style.setProperty("--swing", angle.toFixed(2) + "deg");
      if (Math.abs(angle) > 0.04 || t < 250) swingRaf = requestAnimationFrame(frame);
      else { btn.style.setProperty("--swing", "0deg"); swingRaf = null; }
    }
    swingRaf = requestAnimationFrame(frame);
  }
  function setPull(px) {
    btn.style.setProperty("--pull", px + "px");
    btn.style.setProperty("--stretch", 1 + px / 20);
  }
  function release() {
    btn.classList.add("spring");
    setPull(0);
    setTimeout(() => btn.classList.remove("spring"), 400);
  }
  function flip() { efaSetTheme(efaTheme() === "day" ? "night" : "day"); }
  btn.addEventListener("pointerdown", (e) => {
    if (swingRaf) { cancelAnimationFrame(swingRaf); swingRaf = null; }
    btn.style.setProperty("--swing", "0deg");
    startY = e.clientY; pulled = 0; dragged = false;
    btn.classList.remove("spring");
    try { btn.setPointerCapture(e.pointerId); } catch (err) {}
  });
  btn.addEventListener("pointermove", (e) => {
    if (startY === null) return;
    pulled = Math.max(0, Math.min(14, e.clientY - startY));
    if (pulled > 3) dragged = true;
    setPull(dragged ? pulled : 0);
  });
  let suppressClick = false;
  btn.addEventListener("pointerup", () => {
    suppressClick = true;
    if (startY === null) return;
    const shouldFlip = pulled >= 7 || !dragged;
    const amp = 13 + Math.min(11, pulled * 0.8);
    startY = null;
    release();
    startSwing(amp);
    if (shouldFlip) setTimeout(flip, 90);
  });
  btn.addEventListener("pointercancel", () => { startY = null; release(); });
  btn.addEventListener("click", () => {
    if (suppressClick) { suppressClick = false; return; }
    startSwing(14);
    flip();
  });
}
function wireBulbs() { document.querySelectorAll(".efa-bulb").forEach(wireBulb); }


/* ================================================================
   Animated logout — glowing liquid transition (owner design,
   2026-11-04): three luminous streams in the site's own colors
   (white / neon / black) pour from the top of the page — over the
   page itself, no backdrop — braid around each other at the
   center, tighten into a knot, and only then does the login page
   load. Palettes are tuned per theme so the colors stay luminous
   and harmonious in BOTH modes: night uses the raw neon with a
   light halo on the black stream; day uses the site's day-neon
   (#4c8a06) and turns the white stream's glow into a soft shadow
   so it still reads on the light page.
   The real logout fires IMMEDIATELY on click (Auth.beginLogout:
   server revoke + storage clear) — the animation is a curtain
   and can never trap the user: a tap skips it, a 2.9s hard cap
   forces navigation, reduced-motion and any engine error fall
   back to the instant logout. Session expiry (forceReauth in
   api.js) never plays it.
   ================================================================ */
let efaLoRunning = false;
function efaAnimatedLogout() {
  if (efaLoRunning) return;
  const instant = () => {
    try { Auth.logout(); } catch (e) { location.href = "/auth.html"; }
  };
  if (typeof Auth === "undefined" || typeof Auth.beginLogout !== "function") { instant(); return; }
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) { instant(); return; }
  efaLoRunning = true;
  Auth.beginLogout();
  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    location.href = "/auth.html";
  };
  const hardCap = setTimeout(finish, 2900);
  try {
    efaPlayLogoutTransition(() => { clearTimeout(hardCap); finish(); });
  } catch (e) {
    clearTimeout(hardCap);
    finish();
  }
}

function efaPlayLogoutTransition(onDone) {
  const day = (typeof efaTheme === "function" ? efaTheme() : "night") === "day";
  const PAL = day
    ? { w: ["#ffffff", "#5a6e50", 0.8, 0.5], n: ["#4c8a06", "#4c8a06", 1, 0.85], b: ["#101410", "#101410", 0.5, 0.35] }
    : { w: ["#ffffff", "#ffffff", 1, 0.9], n: ["#a3ff12", "#a3ff12", 1, 0.9], b: ["#101410", "#cfe8d8", 1, 0.85] };
  const NS = "http://www.w3.org/2000/svg";
  const ov = document.createElement("div");
  ov.className = "efa-lo";
  ov.setAttribute("aria-hidden", "true");
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");
  svg.style.position = "absolute";
  const defs = document.createElementNS(NS, "defs");
  [["w", PAL.w], ["n", PAL.n], ["b", PAL.b]].forEach(([k, pal]) => {
    const f = document.createElementNS(NS, "filter");
    f.setAttribute("id", "efa-goo-" + k);
    f.setAttribute("x", "-40%"); f.setAttribute("y", "-40%");
    f.setAttribute("width", "180%"); f.setAttribute("height", "180%");
    f.innerHTML =
      '<feGaussianBlur in="SourceGraphic" stdDeviation="10" result="b"/>' +
      '<feColorMatrix in="b" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -11" result="g"/>' +
      '<feDropShadow in="g" dx="0" dy="0" stdDeviation="5" flood-color="' + pal[1] + '" flood-opacity="' + pal[2] + '" result="s1"/>' +
      '<feDropShadow in="s1" dx="0" dy="0" stdDeviation="13" flood-color="' + pal[1] + '" flood-opacity="' + pal[3] + '"/>';
    defs.appendChild(f);
  });
  svg.appendChild(defs);
  ov.appendChild(svg);
  const layers = {};
  [["w", "w"], ["n", "n"], ["b", "b"]].forEach(([k]) => {
    const d = document.createElement("div");
    d.className = "efa-lo-goo";
    d.style.filter = "url(#efa-goo-" + k + ")";
    ov.appendChild(d);
    layers[k] = d;
  });
  document.body.appendChild(ov);
  requestAnimationFrame(() => ov.classList.add("on"));

  const STREAMS = [
    { key: "w", color: PAL.w[0], fromX: 0.22, head: 54, delay: 0,   phase: 0.0, orbitA: -Math.PI / 2 },
    { key: "n", color: PAL.n[0], fromX: 0.50, head: 64, delay: 110, phase: 2.1, orbitA: Math.PI / 6 },
    { key: "b", color: PAL.b[0], fromX: 0.78, head: 54, delay: 220, phase: 4.2, orbitA: Math.PI * 5 / 6 }
  ];
  const TRAILS = 10, DESCENT = 880, FADE_START = 1900, TOTAL = 2200;
  const W = window.innerWidth, H = window.innerHeight;
  const CX = W * 0.5, CY = H * 0.46;
  const clamp01 = (v) => v < 0 ? 0 : v > 1 ? 1 : v;
  const easeInQuad = (q) => q * q;
  const easeOutCubic = (q) => 1 - Math.pow(1 - q, 3);
  const easeInOut = (q) => q < .5 ? 2 * q * q : 1 - Math.pow(-2 * q + 2, 2) / 2;

  const units = [];
  STREAMS.forEach((st) => {
    const mk = (size) => {
      const d = document.createElement("div");
      d.className = "efa-lo-blob";
      d.style.width = size + "px";
      d.style.height = size + "px";
      d.style.background = st.color;
      d._r = size / 2;
      layers[st.key].appendChild(d);
      return d;
    };
    units.push({ el: mk(st.head), stream: st, kind: "head", born: st.delay });
    for (let i = 1; i <= TRAILS; i++) {
      units.push({ el: mk(st.head * (0.88 - i * 0.047)), stream: st, kind: "trail", lagMs: i * 42, born: st.delay });
    }
  });
  const place = (elm, x, y, s) => {
    elm.style.transform = "translate(" + (x - elm._r) + "px," + (y - elm._r) + "px) scale(" + s + ")";
  };
  function orbitAngle(ot) {
    if (ot <= 0) return 0;
    if (ot < 700) return ot * 0.0035 + 0.5 * (0.007 / 700) * ot * ot;
    return 4.9 + (ot - 700) * 0.0105;
  }
  function streamPath(st, t) {
    const tA = st.delay + DESCENT;
    if (t <= tA) {
      const q = clamp01((t - st.delay) / DESCENT);
      return {
        x: st.fromX * W + (CX - st.fromX * W) * easeInOut(q) + Math.sin(q * 5.2 + st.phase) * 20 * (1 - q),
        y: -70 + (CY + 70) * easeInQuad(q),
        p: q
      };
    }
    const ot = t - tA;
    let r = 64 * easeOutCubic(clamp01(ot / 240));
    if (ot > 640) r = 64 - 42 * easeInOut(clamp01((ot - 640) / 300));
    const ang = st.orbitA + orbitAngle(ot);
    return { x: CX + r * Math.cos(ang), y: CY + r * Math.sin(ang) * 0.92, p: 1 };
  }
  function render(t) {
    STREAMS.forEach((st) => { st._head = streamPath(st, t); });
    const shrink = t > 1780 ? Math.max(0.55, 1 - (t - 1780) / 300 * 0.45) : 1;
    units.forEach((u) => {
      if (u.kind === "head") {
        if (t < u.born) { place(u.el, u.stream._head.x, -140, 0.01); return; }
        place(u.el, u.stream._head.x, u.stream._head.y, shrink);
      } else {
        const tp = streamPath(u.stream, t - u.lagMs);
        if (t < u.born || tp.p <= 0) { place(u.el, tp.x, -140, 0.01); return; }
        place(u.el, tp.x, tp.y, shrink);
      }
    });
    ov.style.opacity = t > FADE_START ? String(Math.max(0, 1 - (t - FADE_START) / 300)) : "";
  }

  let raf = 0, startAt = 0, stopped = false;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    cancelAnimationFrame(raf);
    ov.remove();
    onDone();
  };
  ov.addEventListener("pointerdown", stop);
  const frame = (now) => {
    const t = now - startAt;
    render(t);
    if (t >= TOTAL) { stop(); return; }
    raf = requestAnimationFrame(frame);
  };
  startAt = performance.now();
  raf = requestAnimationFrame(frame);
}

function renderLiquidNav() {
  const activeKey = lqActiveKey();
  const brand = `<a class="lq-brand" href="/"><span class="brand-badge"><img class="brand-logo" src="/shared/logo-symbol.webp" alt="" /></span>eFootball Arena</a>`;

  const header = document.createElement("header");
  header.className = "lq-header";
  header.innerHTML = `
    ${brand}
    <div class="lq-zone">
      <ul>${LQ_ITEMS.map((i) => lqItemHtml(i, activeKey)).join("")}</ul>
      <div class="lq-indicator"></div>
    </div>
    <div class="lq-utils">
      ${bulbToggleHtml(false)}
      ${lqLanguageHtml()}
      <button class="lq-logout" type="button" aria-label="خروج" title="خروج"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 21h4a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-4"/><path d="m8 17-5-5 5-5"/><path d="M3 12h12"/></svg></button>
    </div>`;

  const topbar = document.createElement("header");
  topbar.className = "lq-topbar";
  topbar.innerHTML = `
    ${brand}
    <nav class="lq-top-links">
      <a href="/app/community.html" class="${activeKey === "community" ? "active" : ""}">المجتمع</a>
      <a href="/app/ratings.html" class="${activeKey === "ratings" ? "active" : ""}">التصنيف</a>
    </nav>
    <div class="lq-sp"></div>
    ${bulbToggleHtml(true)}
    ${lqLanguageHtml()}
    <button class="lq-logout" type="button" aria-label="خروج" title="خروج"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 21h4a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-4"/><path d="m8 17-5-5 5-5"/><path d="M3 12h12"/></svg></button>`;

  const dock = document.createElement("div");
  dock.className = "lq-dock";
  dock.innerHTML = `
    <div class="lq-navigation">
      <ul>${LQ_ITEMS.filter((i) => LQ_DOCK_KEYS.includes(i.key)).map((i) => lqItemHtml(i, activeKey)).join("")}</ul>
      <div class="lq-indicator"></div>
    </div>`;

  document.body.prepend(dock);
  document.body.prepend(topbar);
  document.body.prepend(header);
  document.body.classList.add("lq-on");

  lqWireIndicator(header.querySelector(".lq-zone"), true);
  lqWireIndicator(dock.querySelector(".lq-navigation"), false);
  wireBulbs();

  document.querySelectorAll(".lq-logout").forEach((b) =>
    b.addEventListener("click", () => efaAnimatedLogout()));

  const selects = Array.from(document.querySelectorAll(".nav-language"));
  selects.forEach((sel) => {
    sel.value = i18n.current();
    sel.addEventListener("change", () => {
      selects.forEach((s) => { s.value = sel.value; });
      i18n.setLanguage(sel.value);
    });
  });
  i18n.apply();

  if (typeof apiFetch === "function") {
    const updateInviteBadge = (isRetry) => {
      apiFetch("/invites/count").then((r) => {
        document.querySelectorAll(".nav-invite-badge").forEach((badge) => {
          if (r && r.pending_received > 0) { badge.textContent = r.pending_received; badge.hidden = false; }
          else { badge.hidden = true; }
        });
      }).catch(() => { if (!isRetry) setTimeout(() => updateInviteBadge(true), 3000); });
    };
    updateInviteBadge(false);
    const badgeTimer = setInterval(() => updateInviteBadge(true), 30000);
    window.addEventListener("pagehide", () => clearInterval(badgeTimer));
  }
}

function renderClassicNav() {
  const nav = document.createElement("div");
  nav.className = "navbar";
  const logged = Auth.loggedIn();
  const currentPath = location.pathname;
  nav.innerHTML = `
    <a class="brand" href="/"><span class="brand-badge"><img class="brand-logo" src="/shared/logo-symbol.webp" alt="" /></span>eFootball Arena</a>
    <button class="nav-toggle" id="nav-toggle" type="button" aria-expanded="false" aria-controls="nav-menu" aria-label="فتح قائمة التنقل">☰</button>
    <div class="nav-menu" id="nav-menu">
    <div class="spacer"></div>
    <a class="nav-link ${currentPath.endsWith("/tournaments.html") ? "active" : ""}" href="/app/tournaments.html">البطولات</a>
    ${logged ? `
      <a class="nav-link ${currentPath.endsWith("/dashboard.html") ? "active" : ""}" href="/app/dashboard.html">لوحتي</a>
      <a class="nav-link ${currentPath.endsWith("/ratings.html") ? "active" : ""}" href="/app/ratings.html">التصنيف</a>
      <a class="nav-link ${currentPath.endsWith("/community.html") ? "active" : ""}" href="/app/community.html">المجتمع</a>
      <a class="nav-link ${currentPath.endsWith("/arena-star.html") ? "active" : ""}" href="/app/arena-star.html">أرينا ستار</a>
      <a class="nav-bell" href="/app/invites.html" aria-label="الدعوات" title="الدعوات">🔔<span class="nav-badge" id="nav-invite-badge" hidden></span></a>
      <button class="user-chip" id="nav-user" type="button" title="لوحة اللاعب">⚽ <span>حسابي</span></button>
      <button class="btn btn-ghost" type="button" id="nav-logout" style="padding:8px 10px" aria-label="خروج" title="خروج"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 21h4a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-4"/><path d="m8 17-5-5 5-5"/><path d="M3 12h12"/></svg></button>
    ` : `
      <a class="btn btn-primary" href="/auth.html" style="padding:8px 18px">دخول / تسجيل</a>
    `}
    ${bulbToggleHtml(false)}
    <label class="language-picker" title="اللغة">
      <span class="lang-globe" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg></span>
      <span class="sr-only">اللغة</span>
      <select id="nav-language" aria-label="اللغة">
        <option value="ar">AR</option>
        <option value="fr">FR</option>
        <option value="en">EN</option>
      </select>
    </label>
    </div>
  `;
  document.body.prepend(nav);
  wireBulbs();
  const menu = nav.querySelector("#nav-menu");
  const toggle = nav.querySelector("#nav-toggle");
  const closeMenu = () => {
    nav.classList.remove("menu-open");
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "فتح قائمة التنقل");
  };
  let menuOpenScrollY = null;
  toggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("menu-open");
    toggle.setAttribute("aria-expanded", String(isOpen));
    toggle.setAttribute("aria-label", isOpen ? "إغلاق قائمة التنقل" : "فتح قائمة التنقل");
    menuOpenScrollY = isOpen ? window.scrollY : null;
  });
  window.addEventListener("scroll", () => {
    if (menuOpenScrollY === null || !nav.classList.contains("menu-open")) return;
    if (Math.abs(window.scrollY - menuOpenScrollY) > 40) { closeMenu(); menuOpenScrollY = null; }
  }, { passive: true });
  menu.querySelectorAll("a, button").forEach((elm) => elm.addEventListener("click", closeMenu));
  window.addEventListener("pageshow", (e) => { if (e.persisted) closeMenu(); });
  document.addEventListener("click", (e) => {
    if (nav.classList.contains("menu-open") && !nav.contains(e.target)) closeMenu();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenu(); });
  nav.querySelector("#nav-logout")?.addEventListener("click", () => efaAnimatedLogout());
  nav.querySelector("#nav-user")?.addEventListener("click", () => location.href = "/app/dashboard.html");
  const language = nav.querySelector("#nav-language");
  language.value = i18n.current();
  language.addEventListener("change", () => i18n.setLanguage(language.value));
  i18n.apply();
  if (logged && typeof apiFetch === "function") {
    const bellStyle = document.createElement("style");
    bellStyle.textContent = ".nav-bell{position:relative;font-size:1.05rem;text-decoration:none;padding:6px 4px;line-height:1}.nav-badge{position:absolute;top:-3px;inset-inline-end:-7px;background:#e5484d;color:#fff;border-radius:999px;font-size:.62rem;font-weight:800;min-width:17px;height:17px;display:grid;place-items:center;padding:0 4px}";
    document.head.appendChild(bellStyle);
    const updateInviteBadge = (isRetry) => {
      apiFetch("/invites/count").then((r) => {
        const badge = nav.querySelector("#nav-invite-badge");
        if (!badge) return;
        if (r && r.pending_received > 0) { badge.textContent = r.pending_received; badge.hidden = false; }
        else { badge.hidden = true; }
      }).catch(() => { if (!isRetry) setTimeout(() => updateInviteBadge(true), 3000); });
    };
    updateInviteBadge(false);
    const badgeTimer = setInterval(() => updateInviteBadge(true), 30000);
    window.addEventListener("pagehide", () => clearInterval(badgeTimer));
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (Auth.loggedIn()) renderLiquidNav();
  else renderClassicNav();
});
