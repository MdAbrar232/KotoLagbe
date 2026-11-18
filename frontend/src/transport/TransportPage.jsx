import { useId, useState } from "react";
import Login from "../login.jsx";
import { emptyRoute, transportRequest } from "./api.js";
import { useTransportList } from "./useTransportList.js";
import { FareRows, LoadState, LocationDirectory, RequestError } from "./TransportShared.jsx";
import "./Transport.css";

const sections = [
  ["transport", "Find fares"],
  ["transport-locations", "Locations"],
  ["transport-submit", "Submit a fare"],
];

function RouteFields({ route, setRoute, locations, modes, required = false }) {
  const prefix = useId();
  function change(field, value) {
    setRoute((previous) => {
      const next = { ...previous, [field]: value };
      if (field === "origin" && value === next.destination) next.destination = "";
      return next;
    });
  }

  return (
    <div className="tr-fields">
      <div className="tr-field">
        <label htmlFor={prefix + "-from"}>From</label>
        <select id={prefix + "-from"} required={required} value={route.origin} onChange={(e) => change("origin", e.target.value)}>
          <option value="">{required ? "Choose origin" : "All origins"}</option>
          {locations.map((stop) => <option key={stop.id} value={stop.id}>{stop.name} · {stop.area}</option>)}
        </select>
      </div>
      <div className="tr-field">
        <label htmlFor={prefix + "-to"}>To</label>
        <select id={prefix + "-to"} required={required} value={route.destination} onChange={(e) => change("destination", e.target.value)}>
          <option value="">{required ? "Choose destination" : "All destinations"}</option>
          {locations.map((stop) => (
            <option key={stop.id} value={stop.id} disabled={String(stop.id) === route.origin}>{stop.name} · {stop.area}</option>
          ))}
        </select>
      </div>
      <div className="tr-field">
        <label htmlFor={prefix + "-mode"}>Transport mode</label>
        <select id={prefix + "-mode"} required={required} value={route.transport_mode} onChange={(e) => change("transport_mode", e.target.value)}>
          <option value="">{required ? "Choose mode" : "All modes"}</option>
          {modes.map((mode) => <option key={mode.id} value={mode.id}>{mode.name}</option>)}
        </select>
      </div>
    </div>
  );
}

function FareFinder({ route, setRoute, locations, modes }) {
  const filters = new URLSearchParams(Object.entries(route).filter(([, value]) => value !== "")).toString();
  const list = useTransportList(filters ? "fares/?" + filters : "fares/");
  return (
    <>
      <div className="tr-panel">
        <div className="tr-heading">
          <h2>Choose a route</h2>
          {filters && <button type="button" className="tr-link" onClick={() => setRoute(emptyRoute)}>Clear filters</button>}
        </div>
        <RouteFields route={route} setRoute={setRoute} locations={locations} modes={modes} />
      </div>
      <section className="tr-results" aria-label="Approved fares">
        <div className="tr-heading">
          <h2>Approved fares</h2>
          <button type="button" className="tr-quiet" disabled={list.loading} onClick={list.reload}>Refresh fares</button>
        </div>
        <LoadState lists={[list]}>
          {list.rows.length
            ? <FareRows fares={list.rows} locations={locations} modes={modes} />
            : <p className="tr-empty">{filters ? "No approved fares match this route." : "No fares have been approved yet."}</p>}
        </LoadState>
      </section>
    </>
  );
}

function FareForm({ route, setRoute, locations, modes, token, onSignIn }) {
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [receipt, setReceipt] = useState(null);

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    setError(null);
    setReceipt(null);
    if (route.origin === route.destination) {
      setError(new Error("Choose a different destination."));
      return;
    }
    setBusy(true);
    try {
      const saved = await transportRequest("fares/", {
        method: "POST", token,
        body: {
          origin: Number(route.origin), destination: Number(route.destination),
          transport_mode: Number(route.transport_mode), fare: amount,
        },
      });
      setReceipt(saved);
      setAmount("");
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  if (locations.length < 2 || !modes.length) {
    return <p className="tr-empty">A fare needs two different locations and a transport mode. Check back when those are available.</p>;
  }
  return (
    <form className="tr-panel" onSubmit={submit}>
      <div className="tr-heading"><h2>Report what you paid</h2></div>
      <fieldset className="tr-fieldset" disabled={busy}>
        <RouteFields route={route} setRoute={setRoute} locations={locations} modes={modes} required />
        <label className="tr-field tr-amount">Fare paid (BDT)
          <input type="number" inputMode="decimal" min="0.01" max="99999999.99" step="0.01"
            required value={amount} onChange={(e) => setAmount(e.target.value)} />
        </label>
        <p className="tr-note">Staff review each fare before it appears in the public list.</p>
        <button className="tr-primary" type="submit">{busy ? "Submitting…" : "Submit fare"}</button>
      </fieldset>
      <RequestError error={error} onSignIn={onSignIn} />
      {receipt && <p className="tr-alert tr-success" role="status">Fare #{receipt.id} submitted for staff review.</p>}
    </form>
  );
}

export default function TransportPage({ token, onSignedIn, onRegister }) {
  const [page, setPage] = useState("transport");
  const [route, setRoute] = useState(emptyRoute);
  const [showLogin, setShowLogin] = useState(false);
  const directory = page === "transport-locations";
  const submit = page === "transport-submit";
  const guestPrompt = submit && !token;
  const locations = useTransportList(guestPrompt || showLogin ? null : "locations/");
  const modes = useTransportList(directory || guestPrompt || showLogin ? null : "modes/");
  const lists = directory ? [locations] : [locations, modes];
  const onSignIn = () => setShowLogin(true);

  if (showLogin) {
    return <Login
      initialUsername={localStorage.getItem("username") || ""}
      onLoginSuccess={(data) => { setShowLogin(false); onSignedIn(data); }}
      onSwitchToRegister={onRegister}
    />;
  }

  return (
    <section className="tr-page tr-public" aria-label="Transport">
      <header className="tr-header">
        <h1>Transport fares</h1>
        <p>Find what riders paid between stops in Dhaka.</p>
      </header>
      <nav className="tr-sections" aria-label="Transport sections">
        {sections.map(([value, label]) => (
          <button type="button" key={value} aria-pressed={page === value} onClick={() => setPage(value)}>{label}</button>
        ))}
      </nav>
      {guestPrompt ? (
        <div className="tr-panel">
          <h2>Submit a fare</h2>
          <p className="tr-note">Sign in to report the fare you paid.</p>
          <button className="tr-primary" type="button" onClick={onSignIn}>Sign in to submit</button>
        </div>
      ) : (
        <LoadState lists={lists} onSignIn={onSignIn}>
          {directory && <section className="tr-panel">
            <div className="tr-heading"><h2>Transport locations</h2></div>
            <LocationDirectory locations={locations.rows} />
          </section>}
          {page === "transport" && <FareFinder route={route} setRoute={setRoute} locations={locations.rows} modes={modes.rows} />}
          {submit && <FareForm route={route} setRoute={setRoute} locations={locations.rows} modes={modes.rows} token={token} onSignIn={onSignIn} />}
        </LoadState>
      )}
    </section>
  );
}
