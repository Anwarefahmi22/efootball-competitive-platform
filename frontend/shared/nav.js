function renderNav() {
  const nav = document.createElement("div");
  nav.className = "navbar";
  const logged = Auth.loggedIn();
  nav.innerHTML = `
    <a class="brand" href="/index.html">eFootball Arena</a>
    <div class="spacer"></div>
    <a class="nav-link" href="/app/tournaments.html">البطولات</a>
    ${logged ? `
      <a class="nav-link" href="/app/dashboard.html">لوحتي</a>
      <a class="nav-link" href="/app/ratings.html">التصنيف</a>
      <div class="user-chip" id="nav-user" title="لوحة اللاعب">⚽ <span>حسابي</span></div>
      <a class="btn btn-ghost" href="#" id="nav-logout" style="padding:8px 14px">خروج</a>
    ` : `
      <a class="btn btn-primary" href="/auth.html" style="padding:8px 18px">دخول / تسجيل</a>
    `}
  `;
  document.body.prepend(nav);
  nav.querySelector("#nav-logout")?.addEventListener("click", (e) => { e.preventDefault(); Auth.logout(); });
  nav.querySelector("#nav-user")?.addEventListener("click", () => location.href = "/app/dashboard.html");
}
document.addEventListener("DOMContentLoaded", renderNav);
