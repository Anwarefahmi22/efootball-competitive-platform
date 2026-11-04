/* eFootball Arena — presence (migration 024).
   Two jobs:
   1) Heartbeat: while a logged-in page is actually visible, ping
      POST /users/me/heartbeat every 45s so the server can stamp
      last_seen and accrue real activity time. Hidden tabs stay
      silent (an abandoned tab must not fake activity), and the
      timer stops on pagehide so bfcache restores don't leak it.
   2) Shared render helpers for the online dot, the presence line
      (online / last seen) and the activity-time format, used by
      Arena Star cards, the profile page and the invites inbox. */
(function () {
  if (window.Auth && Auth.loggedIn()) {
    let timer = null;
    const beat = () => {
      if (document.visibilityState !== "visible") return;
      fetch(API_BASE + "/users/me/heartbeat", {
        method: "POST",
        headers: { Authorization: "Bearer " + Auth.token() },
        keepalive: true,
      }).catch(() => {});
    };
    const start = () => {
      if (timer) return;
      beat();
      timer = setInterval(beat, 45000);
    };
    const stop = () => {
      if (timer) clearInterval(timer);
      timer = null;
    };
    start();
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") beat();
    });
    window.addEventListener("pagehide", stop);
    window.addEventListener("pageshow", start);
  }

  window.presenceDotHtml = (online) =>
    `<span class="presence-dot ${online ? "on" : "off"}" aria-hidden="true"></span>`;

  // A presence line for a payload carrying {is_online, last_seen_at}.
  // The label is a static dictionary string (auto-translated by the
  // i18n observer); the timestamp goes through Intl so it is already
  // locale-correct in all three languages.
  window.presenceLineHtml = (p) => {
    if (p && p.is_online) {
      return `<span class="presence-line">${window.presenceDotHtml(true)}<span>متصل الآن</span></span>`;
    }
    if (p && p.last_seen_at) {
      const lang = window.i18n ? i18n.current() : "ar";
      const when = new Intl.DateTimeFormat(lang === "ar" ? "ar-EG" : lang, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(p.last_seen_at));
      return `<span class="presence-line">${window.presenceDotHtml(false)}<span>آخر ظهور</span> <span class="presence-when">${when}</span></span>`;
    }
    return `<span class="presence-line">${window.presenceDotHtml(false)}<span>غير متصل</span></span>`;
  };

  // Accumulated activity seconds -> compact human duration.
  window.fmtActiveTime = (seconds) => {
    const s = Math.max(0, Math.floor(seconds || 0));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h} س ${m} د`;
    if (m > 0) return `${m} دقيقة`;
    return "أقل من دقيقة";
  };
})();
