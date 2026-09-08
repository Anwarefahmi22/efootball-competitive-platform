/* eFootball Arena — shared UI helpers (RTL) */
// In production the API serves the frontend itself, so /api/v1 lives on the
// same origin. The classic local dev setup (nginx on :8080) still targets
// localhost:8000 explicitly.
const API_BASE =
  location.port === "8080" ? "http://localhost:8000/api/v1" : location.origin + "/api/v1";

const TOKEN_KEY = "efa_access_token";
const REFRESH_KEY = "efa_refresh_token";
const USER_KEY = "efa_user_id";

const Auth = {
  save(tokenPair) {
    localStorage.setItem(TOKEN_KEY, tokenPair.access_token);
    localStorage.setItem(REFRESH_KEY, tokenPair.refresh_token);
  },
  token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  loggedIn() {
    return !!localStorage.getItem(TOKEN_KEY);
  },
  logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    location.href = "/auth.html";
  },
};

async function apiFetch(path, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  const token = Auth.token();
  if (token && !options.noAuth) headers["Authorization"] = "Bearer " + token;

  let res;
  try {
    res = await fetch(API_BASE + path, Object.assign({}, options, { headers }));
  } catch (e) {
    throw { detail: "تعذر الاتصال بالخادم. تأكد من تشغيل Docker (localhost:8000)." };
  }

  if (res.status === 401 && !options.noAuth) {
    // try refresh once
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (refresh) {
      const r = await fetch(API_BASE + "/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (r.ok) {
        const pair = { access_token: (await r.json()).access_token, refresh_token: refresh };
        Auth.save(pair);
        headers["Authorization"] = "Bearer " + pair.access_token;
        res = await fetch(API_BASE + path, Object.assign({}, options, { headers }));
      }
    }
  }

  if (!res.ok) {
    let detail = "خطأ غير معروف (" + res.status + ")";
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body);
    } catch (_) {}
    throw { status: res.status, detail };
  }
  return res.json();
}

function toast(message, type = "info") {
  let holder = document.getElementById("efa-toast");
  if (!holder) {
    holder = document.createElement("div");
    holder.id = "efa-toast";
    document.body.appendChild(holder);
  }
  const t = document.createElement("div");
  t.className = "toast " + type;
  t.textContent = message;
  holder.appendChild(t);
  setTimeout(() => t.remove(), 4200);
}

function el(id) {
  return document.getElementById(id);
}

function statusLabel(status) {
  const map = {
    draft: "مسودة",
    open: "مفتوح للتسجيل",
    full: "مكتمل العدد",
    running: "جارية",
    completed: "منتهية",
    cancelled: "ملغاة",
  };
  return map[status] || status;
}

async function requireAuthOrRedirect() {
  if (!Auth.loggedIn()) {
    location.href = "/auth.html?next=" + encodeURIComponent(location.pathname);
    return false;
  }
  return true;
}
