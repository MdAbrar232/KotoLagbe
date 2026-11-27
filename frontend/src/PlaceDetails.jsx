import { useEffect, useState } from "react";
import "./PlaceDetails.css";

const API_URL = "http://127.0.0.1:8000/api/places";
const MAX_PHOTO_SIZE = 5 * 1024 * 1024;

function asList(data) {
  return Array.isArray(data) ? data : data?.results || [];
}

function responseError(data, fallback) {
  if (data?.detail) return data.detail;
  for (const value of Object.values(data || {})) {
    if (Array.isArray(value) && value.length) return String(value[0]);
    if (typeof value === "string") return value;
  }
  return fallback;
}

function PlaceDetails({
  placeId,
  onBack,
  accessToken,
  isFavorite,
  onToggleFavorite,
  onSignIn,
}) {
  const [place, setPlace] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [myReview, setMyReview] = useState(null);
  const [placeItems, setPlaceItems] = useState([]);
  const [photos, setPhotos] = useState([]);
  const [myPhotos, setMyPhotos] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewsError, setReviewsError] = useState("");
  const [itemsError, setItemsError] = useState("");
  const [photosError, setPhotosError] = useState("");

  const [rating, setRating] = useState("5");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [reviewMessage, setReviewMessage] = useState("");
  const [reviewError, setReviewError] = useState("");

  const [photoFile, setPhotoFile] = useState(null);
  const [photoCaption, setPhotoCaption] = useState("");
  const [photoSubmitting, setPhotoSubmitting] = useState(false);
  const [photoMessage, setPhotoMessage] = useState("");
  const [photoError, setPhotoError] = useState("");

  const [itemSuggestion, setItemSuggestion] = useState({
    name: "",
    category: "Food",
    description: "",
    price: "",
  });
  const [itemSubmitting, setItemSubmitting] = useState(false);
  const [itemMessage, setItemMessage] = useState("");
  const [itemError, setItemError] = useState("");
  const [priceValues, setPriceValues] = useState({});
  const [priceMessages, setPriceMessages] = useState({});
  const [priceErrors, setPriceErrors] = useState({});
  const [priceBusyIds, setPriceBusyIds] = useState([]);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchData() {
      setLoading(true);
      setError("");
      setReviewsError("");
      setItemsError("");
      setPhotosError("");

      try {
        const [placeResponse, reviewsResponse, itemsResponse, photosResponse] = await Promise.all([
          fetch(`${API_URL}/${placeId}/`, { signal: controller.signal }),
          fetch(`${API_URL}/${placeId}/reviews/`, { signal: controller.signal }),
          fetch(`${API_URL}/items/?place=${placeId}`, { signal: controller.signal }),
          fetch(`${API_URL}/${placeId}/photos/`, { signal: controller.signal }),
        ]);

        if (!placeResponse.ok) throw new Error("Could not find this place.");
        setPlace(await placeResponse.json());

        if (reviewsResponse.ok) {
          setReviews(asList(await reviewsResponse.json()));
        } else {
          setReviewsError("Could not load reviews.");
        }

        if (itemsResponse.ok) {
          setPlaceItems(asList(await itemsResponse.json()));
        } else {
          setItemsError("Could not load place items.");
        }

        if (photosResponse.ok) {
          setPhotos(asList(await photosResponse.json()));
        } else {
          setPhotosError("Could not load place photos.");
        }

        if (accessToken) {
          const [ownReviewResponse, ownPhotosResponse] = await Promise.all([
            fetch(`${API_URL}/${placeId}/reviews/mine/`, {
              headers: { Authorization: `Bearer ${accessToken}` },
              signal: controller.signal,
            }),
            fetch(`${API_URL}/${placeId}/photos/mine/`, {
              headers: { Authorization: `Bearer ${accessToken}` },
              signal: controller.signal,
            }),
          ]);

          if (ownReviewResponse.ok) {
            const ownData = await ownReviewResponse.json();
            setMyReview(ownData);
            setRating(String(ownData.rating || 5));
            setComment(ownData.comment || "");
          } else if (ownReviewResponse.status === 404) {
            setMyReview(null);
            setRating("5");
            setComment("");
          } else {
            setMyReview(null);
          }

          if (ownPhotosResponse.ok) {
            setMyPhotos(asList(await ownPhotosResponse.json()));
          } else {
            setMyPhotos([]);
          }
        } else {
          setMyReview(null);
          setMyPhotos([]);
          setRating("5");
          setComment("");
        }
      } catch (err) {
        if (err.name !== "AbortError") setError(err.message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    fetchData();
    return () => controller.abort();
  }, [placeId, accessToken]);

  async function refreshPlaceAndReviews() {
    const [placeResponse, reviewsResponse] = await Promise.all([
      fetch(`${API_URL}/${placeId}/`),
      fetch(`${API_URL}/${placeId}/reviews/`),
    ]);

    if (placeResponse.ok) setPlace(await placeResponse.json());
    if (reviewsResponse.ok) setReviews(asList(await reviewsResponse.json()));
  }

  async function refreshPhotos() {
    const publicResponse = await fetch(`${API_URL}/${placeId}/photos/`);
    if (publicResponse.ok) setPhotos(asList(await publicResponse.json()));

    if (accessToken) {
      const ownResponse = await fetch(`${API_URL}/${placeId}/photos/mine/`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (ownResponse.ok) setMyPhotos(asList(await ownResponse.json()));
    }
  }

  async function refreshItems() {
    const response = await fetch(`${API_URL}/items/?place=${placeId}`);
    if (response.ok) setPlaceItems(asList(await response.json()));
  }

  async function submitPhoto(event) {
    event.preventDefault();
    if (!accessToken) {
      onSignIn?.();
      return;
    }
    if (!photoFile) {
      setPhotoError("Choose a photo to upload.");
      return;
    }
    if (photoFile.size > MAX_PHOTO_SIZE) {
      setPhotoError("The photo must be 5 MB or smaller.");
      return;
    }

    setPhotoSubmitting(true);
    setPhotoMessage("");
    setPhotoError("");
    const form = event.currentTarget;
    const formData = new FormData();
    formData.append("image_upload", photoFile);
    formData.append("caption", photoCaption.trim());

    try {
      const response = await fetch(`${API_URL}/${placeId}/photos/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(responseError(data, "Could not upload this photo."));
      }

      setPhotoFile(null);
      setPhotoCaption("");
      form.reset();
      setPhotoMessage("Your photo has been submitted. It will appear after admin approval.");
      await refreshPhotos();
    } catch (err) {
      setPhotoError(err.message);
    } finally {
      setPhotoSubmitting(false);
    }
  }

  async function submitItemSuggestion(event) {
    event.preventDefault();
    if (!accessToken) {
      onSignIn?.();
      return;
    }

    setItemSubmitting(true);
    setItemMessage("");
    setItemError("");

    try {
      const response = await fetch(`${API_URL}/items/suggest/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          place: placeId,
          name: itemSuggestion.name.trim(),
          category: itemSuggestion.category.trim(),
          description: itemSuggestion.description.trim(),
          price: itemSuggestion.price,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(responseError(data, "Could not submit this item."));
      }

      setItemSuggestion({ name: "", category: "Food", description: "", price: "" });
      setItemMessage("Your item and starting price have been sent for admin moderation.");
      await refreshItems();
    } catch (err) {
      setItemError(err.message);
    } finally {
      setItemSubmitting(false);
    }
  }

  async function submitItemPrice(event, itemId) {
    event.preventDefault();
    if (!accessToken) {
      onSignIn?.();
      return;
    }

    const value = String(priceValues[itemId] || "").trim();
    if (!value || Number(value) <= 0) {
      setPriceErrors((current) => ({ ...current, [itemId]: "Enter a price greater than zero." }));
      return;
    }

    setPriceBusyIds((current) => [...current, itemId]);
    setPriceErrors((current) => ({ ...current, [itemId]: "" }));
    setPriceMessages((current) => ({ ...current, [itemId]: "" }));

    try {
      const response = await fetch(`${API_URL}/items/${itemId}/prices/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ price: value }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(responseError(data, "Could not submit this price."));
      }

      setPriceValues((current) => ({ ...current, [itemId]: "" }));
      setPriceMessages((current) => ({
        ...current,
        [itemId]: "Price submitted for moderation.",
      }));
    } catch (err) {
      setPriceErrors((current) => ({ ...current, [itemId]: err.message }));
    } finally {
      setPriceBusyIds((current) => current.filter((id) => id !== itemId));
    }
  }

  async function submitReview(event) {
    event.preventDefault();
    if (!accessToken) {
      onSignIn?.();
      return;
    }

    setSubmitting(true);
    setReviewMessage("");
    setReviewError("");

    const isEditing = Boolean(myReview?.id);
    const endpoint = isEditing
      ? `${API_URL}/${placeId}/reviews/${myReview.id}/`
      : `${API_URL}/${placeId}/reviews/`;

    try {
      const response = await fetch(endpoint, {
        method: isEditing ? "PATCH" : "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ rating: Number(rating), comment: comment.trim() }),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(responseError(data, "Could not submit your review."));
      }

      setMyReview(data);
      setReviewMessage(
        isEditing
          ? "Your review has been updated and sent for moderation."
          : "Your review has been submitted for moderation."
      );
      await refreshPlaceAndReviews();
    } catch (err) {
      setReviewError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <p className="message">Loading place details...</p>;

  if (error) {
    return (
      <section className="place-details">
        <button className="back-button" onClick={onBack}>← Back to places</button>
        <p className="message error">{error}</p>
      </section>
    );
  }

  if (!place) return null;

  return (
    <section className="place-details">
      <button className="back-button" onClick={onBack}>← Back to places</button>

      <div className="details-card">
        <div className="details-top">
          <span className="category">{place.category}</span>
          <span className="area">{place.area}</span>
        </div>

        <h1>{place.name}</h1>
        <p className="details-address">{place.address || place.area}</p>

        <div className="details-rating">
          {Number(place.review_count || 0) > 0 ? (
            <>
              <strong>★ {Number(place.average_rating).toFixed(1)}</strong>
              <span>({place.review_count} approved reviews)</span>
            </>
          ) : <span>No approved reviews yet</span>}
        </div>

        <div className="details-action-row">
          {accessToken ? (
            <button
              className={`favorite-toggle ${isFavorite ? "is-favorite" : ""}`}
              onClick={() => onToggleFavorite?.(place)}
            >
              {isFavorite ? "♥ Remove from favorites" : "♡ Add to favorites"}
            </button>
          ) : (
            <button className="favorite-toggle" onClick={onSignIn}>Sign in to save this place</button>
          )}
        </div>

        <div className="details-divider" />
        <h2>About this place</h2>
        <p className="details-description">{place.description || "No description available."}</p>
        <div className="details-price">
          <span className="price-label">Average price</span>
          <strong>{place.average_price != null ? `৳${Number(place.average_price).toLocaleString("en-BD")}` : "Not available"}</strong>
        </div>

        <div className="details-divider" />

        <section className="photos-section">
          <h2>Photos</h2>
          <p className="reviews-intro">Photos shared by visitors and approved by the KotoLagbe team.</p>
          {photosError && <p className="message error">{photosError}</p>}
          {photos.length > 0 ? (
            <div className="place-photo-grid">
              {photos.map((photo) => (
                <figure className="place-photo-card" key={photo.id}>
                  <a href={photo.image} target="_blank" rel="noreferrer">
                    <img src={photo.image} alt={photo.caption || `${place.name} visitor photo`} loading="lazy" />
                  </a>
                  {photo.caption && <figcaption>{photo.caption}</figcaption>}
                </figure>
              ))}
            </div>
          ) : !photosError ? (
            <p className="reviews-empty">No approved photos yet. You can share the first one.</p>
          ) : null}

          <div className="photo-upload-box">
            <h3>Share a photo of this place</h3>
            {!accessToken ? (
              <p className="reviews-intro">Please <button type="button" className="inline-action" onClick={onSignIn}>sign in</button> to upload a photo.</p>
            ) : (
              <form className="contribution-form" onSubmit={submitPhoto}>
                <label htmlFor="place-photo-file">Choose photo (JPEG, PNG or WebP; maximum 5 MB)</label>
                <input
                  id="place-photo-file"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  required
                  onChange={(event) => setPhotoFile(event.target.files?.[0] || null)}
                />
                <label htmlFor="place-photo-caption">Caption (optional)</label>
                <input
                  id="place-photo-caption"
                  type="text"
                  maxLength={255}
                  value={photoCaption}
                  onChange={(event) => setPhotoCaption(event.target.value)}
                  placeholder="What does this photo show?"
                />
                {photoError && <p className="message error">{photoError}</p>}
                {photoMessage && <p className="review-success">{photoMessage}</p>}
                <button className="review-submit-button" type="submit" disabled={photoSubmitting}>
                  {photoSubmitting ? "Uploading..." : "Submit photo"}
                </button>
              </form>
            )}
          </div>

          {accessToken && myPhotos.length > 0 && (
            <div className="my-photo-submissions">
              <h3>Your photo submissions</h3>
              {myPhotos.map((photo) => (
                <div className="my-photo-status" key={photo.id}>
                  <img src={photo.image} alt={photo.caption || `Your photo submission ${photo.id}`} />
                  <span>{photo.caption || `Photo #${photo.id}`}</span>
                  <span className={`status-${photo.status}`}>{photo.status}</span>
                  {photo.status === "rejected" && photo.rejection_reason && <p>Reason: {photo.rejection_reason}</p>}
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="details-divider" />

        <section className="place-items-section">
          <h2>Items and prices</h2>
          <p className="reviews-intro">See items reported by visitors and share a price you have seen.</p>
          {itemsError && <p className="message error">{itemsError}</p>}
          {placeItems.length > 0 ? (
            <div className="place-items-list">
              {placeItems.map((item) => (
                <article className="place-item-card" key={item.id}>
                  <div className="place-item-heading">
                    <div><h3>{item.name}</h3><span>{item.category}</span></div>
                    <strong>{item.average_price != null ? `৳${Number(item.average_price).toLocaleString("en-BD")}` : "Price not available"}</strong>
                  </div>
                  {item.description && <p>{item.description}</p>}
                  {accessToken ? (
                    <form className="item-price-form" onSubmit={(event) => submitItemPrice(event, item.id)}>
                      <label htmlFor={`item-price-${item.id}`}>Suggest a price (BDT)</label>
                      <input
                        id={`item-price-${item.id}`}
                        type="number"
                        min="0.01"
                        step="0.01"
                        required
                        value={priceValues[item.id] || ""}
                        onChange={(event) => setPriceValues((current) => ({ ...current, [item.id]: event.target.value }))}
                        placeholder="Enter amount"
                      />
                      {priceErrors[item.id] && <p className="message error">{priceErrors[item.id]}</p>}
                      {priceMessages[item.id] && <p className="review-success">{priceMessages[item.id]}</p>}
                      <button className="review-submit-button" type="submit" disabled={priceBusyIds.includes(item.id)}>
                        {priceBusyIds.includes(item.id) ? "Submitting..." : "Submit price"}
                      </button>
                    </form>
                  ) : (
                    <p className="reviews-intro">Sign in to suggest a price. <button type="button" className="inline-action" onClick={onSignIn}>Sign in</button></p>
                  )}
                </article>
              ))}
            </div>
          ) : !itemsError ? (
            <p className="reviews-empty">No approved items have been added for this place yet.</p>
          ) : null}

          <div className="photo-upload-box">
            <h3>Suggest an item</h3>
            {!accessToken ? (
              <p className="reviews-intro">Please <button type="button" className="inline-action" onClick={onSignIn}>sign in</button> to suggest an item.</p>
            ) : (
              <form className="contribution-form" onSubmit={submitItemSuggestion}>
                <label htmlFor="suggest-item-name">Item name</label>
                <input id="suggest-item-name" type="text" maxLength={200} required value={itemSuggestion.name} onChange={(event) => setItemSuggestion((current) => ({ ...current, name: event.target.value }))} />
                <label htmlFor="suggest-item-category">Category</label>
                <input id="suggest-item-category" type="text" maxLength={80} required value={itemSuggestion.category} onChange={(event) => setItemSuggestion((current) => ({ ...current, category: event.target.value }))} />
                <label htmlFor="suggest-item-description">Description (optional)</label>
                <textarea id="suggest-item-description" rows={3} value={itemSuggestion.description} onChange={(event) => setItemSuggestion((current) => ({ ...current, description: event.target.value }))} />
                <label htmlFor="suggest-item-price">Current price (BDT)</label>
                <input id="suggest-item-price" type="number" min="0.01" step="0.01" required value={itemSuggestion.price} onChange={(event) => setItemSuggestion((current) => ({ ...current, price: event.target.value }))} />
                {itemError && <p className="message error">{itemError}</p>}
                {itemMessage && <p className="review-success">{itemMessage}</p>}
                <button className="review-submit-button" type="submit" disabled={itemSubmitting}>
                  {itemSubmitting ? "Submitting..." : "Submit item and price"}
                </button>
              </form>
            )}
          </div>
        </section>

        <div className="details-divider" />

        <section className="reviews-section">
          <h2>Reviews</h2>
          <p className="reviews-intro">Read what visitors think about this place.</p>
          {reviewsError && <p className="message error">{reviewsError}</p>}
          {reviews.length === 0 ? (
            <p className="reviews-empty">No approved reviews yet. Be the first to share your experience.</p>
          ) : (
            <div className="reviews-list">
              {reviews.map((review) => (
                <article className="review-card" key={review.id}>
                  <div className="review-card-top">
                    <strong>{review.username || "User"}</strong>
                    <span className="review-stars">{"★".repeat(Number(review.rating || 0))}{"☆".repeat(5 - Number(review.rating || 0))}</span>
                  </div>
                  <p>{review.comment || "No written comment."}</p>
                  <small>{review.created_at ? new Date(review.created_at).toLocaleDateString() : ""}</small>
                </article>
              ))}
            </div>
          )}
        </section>

        <div className="details-divider" />

        <section className="review-form-section">
          <h2>{myReview ? "Edit your review" : "Write a review"}</h2>
          {!accessToken ? (
            <p className="reviews-intro">Please sign in to submit a review. <button type="button" className="inline-action" onClick={onSignIn}>Sign in</button></p>
          ) : (
            <>
              {myReview && (
                <div className="review-status">
                  <strong>Your review status:</strong>{" "}
                  <span className={`status-${myReview.status}`}>{myReview.status || "pending"}</span>
                  {myReview.status === "rejected" && myReview.rejection_reason && <p className="rejection-reason">Reason: {myReview.rejection_reason}</p>}
                </div>
              )}
              <form className="review-form" onSubmit={submitReview}>
                <label htmlFor="review-rating">Your rating</label>
                <select id="review-rating" value={rating} onChange={(event) => setRating(event.target.value)} required>
                  <option value="5">5 - Excellent</option>
                  <option value="4">4 - Very good</option>
                  <option value="3">3 - Good</option>
                  <option value="2">2 - Fair</option>
                  <option value="1">1 - Poor</option>
                </select>
                <label htmlFor="review-comment">Your comment</label>
                <textarea id="review-comment" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Share your experience with this place..." rows={4} />
                {reviewError && <p className="message error">{reviewError}</p>}
                {reviewMessage && <p className="review-success">{reviewMessage}</p>}
                <button className="review-submit-button" type="submit" disabled={submitting}>
                  {submitting ? "Submitting..." : myReview ? "Update review" : "Submit review"}
                </button>
              </form>
              <p className="review-note">Reviews are checked by moderators before appearing publicly. Editing a review sends it for moderation again.</p>
            </>
          )}
        </section>
      </div>
    </section>
  );
}

export default PlaceDetails;
