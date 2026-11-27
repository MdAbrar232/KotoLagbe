import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "./services/api.js";
import { useApiData } from "./services/useApiData.js";
import AdminModerationRows from "./AdminModerationRows.jsx";
import "./AdminPanel.css";

const contributionQueues = ["items", "item-prices", "reviews", "photos"];
const TABS = [
  ["places", "Places"], ["users", "Users"], ["locations", "Locations"],
  ["transport-modes", "Transport modes"], ["fares", "Fare moderation"], ["items", "Place items"],
  ["item-prices", "Item prices"], ["reviews", "Reviews"], ["photos", "Photos"], ["activity", "Activity log"],
];
const PLACE_FIELDS = [
  ["name", "Name", "text"], ["category", "Category", "text"], ["area", "Area", "text"],
  ["address", "Address", "text"], ["average_price", "Average price", "number"], ["description", "Description", "textarea"],
];
const LOCATION_FIELDS = [
  ["name", "Location name", "text"], ["area", "Area", "text"], ["description", "Description", "textarea"],
  ["latitude", "Latitude", "number"], ["longitude", "Longitude", "number"],
];
const MODE_FIELDS = [["name", "Transport mode name", "text"]];
const USER_FIELDS = [["username", "Username"], ["email", "Email"], ["full_name", "Full name"], ["location", "Location"], ["bio", "Bio"]];
const GENDERS = [["male", "Male"], ["female", "Female"], ["non_binary", "Non-binary"], ["other", "Other"], ["prefer_not_to_say", "Prefer not to say"]];

