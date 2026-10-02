/**
 * GrievanceAI — Shared utilities, API client, auth helpers.
 */
const API = "/api";

// ---- Auth ----------------------------------------------------------------
const Auth = {
  getToken() { return localStorage.getItem("grievance_token"); },
  getUser() {
    const u = localStorage.getItem("grievance_user");
    return u ? JSON.parse(u) : null;
  },
  set(token, user) {
    localStorage.setItem("grievance_token", token);
    localStorage.setItem("grievance_user", JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem("grievance_token");
    localStorage.removeItem("grievance_user");
  },
  isLoggedIn() { return !!this.getToken(); },
  isAdmin() {
    const u = this.getUser();
    return u && u.role === "admin";
  },
};

async function api(path, options = {}) {
  const token = Auth.getToken();
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { headers, ...options });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ---- Helpers --------------------------------------------------------------
function badgeClass(priority) {
  return `badge badge-${priority.toLowerCase()}`;
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function showLoader(el, show = true) {
  if (show) el.innerHTML = '<span class="loader"></span>';
  else el.innerHTML = "";
}

// ---- Navbar user state ---------------------------------------------------
function updateNavbarAuth() {
  const user = Auth.getUser();
  const nav = document.querySelector(".navbar-links");
  if (!nav) return;
  const existing = nav.querySelector(".auth-section");
  if (existing) existing.remove();
  const section = document.createElement("div");
  section.className = "auth-section";
  section.style.cssText = "margin-left:auto; display:flex; align-items:center; gap:8px;";
  if (user) {
    section.innerHTML = `
      <span style="color:rgba(255,255,255,0.85); font-size:0.82rem; font-weight:600;">
        ${user.role === "admin" ? "👑" : "👤"} ${user.full_name}
      </span>
      <button class="btn btn-secondary btn-sm" onclick="logout()" style="background:rgba(255,255,255,0.15); color:#fff; border:1px solid rgba(255,255,255,0.3);">Logout</button>
    `;
  } else {
    section.innerHTML = `
      <a href="/login" class="btn btn-sm" style="background:rgba(255,255,255,0.15); color:#fff; border:1px solid rgba(255,255,255,0.3); padding:8px 16px; border-radius:8px; font-weight:600; text-decoration:none; font-size:0.82rem;">Login / Register</a>
    `;
  }
  nav.appendChild(section);
}

function logout() {
  Auth.clear();
  window.location.href = "/login";
}

// Call on page load
document.addEventListener("DOMContentLoaded", () => {
  if (typeof updateNavbarAuth === "function") updateNavbarAuth();
  // Role-based access control on admin pages
  const path = window.location.pathname;
  const adminPages = ["/dashboard", "/queue", "/analytics"];
  if (adminPages.includes(path)) {
    const user = Auth.getUser();
    if (!user) {
      window.location.href = "/login";
      return;
    }
    if (user.role !== "admin") {
      alert("Access denied: Admin only. Redirecting to My Complaints.");
      window.location.href = "/my-complaints";
      return;
    }
  }
});
