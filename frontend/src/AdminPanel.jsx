import { useEffect, useState } from "react";
import "./AdminPanel.css";

const API = "http://127.0.0.1:8000/api/admin";
// The login page (written by the teammate) should store the access token under this key.
const TOKEN_KEY = "access";

function authHeaders() {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...options.headers,
    },
  });

  if (response.status === 401 || response.status === 403) {
    throw new Error("AUTH");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const firstFieldError = Object.values(body).flat()[0];
    throw new Error(body.detail || (typeof firstFieldError === "string" ? firstFieldError : "") || "Request failed.");
  }
  return response.status === 204 ? null : response.json();
}

const EDIT_FIELDS = [
  ["name", "Name"],
  ["category", "Category"],
  ["area", "Area"],
  ["address", "Address"],
  ["average_price", "Average price"],
  ["description", "Description"],
];

const USER_FIELDS = [
  ["username", "Username"],
  ["email", "Email"],
  ["full_name", "Full name"],
  ["location", "Location"],
  ["bio", "Bio"],
];

const GENDERS = [
  ["male", "Male"],
  ["female", "Female"],
  ["non_binary", "Non-binary"],
  ["other", "Other"],
  ["prefer_not_to_say", "Prefer not to say"],
];

function AdminPanel() {
  const [tab, setTab] = useState("places");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [needsLogin, setNeedsLogin] = useState(false);
  const [tokenInput, setTokenInput] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [draft, setDraft] = useState(null);
  const [userDraft, setUserDraft] = useState(null);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      const params = new URLSearchParams();
      if (search.trim()) params.set("search", search.trim());
      if (tab === "places" && statusFilter) params.set("status", statusFilter);

      try {
        const [list, summary] = await Promise.all([
          request(`/${tab}/?${params.toString()}`),
          request("/stats/"),
        ]);
        if (cancelled) return;
        setItems(list);
        setStats(summary);
        setNeedsLogin(false);
      } catch (err) {
        if (cancelled) return;
        if (err.message === "AUTH") {
          setNeedsLogin(true);
        } else {
          setError("Could not load data. Check that Django is running.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    const timeout = setTimeout(load, 250);
    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [tab, search, statusFilter, reloadKey]);

  const reload = () => setReloadKey((key) => key + 1);

  async function act(path, options, confirmText) {
    if (confirmText && !window.confirm(confirmText)) return;
    try {
      await request(path, options);
      reload();
    } catch (err) {
      setError(err.message === "AUTH" ? "Administrator access required." : err.message);
    }
  }

  async function savePlace(event) {
    event.preventDefault();
    const body = {};
    EDIT_FIELDS.forEach(([key]) => {
      if (draft[key] !== undefined) body[key] = draft[key] === "" && key === "average_price" ? null : draft[key];
    });
    await act(`/places/${draft.id}/`, { method: "PATCH", body: JSON.stringify(body) });
    setDraft(null);
  }

  async function saveUser(event) {
    event.preventDefault();
    setFormError("");
    const body = {};
    [...USER_FIELDS.map(([key]) => key), "gender"].forEach((key) => {
      body[key] = userDraft[key] ?? "";
    });
    try {
      await request(`/users/${userDraft.id}/`, { method: "PATCH", body: JSON.stringify(body) });
      setUserDraft(null);
      reload();
    } catch (err) {
      setFormError(err.message === "AUTH" ? "Administrator access required." : err.message);
    }
  }

  function saveToken() {
    localStorage.setItem(TOKEN_KEY, tokenInput.trim());
    setTokenInput("");
    reload();
  }

  const moderation = stats?.moderation_enabled;

  return (
    <section className="admin">
      <header className="admin-header">
        <div>
          <p className="eyebrow">ADMINISTRATION</p>
          <h1>KotoLagbe admin</h1>
        </div>
        <a className="back-link" href="/">Back to site</a>
      </header>

      {needsLogin && (
        <section className="login-box">
          <p>Administrator access required. Sign in as a staff user, or paste an access token for testing.</p>
          <div className="login-row">
            <input
              type="password"
              placeholder="Access token"
              aria-label="Access token"
              value={tokenInput}
              onChange={(event) => setTokenInput(event.target.value)}
            />
            <button type="button" onClick={saveToken}>Use token</button>
          </div>
        </section>
      )}

      {!needsLogin && stats && (
        <section className="stats">
          <div><strong>{stats.places}</strong><span>Places</span></div>
          {moderation && <div><strong>{stats.pending_places}</strong><span>Pending approval</span></div>}
          <div><strong>{stats.users}</strong><span>Users</span></div>
          <div><strong>{stats.blocked_users}</strong><span>Blocked</span></div>
        </section>
      )}

      {!needsLogin && (
        <>
          <nav className="tabs">
            <button type="button" className={tab === "places" ? "active" : ""} onClick={() => setTab("places")}>Places</button>
            <button type="button" className={tab === "users" ? "active" : ""} onClick={() => setTab("users")}>Users</button>
          </nav>

          <div className="admin-filters">
            <input
              type="search"
              placeholder={tab === "places" ? "Search places or areas..." : "Search users..."}
              aria-label="Search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            {tab === "places" && moderation && (
              <select aria-label="Filter by status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            )}
          </div>

          {loading && <p className="message">Loading...</p>}
          {error && <p className="message error">{error}</p>}
          {!loading && !error && items.length === 0 && <p className="message">Nothing to show.</p>}

          {tab === "places" && items.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th><th>Category</th><th>Area</th>
                    {moderation && <th>Status</th>}
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((place) => (
                    <tr key={place.id}>
                      <td>{place.name}</td>
                      <td>{place.category}</td>
                      <td>{place.area}</td>
                      {moderation && <td><span className={`badge ${place.status}`}>{place.status}</span></td>}
                      <td className="actions">
                        {moderation && place.status !== "approved" && (
                          <button type="button" onClick={() => act(`/places/${place.id}/approve/`, { method: "POST" })}>Approve</button>
                        )}
                        {moderation && place.status !== "rejected" && (
                          <button type="button" onClick={() => act(`/places/${place.id}/reject/`, { method: "POST" })}>Reject</button>
                        )}
                        <button type="button" onClick={() => setDraft({ ...place })}>Edit</button>
                        <button
                          type="button"
                          className="danger"
                          onClick={() => act(`/places/${place.id}/`, { method: "DELETE" }, `Delete "${place.name}"?`)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === "users" && items.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Username</th><th>Full name</th><th>Email</th><th>Location</th><th>Role</th><th>Status</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {items.map((user) => (
                    <tr key={user.id}>
                      <td>{user.username}</td>
                      <td>{user.full_name}</td>
                      <td>{user.email}</td>
                      <td>{user.location}</td>
                      <td>{user.is_staff ? "Admin" : "Member"}</td>
                      <td><span className={`badge ${user.is_active ? "approved" : "rejected"}`}>{user.is_active ? "Active" : "Blocked"}</span></td>
                      <td className="actions">
                        {!user.is_staff && (
                          <button type="button" onClick={() => { setFormError(""); setUserDraft({ ...user }); }}>Edit</button>
                        )}
                        {!user.is_staff && (user.is_active ? (
                          <button type="button" onClick={() => act(`/users/${user.id}/block/`, { method: "POST" }, `Block ${user.username}?`)}>Block</button>
                        ) : (
                          <button type="button" onClick={() => act(`/users/${user.id}/unblock/`, { method: "POST" })}>Unblock</button>
                        ))}
                        {!user.is_staff && (
                          <button
                            type="button"
                            className="danger"
                            onClick={() => act(`/users/${user.id}/`, { method: "DELETE" }, `Delete account ${user.username}? This cannot be undone.`)}
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {draft && (
        <div className="modal-backdrop">
          <form className="modal" onSubmit={savePlace}>
            <h2>Edit place</h2>
            {EDIT_FIELDS.map(([key, label]) => (
              <label key={key}>
                {label}
                {key === "description" ? (
                  <textarea rows={3} value={draft[key] ?? ""} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} />
                ) : (
                  <input value={draft[key] ?? ""} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} />
                )}
              </label>
            ))}
            <div className="modal-actions">
              <button type="button" onClick={() => setDraft(null)}>Cancel</button>
              <button type="submit" className="primary">Save changes</button>
            </div>
          </form>
        </div>
      )}

      {userDraft && (
        <div className="modal-backdrop">
          <form className="modal" onSubmit={saveUser}>
            <h2>Edit user</h2>
            {USER_FIELDS.map(([key, label]) => (
              <label key={key}>
                {label}
                {key === "bio" ? (
                  <textarea rows={3} maxLength={300} value={userDraft[key] ?? ""} onChange={(event) => setUserDraft({ ...userDraft, [key]: event.target.value })} />
                ) : (
                  <input
                    type={key === "email" ? "email" : "text"}
                    required={key !== "location"}
                    value={userDraft[key] ?? ""}
                    onChange={(event) => setUserDraft({ ...userDraft, [key]: event.target.value })}
                  />
                )}
              </label>
            ))}
            <label>
              Gender
              <select value={userDraft.gender ?? "prefer_not_to_say"} onChange={(event) => setUserDraft({ ...userDraft, gender: event.target.value })}>
                {GENDERS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            {formError && <p className="form-error">{formError}</p>}
            <div className="modal-actions">
              <button type="button" onClick={() => setUserDraft(null)}>Cancel</button>
              <button type="submit" className="primary">Save changes</button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}

export default AdminPanel;
