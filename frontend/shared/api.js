/* eFootball Arena — shared UI helpers (RTL) */
// In production the API serves the frontend itself, so /api/v1 lives on the
// same origin. The classic local dev setup (nginx on :8080) still targets
// localhost:8000 explicitly.
const API_BASE =
  location.port === "8080" ? "http://localhost:8000/api/v1" : location.origin + "/api/v1";
const API_TIMEOUT_MS = 12000;

const TOKEN_KEY = "efa_access_token";
const REFRESH_KEY = "efa_refresh_token";
const USER_KEY = "efa_user_id";
let refreshPromise = null;

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

function apiError(status, detail, code = "api_error") {
  return { status, detail, code };
}

async function readResponseBody(res) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (_) {
    return text;
  }
}

async function fetchWithTimeout(url, options) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    return await fetch(url, Object.assign({}, options, { signal: controller.signal }));
  } catch (error) {
    if (error.name === "AbortError") {
      throw apiError(408, "انتهت مهلة الاتصال بالخادم. حاول مرة أخرى.", "timeout");
    }
    throw apiError(0, "تعذر الاتصال بالخادم. تأكد من تشغيل Docker (localhost:8000).", "network");
  } finally {
    clearTimeout(timeout);
  }
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  if (!refreshPromise) {
    refreshPromise = fetchWithTimeout(API_BASE + "/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    }).then(async (res) => {
      if (!res.ok) return false;
      const body = await readResponseBody(res);
      if (!body || !body.access_token) return false;
      Auth.save({ access_token: body.access_token, refresh_token: refresh });
      return true;
    }).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  if (!(options.body instanceof FormData) && options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const token = Auth.token();
  if (token && !options.noAuth) headers["Authorization"] = "Bearer " + token;

  const requestOptions = Object.assign({}, options, { headers });
  delete requestOptions.noAuth;
  delete requestOptions.noBody;
  let res = await fetchWithTimeout(API_BASE + path, requestOptions);

  if (res.status === 401 && !options.noAuth) {
    if (await refreshAccessToken()) {
      headers["Authorization"] = "Bearer " + Auth.token();
      res = await fetchWithTimeout(API_BASE + path, Object.assign({}, requestOptions, { headers }));
    }
  }

  if (!res.ok) {
    const body = await readResponseBody(res);
    const detail = body && typeof body === "object" && body.detail
      ? (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail))
      : (typeof body === "string" && body ? body : "خطأ غير معروف (" + res.status + ")");
    throw apiError(res.status, detail, res.status === 401 ? "unauthorized" : "api_error");
  }
  return res.status === 204 ? null : readResponseBody(res);
}

async function apiFetchFile(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  const token = Auth.token();
  if (token && !options.noAuth) headers["Authorization"] = "Bearer " + token;
  const requestOptions = Object.assign({}, options, { headers });
  delete requestOptions.noAuth;
  let res = await fetchWithTimeout(API_BASE + path, requestOptions);
  if (res.status === 401 && !options.noAuth && await refreshAccessToken()) {
    headers["Authorization"] = "Bearer " + Auth.token();
    res = await fetchWithTimeout(API_BASE + path, Object.assign({}, requestOptions, { headers }));
  }
  if (!res.ok) {
    const body = await readResponseBody(res);
    const detail = body && typeof body === "object" && body.detail ? body.detail : "تعذر تحميل الملف.";
    throw apiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail), "api_error");
  }
  return res.blob();
}

const api = {
  get(path, options = {}) {
    return apiFetch(path, Object.assign({}, options, { method: "GET" }));
  },
  post(path, body, options = {}) {
    return apiFetch(path, Object.assign({}, options, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }));
  },
  put(path, body, options = {}) {
    return apiFetch(path, Object.assign({}, options, {
      method: "PUT",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }));
  },
  delete(path, options = {}) {
    return apiFetch(path, Object.assign({}, options, { method: "DELETE" }));
  },
};

function toast(message, type = "info") {
  let holder = document.getElementById("efa-toast");
  if (!holder) {
    holder = document.createElement("div");
    holder.id = "efa-toast";
    holder.setAttribute("aria-live", "polite");
    holder.setAttribute("role", "status");
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
    registration_open: "مفتوح للتسجيل",
    registration_closed: "مغلق",
    in_progress: "جارية",
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
