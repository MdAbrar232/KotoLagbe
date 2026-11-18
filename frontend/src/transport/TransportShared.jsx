import { useState } from "react";

const amounts = new Intl.NumberFormat("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const dates = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });

export function RequestError({ error, onRetry, onSignIn }) {
  if (!error) return null;
  const signIn = error.status === 401 && onSignIn;
  return (
    <div className="tr-alert tr-error" role="alert">
      <span>{error.message}</span>
      {signIn
        ? <button type="button" className="tr-link" onClick={onSignIn}>Sign in again</button>
        : onRetry && <button type="button" className="tr-link" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function LoadState({ lists, onSignIn, children }) {
  const failed = lists.find((list) => list.error);
  if (failed) return <RequestError error={failed.error} onRetry={failed.reload} onSignIn={onSignIn} />;
  if (lists.some((list) => list.loading)) return <p className="tr-empty" role="status">Loading…</p>;
  return children;
}

export function LocationDirectory({ locations }) {
  const [search, setSearch] = useState("");
  const query = search.trim().toLowerCase();
  const matches = locations.filter((stop) => (stop.name + " " + stop.area).toLowerCase().includes(query));

  if (!locations.length) {
    return <p className="tr-empty">No transport locations have been added yet.</p>;
  }
  return (
    <>
      <label className="tr-field tr-search">Search locations
        <input type="search" placeholder="Name or area" value={search} onChange={(e) => setSearch(e.target.value)} />
      </label>
      {matches.length === 0 && <p className="tr-empty">No locations match your search.</p>}
      <ul className="tr-locations">
        {matches.map((stop) => (
          <li key={stop.id}>
            <div className="tr-card-head">
              <div><h3>{stop.name}</h3><p>{stop.area}</p></div>
            </div>
            {stop.description && <p>{stop.description}</p>}
            <dl className="tr-coords">
              <div><dt>Latitude</dt><dd>{stop.latitude.toFixed(6)}</dd></div>
              <div><dt>Longitude</dt><dd>{stop.longitude.toFixed(6)}</dd></div>
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}

export function FareRows({ fares, locations, modes }) {
  const stops = new Map(locations.map((stop) => [stop.id, stop]));
  const modeNames = new Map(modes.map((mode) => [mode.id, mode.name]));
  return (
    <ul className="tr-fares">
      {fares.map((fare) => {
        const origin = stops.get(fare.origin);
        const destination = stops.get(fare.destination);
        return (
          <li key={fare.id}>
            <div className="tr-trip">
              <p className="tr-meta">
                <strong>{modeNames.get(fare.transport_mode) ?? "Mode #" + fare.transport_mode}</strong>
                <time dateTime={fare.submitted_at}>{dates.format(new Date(fare.submitted_at))}</time>
              </p>
              <p className="tr-route">
                <span>{origin?.name ?? "Location #" + fare.origin}</span>
                <span className="tr-direction" aria-hidden="true">→</span><span className="tr-sr">to</span>
                <span>{destination?.name ?? "Location #" + fare.destination}</span>
              </p>
              {origin && destination && <p className="tr-areas">{origin.area} → {destination.area}</p>}
            </div>
            <strong className="tr-price">৳{amounts.format(Number(fare.fare))}</strong>
          </li>
        );
      })}
    </ul>
  );
}
