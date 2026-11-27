import { useState } from "react";
import { apiRequest } from "./services/api.js";
import { useApiData } from "./services/useApiData.js";

function ContributionForm({ placeId, item, token }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = Object.fromEntries(new FormData(form));
    const path = item ? "/places/items/" + item.id + "/prices/" : "/places/items/suggest/";
    if (!item) body.place = placeId;
    setBusy(true); setError(""); setMessage("");
    try {
      await apiRequest(path, { method: "POST", token, body });
      form.reset();
      setMessage(item ? "Price submitted for staff review." : "Item and starting price submitted for staff review.");
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <form className="contribution-form" onSubmit={submit}>
    <fieldset disabled={busy}><legend>{item ? "Report a price for " + item.name : "Suggest an item"}</legend>
      {!item && <>
        <label>Item name<input name="name" maxLength={200} required /></label>
        <label>Item category<input name="category" maxLength={80} required /></label>
        <label>Description (optional)<input name="description" /></label>
      </>}
      <label>Price (BDT)<input name="price" type="number" step="0.01" min="0.01" max="99999999.99" required /></label>
      <button className="review-submit-button" type="submit">{item ? "Submit price" : "Submit item"}</button>
    </fieldset>
    {message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}
  </form>;
}

function PriceHistory({ item, token, onSignIn }) {
  const prices = useApiData("/places/items/" + item.id + "/prices/");
  return <div>
    {prices.loading && <p role="status">Loading prices…</p>}
    {prices.error && <p role="alert">{prices.error.message} <button onClick={prices.reload}>Retry</button></p>}
    {!prices.loading && !prices.error && !prices.rows.length && <p>No approved prices yet.</p>}
    <ul>{prices.rows.map((row) => <li key={row.id}>৳{row.price} · {new Date(row.submitted_at).toLocaleDateString()}</li>)}</ul>
    {token ? <ContributionForm item={item} token={token} /> :
      <button className="inline-action" onClick={onSignIn}>Sign in to report a price</button>}
  </div>;
}

export default function PlaceItems({ placeId, token, onSignIn }) {
  const items = useApiData("/places/items/?place=" + placeId);
  const [expanded, setExpanded] = useState(null);
  return <section className="place-contributions" aria-label="Items and prices">
    <h2>Items and prices</h2>
    {items.loading && <p role="status">Loading items…</p>}
    {items.error && <p role="alert">{items.error.message} <button onClick={items.reload}>Retry</button></p>}
    {!items.loading && !items.error && !items.rows.length && <p>No approved items yet.</p>}
    {items.rows.map((item) => <article key={item.id} className="contribution-item">
      <h3>{item.name}</h3><p>{item.category}{item.description && " · " + item.description}</p>
      {item.average_price != null && <p>Average price: ৳{item.average_price}</p>}
      <button className="inline-action" aria-expanded={expanded === item.id}
        onClick={() => setExpanded(expanded === item.id ? null : item.id)}>Prices for {item.name}</button>
      {expanded === item.id && <PriceHistory item={item} token={token} onSignIn={onSignIn} />}
    </article>)}
    {token ? <details><summary>Suggest an item</summary><ContributionForm placeId={placeId} token={token} /></details>
      : <button className="inline-action" onClick={onSignIn}>Sign in to suggest an item</button>}
  </section>;
}
