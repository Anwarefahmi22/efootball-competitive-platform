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
      <span aria-hidden="true">文</span>
      <span class="sr-only">اللغة</span>
      <select class="nav-language" aria-label="اللغة">
        <option value="ar">العربية</option>
        <option value="fr">Français</option>
        <option value="en">English</option>
      </select>
    </label>`;
}

function lqWireIndicator(zone, hoverable) {
  const indicator = zone.querySelector(".lq-indicator");
  const list = zone.querySelector("ul");
  const items = Array.from(zone.querySelectorAll("li"));
  const activeLi = zone.querySelector("li.active");
  function place(li, animate) {
    if (!li) { indicator.style.opacity = "0"; return; }
    indicator.style.opacity = "1";
    if (!animate) indicator.classList.add("lq-noanim");
    indicator.style.transform = "translateX(" + (li.offsetLeft + li.offsetWidth / 2 - 35) + "px)";
    if (!animate) { void indicator.offsetWidth; indicator.classList.remove("lq-noanim"); }
  }
  place(activeLi, false);
  window.addEventListener("resize", () => place(zone.querySelector("li.active"), false));
  /* Late-arriving resources (the brand logo image, the Orbitron /
     IBM Plex webfonts) can still nudge the zone's geometry after the
     first placement. Correct with a short glide once they settle —
     the indicator then never sits wrong while the page finishes
     loading, and the correction reads as motion, not a jump. The
     logo's box is aspect-ratio-reserved in CSS, so in practice the
     font swap is the only mover. Skipped mid-hover: never yank the
     circle away from a preview. */
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

function renderLiquidNav() {
  const activeKey = lqActiveKey();
  const brand = `<a class="lq-brand" href="/"><img class="brand-logo" src="/shared/logo-symbol.webp" alt="" />eFootball Arena</a>`;

  const header = document.createElement("header");
  header.className = "lq-header";
  header.innerHTML = `
    ${brand}
    <div class="lq-zone">
      <ul>${LQ_ITEMS.map((i) => lqItemHtml(i, activeKey)).join("")}</ul>
      <div class="lq-indicator"></div>
    </div>
    <div class="lq-utils">
      ${lqLanguageHtml()}
      <button class="lq-logout" type="button">خروج</button>
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
    ${lqLanguageHtml()}
    <button class="lq-logout" type="button">خروج</button>`;

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

  document.querySelectorAll(".lq-logout").forEach((b) =>
    b.addEventListener("click", () => Auth.logout()));

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
    <a class="brand" href="/"><img class="brand-logo" src="/shared/logo-symbol.webp" alt="" />eFootball Arena</a>
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
      <button class="btn btn-ghost" type="button" id="nav-logout" style="padding:8px 14px">خروج</button>
    ` : `
      <a class="btn btn-primary" href="/auth.html" style="padding:8px 18px">دخول / تسجيل</a>
    `}
    <label class="language-picker" title="اللغة">
      <span aria-hidden="true">文</span>
      <span class="sr-only">اللغة</span>
      <select id="nav-language" aria-label="اللغة">
        <option value="ar">العربية</option>
        <option value="fr">Français</option>
        <option value="en">English</option>
      </select>
    </label>
    </div>
  `;
  document.body.prepend(nav);
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
  nav.querySelector("#nav-logout")?.addEventListener("click", () => Auth.logout());
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
