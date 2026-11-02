function renderNav() {
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
  toggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("menu-open");
    toggle.setAttribute("aria-expanded", String(isOpen));
    toggle.setAttribute("aria-label", isOpen ? "إغلاق قائمة التنقل" : "فتح قائمة التنقل");
  });
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
    // The badge must not depend on a page reload: an invite can arrive
    // while a page sits open, so poll. One quiet retry covers a dropped
    // first fetch on a slow mobile connection.
    const updateInviteBadge = (isRetry) => {
      apiFetch("/invites/count").then((r) => {
        const badge = nav.querySelector("#nav-invite-badge");
        if (!badge) return;
        if (r && r.pending_received > 0) { badge.textContent = r.pending_received; badge.hidden = false; }
        else { badge.hidden = true; }
      }).catch(() => { if (!isRetry) setTimeout(() => updateInviteBadge(true), 3000); });
    };
    updateInviteBadge(false);
    setInterval(() => updateInviteBadge(true), 30000);
  }
}
document.addEventListener("DOMContentLoaded", renderNav);
