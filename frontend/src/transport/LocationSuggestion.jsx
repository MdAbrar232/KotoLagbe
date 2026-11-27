import { useState } from "react";
import { transportRequest } from "./api.js";

export default function LocationSuggestion({ token, onSignIn }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    setBusy(true); setError(""); setMessage("");
    try {
      await transportRequest("locations/", { method: "POST", token, body: Object.fromEntries(new FormData(form)) });
      form.reset();
      setMessage("Location submitted for staff review.");
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  if (!token) return <button className="tr-link" onClick={onSignIn}>Sign in to suggest a location</button>;
  return <details><summary>Suggest a location</summary><form onSubmit={submit} className="tr-submission">
    <fieldset className="tr-fieldset" disabled={busy}>
      <label className="tr-field">Location name<input name="name" maxLength={200} required /></label>
      <label className="tr-field">Area<input name="area" maxLength={150} required /></label>
      <label className="tr-field">Latitude<input name="latitude" type="number" min="-90" max="90" step="0.000001" required /></label>
      <label className="tr-field">Longitude<input name="longitude" type="number" min="-180" max="180" step="0.000001" required /></label>
      <label className="tr-field">Description (optional)<input name="description" /></label>
      <button className="tr-primary" type="submit">Submit location</button>
    </fieldset>
    {message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}
  </form></details>;
}
