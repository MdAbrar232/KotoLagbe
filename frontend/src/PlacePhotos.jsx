import { useState } from "react";
import { apiRequest } from "./services/api.js";
import { useApiData } from "./services/useApiData.js";
import PhotoPreview from "./PhotoPreview.jsx";

export default function PlacePhotos({ placeId, token, onSignIn }) {
  const path = "/places/" + placeId + "/photos/";
  const photos = useApiData(path, token);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function upload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = new FormData(form);
    setError("");
    setMessage("");
    if (body.get("image").size > 5 * 1024 * 1024) {
      setError("Choose a photo of 5 MiB or less.");
      return;
    }
    setBusy(true);
    try {
      await apiRequest(path, { method: "POST", token, body });
      form.reset();
      setMessage("Photo submitted for staff review.");
      photos.reload();
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }

  async function remove(photo) {
    if (!window.confirm("Delete this photo?")) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await apiRequest(path + photo.id + "/", { method: "DELETE", token });
      setMessage("Photo deleted.");
      photos.reload();
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }

  return <section className="place-contributions" aria-label="Place photos">
    <h2>Photos</h2>
    {photos.loading && <p role="status">Loading photos…</p>}
    {photos.error && <p role="alert">{photos.error.message} <button onClick={photos.reload}>Retry</button></p>}
    {!photos.loading && !photos.error && !photos.rows.length && <p>No photos yet.</p>}
    <div className="photo-gallery">{photos.rows.map((photo) => <figure key={photo.id}>
      <PhotoPreview photo={photo} token={token} />
      <figcaption>{photo.caption && <strong>{photo.caption}</strong>}<span>By {photo.username}</span>
        {photo.can_delete && <>
          <span className={"status-" + photo.status}>{photo.status}</span>
          {photo.rejection_reason && <span>{photo.rejection_reason}</span>}
          <button className="inline-action" disabled={busy} onClick={() => remove(photo)}>Delete photo</button>
        </>}
      </figcaption>
    </figure>)}</div>
    {token ? <form onSubmit={upload} className="contribution-form">
      <fieldset disabled={busy}><legend>Upload a photo</legend>
        <label>Photo <input type="file" name="image" accept="image/jpeg,image/png,image/webp" required /></label>
        <small>JPEG, PNG, or WebP. Up to 5 MiB and 16 megapixels.</small>
        <label>Caption (optional)<input name="caption" maxLength={200} /></label>
        <button className="review-submit-button" type="submit">Upload photo</button>
      </fieldset>
    </form> : <button className="inline-action" onClick={onSignIn}>Sign in to upload a photo</button>}
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