function PlaceRelations({ draft, setDraft }) {
  const places = useApiData("/places/");
  const locations = useApiData("/transport/locations/");
  return <>{[["location", "Transport location", locations], ["parent", "Parent place", places]].map(([field, label, list]) =>
    <label key={field}>{label} (optional)
      <select value={draft[field] ?? ""} disabled={list.loading || Boolean(list.error)}
        onChange={(event) => setDraft({ ...draft, [field]: event.target.value ? Number(event.target.value) : null })}>
        <option value="">None</option>
        {draft[field] && !list.rows.some((row) => row.id === draft[field]) && <option value={draft[field]}>Current #{draft[field]}</option>}
        {list.rows.filter((row) => field !== "parent" || row.id !== draft.id).map((row) =>
          <option key={row.id} value={row.id}>{row.name} · {row.area}</option>)}
      </select>
      {list.error && <span role="alert">{list.error.message}</span>}
    </label>)}</>;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function AdminPanel({ token, username, onBack, onSignIn }) {
  const request = useCallback((path, options) => apiRequest("/admin" + path, { ...options, token }), [token]);
  const [tab, setTab] = useState("places");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [needsLogin, setNeedsLogin] = useState(false);
  const [rejection, setRejection] = useState(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [draft, setDraft] = useState(null);
  const [userDraft, setUserDraft] = useState(null);
  const [formError, setFormError] = useState("");

  const reload = () => { setLoading(true); setReloadKey((key) => key + 1); };

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true); setError("");
      const params = new URLSearchParams();
      if (search.trim()) params.set("search", search.trim());
      if ((tab === "places" || tab === "locations" || tab === "fares" || contributionQueues.includes(tab)) && statusFilter) params.set("status", statusFilter);
      const query = params.toString();
      try {
        const [list, summary] = await Promise.all([
          request(`/${tab}/${query ? `?${query}` : ""}`), request("/stats/"),
        ]);
        if (cancelled) return;
        setItems(Array.isArray(list) ? list : list.results ?? []); setStats(summary); setNeedsLogin(false);
      } catch (err) {
        if (cancelled) return;
        setItems([]);
        if (err.status === 401 || err.status === 403) setNeedsLogin(true);
        else setError(err.message || "Could not load administration data.");
      } finally { if (!cancelled) setLoading(false); }
    }
    const timeout = setTimeout(load, 180);
    return () => { cancelled = true; clearTimeout(timeout); };
  }, [tab, search, statusFilter, reloadKey, request]);

  async function act(path, options = {}, confirmText = "") {
    if (busy || (confirmText && !window.confirm(confirmText))) return false;
    setError(""); setNotice(""); setBusy(true);
    try {
      await apiRequest(path, { ...options, token });
      setNotice("Change saved."); reload(); return true;
    } catch (err) {
      setError(err.message); return false;
    } finally { setBusy(false); }
  }

  function adminAction(path, options, confirmText) {
    return act("/admin" + path, options, confirmText);
  }

  async function reject(event) {
    event.preventDefault();
    if (!reason.trim()) return;
    const ok = await adminAction("/" + tab + "/" + rejection.id + "/reject/", {
      method: "POST", body: { reason: reason.trim() }
    });
    if (ok) setRejection(null);
  }

  async function saveRecord(event) {
    event.preventDefault(); setFormError("");
    const endpoint = tab === "locations" ? "locations" : "transport-modes";
    const fields = tab === "locations" ? LOCATION_FIELDS : MODE_FIELDS;
    const body = {};
    fields.forEach(([key, , type]) => {
      let value = draft[key] ?? "";
      if (type === "number") value = value === "" ? null : Number(value);
      body[key] = value;
    });
    const editing = Boolean(draft.id);
    const path = `/${endpoint}/${editing ? `${draft.id}/` : ""}`;
    try {
      await request(path, { method: editing ? "PATCH" : "POST", body: JSON.stringify(body) });
      setDraft(null); reload();
    } catch (err) { setFormError(err.message); }
  }

  async function savePlace(event) {
    event.preventDefault(); setFormError("");
    const body = {};
    PLACE_FIELDS.forEach(([key]) => { if (draft[key] !== undefined) body[key] = draft[key] === "" && key === "average_price" ? null : draft[key]; });
    try {
      for (const field of ["parent", "location"]) {
        if (draft[field] !== undefined) body[field] = draft[field];
      }
      await request(draft.id ? `/places/${draft.id}/` : "/places/", { method: draft.id ? "PATCH" : "POST", body });
      setDraft(null); reload();
    } catch (err) { setFormError(err.message); }
  }

  async function saveUser(event) {
    event.preventDefault(); setFormError("");
    const body = {};
    const original = items.find((user) => user.id === userDraft.id);
    for (const key of [...USER_FIELDS.map(([field]) => field), "gender"]) {
      const value = userDraft[key] ?? "";
      if (value !== (original?.[key] ?? "")) body[key] = value;
    }
    try {
      await request(`/users/${userDraft.id}/`, { method: "PATCH", body: JSON.stringify(body) });
      setUserDraft(null); reload();
    } catch (err) { setFormError(err.message); }
  }

  const moderation = stats?.moderation_enabled;
  const editableTab = tab === "locations" || tab === "transport-modes";
  const draftFields = tab === "locations" ? LOCATION_FIELDS : MODE_FIELDS;
  const title = TABS.find(([key]) => key === tab)?.[1] || "Administration";

  return (
    <section className="admin">
      <header className="admin-header">
        <div><p className="eyebrow">ADMINISTRATION</p><h1>KotoLagbe admin</h1></div>
        <button type="button" className="back-link" onClick={onBack}>Back to site</button>
      </header>

      {needsLogin && <section className="login-box">
        <p>Sign in with an active staff account to use administration.</p>
        <button type="button" onClick={onSignIn}>Sign in</button>
      </section>}

      {!needsLogin && stats && <section className="stats">
        <div><strong>{stats.places}</strong><span>Places</span></div>
        <div><strong>{stats.users}</strong><span>Users</span></div>
        <div><strong>{stats.locations}</strong><span>Transport locations</span></div>
        <div><strong>{stats.pending_locations ?? 0}</strong><span>Pending locations</span></div>
        <div><strong>{stats.active_transport_modes}/{stats.transport_modes}</strong><span>Active transport modes</span></div>
        <div><strong>{stats.pending_fares}</strong><span>Pending fares</span></div>
        <div><strong>{stats.approved_fares}</strong><span>Approved fares</span></div>
        <div><strong>{stats.pending_items}</strong><span>Pending items</span></div>
        <div><strong>{stats.pending_item_prices}</strong><span>Pending prices</span></div>
        <div><strong>{stats.pending_reviews}</strong><span>Pending reviews</span></div>
        <div><strong>{stats.pending_photos}</strong><span>Pending photos</span></div>
        <div><strong>{stats.blocked_users}</strong><span>Blocked users</span></div>
      </section>}

      {!needsLogin && <>
        <nav className="tabs" aria-label="Administration sections">
          {TABS.map(([key, label]) => <button type="button" key={key} disabled={busy} aria-pressed={tab === key} className={tab === key ? "active" : ""} onClick={() => { if (tab === key) { reload(); return; } setTab(key); setLoading(true); setItems([]); setNotice(""); setRejection(null); setSearch(""); setStatusFilter(""); setError(""); setDraft(null); setUserDraft(null); }}>{label}</button>)}
        </nav>
        <div className="admin-section-heading">
          <h2>{title}</h2>
          {tab === "places" && <button className="primary" onClick={() => { setFormError(""); setDraft({}); }}>Add place</button>}
          {editableTab && <button type="button" className="primary" onClick={() => { setFormError(""); setDraft(tab === "locations" ? { name: "", area: "", description: "", latitude: "", longitude: "" } : { name: "" }); }}>Add {tab === "locations" ? "location" : "transport mode"}</button>}
        </div>
        <div className="admin-filters">
          <button type="button" className="refresh-list" disabled={loading || busy} onClick={reload}>Refresh list</button>
          {tab !== "activity" && <input type="search" placeholder={`Search ${title.toLowerCase()}...`} aria-label={`Search ${title}`} value={search} onChange={(event) => setSearch(event.target.value)} />}
          {(tab === "places" && moderation || tab === "locations" || tab === "fares" || contributionQueues.includes(tab)) && <select aria-label="Filter by status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">All statuses</option><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option>
          </select>}
        </div>
        {notice && <p role="status">{notice}</p>}
        {loading && <p className="message" role="status">Loading…</p>}
        {error && !rejection && <p className="message error" role="alert">{error}</p>}
        {!loading && !error && items.length === 0 && <p className="message">Nothing to show.</p>}

        {!loading && items.length > 0 && <fieldset className="admin-records" disabled={busy}><div className="table-wrap"><table>
          {tab === "places" && <><thead><tr><th>Name</th><th>Category</th><th>Area</th>{moderation && <th>Status</th>}<th>Actions</th></tr></thead><tbody>
            {items.map((place) => <tr key={place.id}><td>{place.name}</td><td>{place.category}</td><td>{place.area}</td>{moderation && <td><span className={`badge ${place.status}`}>{place.status}</span></td>}<td className="actions">
              {moderation && place.status !== "approved" && <button type="button" onClick={() => adminAction(`/places/${place.id}/approve/`, { method: "POST" })}>Approve</button>}
              {moderation && place.status !== "rejected" && <button type="button" onClick={() => adminAction(`/places/${place.id}/reject/`, { method: "POST" })}>Reject</button>}
              <button type="button" onClick={() => { setFormError(""); setDraft({ ...place }); }}>Edit</button>
              <button type="button" className="danger" onClick={() => adminAction(`/places/${place.id}/`, { method: "DELETE" }, `Delete "${place.name}"?`)}>Delete</button>
            </td></tr>)}
          </tbody></>}

          {tab === "users" && <><thead><tr><th>Username</th><th>Full name</th><th>Email</th><th>Location</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            {items.map((user) => <tr key={user.id}><td>{user.username}</td><td>{user.full_name}</td><td>{user.email}</td><td>{user.location}</td><td>{user.is_staff ? "Admin" : "Member"}</td><td><span className={`badge ${user.is_active ? "approved" : "rejected"}`}>{user.is_active ? "Active" : "Blocked"}</span></td><td className="actions">
              {!user.is_staff && <button type="button" onClick={() => { setFormError(""); setUserDraft({ ...user }); }}>Edit</button>}
              {!user.is_staff && (user.is_active ? <button type="button" onClick={() => adminAction(`/users/${user.id}/block/`, { method: "POST" }, `Block ${user.username}?`)}>Block</button> : <button type="button" onClick={() => adminAction(`/users/${user.id}/unblock/`, { method: "POST" })}>Unblock</button>)}
              {!user.is_staff && <button type="button" className="danger" onClick={() => adminAction(`/users/${user.id}/`, { method: "DELETE" }, `Delete account ${user.username}? This cannot be undone.`)}>Delete</button>}
            </td></tr>)}
          </tbody></>}

          {tab === "locations" && <><thead><tr><th>Name</th><th>Area</th><th>Coordinates</th><th>Contributor</th><th>Submitted</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            {items.map((location) => <tr key={location.id}><td>{location.name}</td><td>{location.area}</td><td>{location.latitude}, {location.longitude}</td><td>{location.contributor || "Admin / legacy"}</td><td>{formatDate(location.submitted_at)}</td><td><span className={`badge ${location.status}`}>{location.status}</span></td><td className="actions">
              {location.status !== "approved" && <button type="button" onClick={() => adminAction(`/locations/${location.id}/approve/`, { method: "POST" })}>Approve</button>}
              {location.status !== "rejected" && <button type="button" onClick={() => adminAction(`/locations/${location.id}/reject/`, { method: "POST" })}>Reject</button>}
              <button type="button" onClick={() => { setFormError(""); setDraft({ ...location }); }}>Edit</button>
              <button type="button" className="danger" onClick={() => adminAction(`/locations/${location.id}/`, { method: "DELETE" }, `Delete location "${location.name}"?`)}>Delete</button>
            </td></tr>)}
          </tbody></>}

          {tab === "transport-modes" && <><thead><tr><th>Mode</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            {items.map((mode) => <tr key={mode.id}><td>{mode.name}</td><td><span className={`badge ${mode.is_active ? "approved" : "rejected"}`}>{mode.is_active ? "Active" : "Inactive"}</span></td><td className="actions"><button type="button" onClick={() => { setFormError(""); setDraft({ ...mode }); }}>Edit</button>{mode.is_active ? <button type="button" onClick={() => adminAction(`/transport-modes/${mode.id}/deactivate/`, { method: "POST" }, `Deactivate ${mode.name}? It will no longer appear in public transport choices.`)}>Deactivate</button> : <button type="button" onClick={() => adminAction(`/transport-modes/${mode.id}/activate/`, { method: "POST" })}>Activate</button>}<button type="button" className="danger" onClick={() => adminAction(`/transport-modes/${mode.id}/`, { method: "DELETE" }, `Delete ${mode.name}?`)}>Delete</button></td></tr>)}
          </tbody></>}

          {tab === "fares" && <><thead><tr><th>Origin</th><th>Destination</th><th>Mode</th><th>Fare (BDT)</th><th>Contributor</th><th>Submitted</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            {items.map((fare) => <tr key={fare.id}><td>{fare.origin_name}<small>{fare.origin_area}</small></td><td>{fare.destination_name}<small>{fare.destination_area}</small></td><td>{fare.transport_mode_name}</td><td>৳{fare.fare}</td><td>{fare.contributor}</td><td>{formatDate(fare.submitted_at)}</td><td><span className={`badge ${fare.status}`}>{fare.status}</span></td><td className="actions">{fare.status !== "approved" && <button type="button" onClick={() => adminAction(`/fares/${fare.id}/approve/`, { method: "POST" })}>Approve</button>}{fare.status !== "rejected" && <button type="button" onClick={() => adminAction(`/fares/${fare.id}/reject/`, { method: "POST" }, `Reject fare submission #${fare.id}?`)}>Reject</button>}</td></tr>)}
          </tbody></>}

          {contributionQueues.includes(tab) && <AdminModerationRows section={tab} rows={items}
            token={token} username={username} busy={busy}
            onApprove={(row) => adminAction("/" + tab + "/" + row.id + "/approve/", { method: "POST" })}
            onReject={(row) => { setReason(""); setError(""); setRejection(row); }}
            onRemove={(row) => act("/places/" + row.place + "/photos/" + row.id + "/", { method: "DELETE" }, "Delete this photo?")} />}

          {tab === "activity" && <><thead><tr><th>When</th><th>Administrator</th><th>Action</th><th>Record</th><th>Details</th></tr></thead><tbody>
            {items.map((log) => <tr key={log.id}><td>{formatDate(log.created_at)}</td><td>{log.actor_username}</td><td>{log.action}</td><td>{log.entity} #{log.entity_id}</td><td>{log.summary}</td></tr>)}
          </tbody></>}
        </table></div></fieldset>}
      </>}

      {rejection && <div className="modal-backdrop"><form className="modal" role="dialog" aria-modal="true" aria-label="Reject submission" onSubmit={reject}>
        <h2>Reject submission #{rejection.id}</h2>
        <label>Rejection reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} required rows={3} autoFocus /></label>
        {error && <p role="alert" className="form-error">{error}</p>}
        <div className="modal-actions"><button type="button" disabled={busy} onClick={() => { setRejection(null); setError(""); }}>Cancel</button>
          <button type="submit" disabled={busy || !reason.trim()}>Confirm rejection</button></div>
      </form></div>}

      {draft && <div className="modal-backdrop"><form className="modal" onSubmit={editableTab ? saveRecord : savePlace}>
        <h2>{draft.id ? "Edit" : "Add"} {tab === "locations" ? "location" : tab === "transport-modes" ? "transport mode" : "place"}</h2>
        {(editableTab ? draftFields : PLACE_FIELDS).map(([key, label, type = "text"]) => <label key={key}>{label}
          {type === "textarea" ? <textarea rows={3} value={draft[key] ?? ""} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} /> : <input type={type} step={type === "number" ? "any" : undefined} required={key !== "average_price" && key !== "description" && key !== "address"} value={draft[key] ?? ""} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} />}
        </label>)}
        {tab === "places" && <PlaceRelations draft={draft} setDraft={setDraft} />}
        {formError && <p className="form-error">{formError}</p>}
        <div className="modal-actions"><button type="button" onClick={() => setDraft(null)}>Cancel</button><button type="submit" className="primary">Save</button></div>
      </form></div>}

      {userDraft && <div className="modal-backdrop"><form className="modal" onSubmit={saveUser}>
        <h2>Edit user</h2>
        {USER_FIELDS.map(([key, label]) => <label key={key}>{label}{key === "bio" ? <textarea rows={3} maxLength={300} value={userDraft[key] ?? ""} onChange={(event) => setUserDraft({ ...userDraft, [key]: event.target.value })} /> : <input type={key === "email" ? "email" : "text"} required={key === "username"} value={userDraft[key] ?? ""} onChange={(event) => setUserDraft({ ...userDraft, [key]: event.target.value })} />}</label>)}
        <label>Gender<select value={userDraft.gender ?? "prefer_not_to_say"} onChange={(event) => setUserDraft({ ...userDraft, gender: event.target.value })}>{GENDERS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        {formError && <p className="form-error">{formError}</p>}
        <div className="modal-actions"><button type="button" onClick={() => setUserDraft(null)}>Cancel</button><button type="submit" className="primary">Save changes</button></div>
      </form></div>}
    </section>
  );
}

export default AdminPanel;
