import { useEffect, useState } from "react";
import "./PlaceDetails.css";

import { API_BASE } from "./services/api.js";
import PlaceItems from "./PlaceItems.jsx";
import PlacePhotos from "./PlacePhotos.jsx";

const API_URL = API_BASE + "/places";

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

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewsError, setReviewsError] = useState("");

  const [rating, setRating] = useState("5");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [reviewMessage, setReviewMessage] = useState("");
  const [reviewError, setReviewError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function fetchData() {
      setLoading(true);
      setError("");
      setReviewsError("");

      try {
        const [placeResponse, reviewsResponse] = await Promise.all([
          fetch(`${API_URL}/${placeId}/`, {
            signal: controller.signal,
          }),
          fetch(`${API_URL}/${placeId}/reviews/`, {
            signal: controller.signal,
          }),
        ]);

        if (!placeResponse.ok) {
          throw new Error("Could not find this place.");
        }

        if (!reviewsResponse.ok) {
          throw new Error("Could not load reviews.");
        }

        const placeData = await placeResponse.json();
        const reviewsData = await reviewsResponse.json();

        setPlace(placeData);
        setReviews(
          Array.isArray(reviewsData)
            ? reviewsData
            : reviewsData.results || []
        );

        if (accessToken) {
          const ownResponse = await fetch(
            `${API_URL}/${placeId}/reviews/mine/`,
            {
              headers: {
                Authorization: `Bearer ${accessToken}`,
              },
              signal: controller.signal,
            }
          );

          if (ownResponse.ok) {
            const ownData = await ownResponse.json();
            setMyReview(ownData);
            setRating(String(ownData.rating || 5));
            setComment(ownData.comment || "");
          } else if (ownResponse.status === 404) {
            setMyReview(null);
            setRating("5");
            setComment("");
          } else {
            setMyReview(null);
          }
        } else {
          setMyReview(null);
          setRating("5");
          setComment("");
        }
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
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

    if (placeResponse.ok) {
      setPlace(await placeResponse.json());
    }

    if (reviewsResponse.ok) {
      const data = await reviewsResponse.json();
      setReviews(Array.isArray(data) ? data : data.results || []);
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
        body: JSON.stringify({
          rating: Number(rating),
          comment: comment.trim(),
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const firstError = Object.values(data)[0];
        throw new Error(
          Array.isArray(firstError)
            ? firstError[0]
            : typeof firstError === "string"
              ? firstError
              : "Could not submit your review."
        );
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

  if (loading) {
    return <p className="message">Loading place details...</p>;
  }

  if (error) {
    return (
      <section className="place-details">
        <button className="back-button" onClick={onBack}>
          ← Back to places
        </button>
        <p className="message error">{error}</p>
      </section>
    );
  }

  if (!place) return null;

  return (
    <section className="place-details">
      <button className="back-button" onClick={onBack}>
        ← Back to places
      </button>

      <div className="details-card">
        <div className="details-top">
          <span className="category">{place.category}</span>
          <span className="area">{place.area}</span>
        </div>

        <h1>{place.name}</h1>

        <p className="details-address">
          {place.address || place.area}
        </p>

        <div className="details-rating">
          {Number(place.review_count || 0) > 0 ? (
            <>
              <strong>
                ★ {Number(place.average_rating).toFixed(1)}
              </strong>
              <span>
                ({place.review_count} approved reviews)
              </span>
            </>
          ) : (
            <span>No approved reviews yet</span>
          )}
        </div>

        <div className="details-action-row">
          {accessToken ? (
            <button
              className={`favorite-toggle ${isFavorite ? "is-favorite" : ""}`}
              onClick={() =>
                onToggleFavorite?.(place)
              }
            >
              {isFavorite ? "♥ Remove from favorites" : "♡ Add to favorites"}
            </button>
          ) : (
            <button className="favorite-toggle" onClick={onSignIn}>
              Sign in to save this place
            </button>
          )}
        </div>

        <div className="details-divider" />

        <h2>About this place</h2>
        <p className="details-description">
          {place.description || "No description available."}
        </p>

        <div className="details-price">
          <span className="price-label">Average price</span>
          <strong>
            {place.average_price != null
              ? `৳${Number(place.average_price).toLocaleString("en-BD")}`
              : "Not available"}
          </strong>
        </div>

        <div className="details-divider" />

        {place.location_name && <p>Transport location: {place.location_name}</p>}
        {place.parent_name && <p>Part of {place.parent_name}</p>}
        <PlaceItems placeId={placeId} token={accessToken} onSignIn={onSignIn} />
        <PlacePhotos placeId={placeId} token={accessToken} onSignIn={onSignIn} />

        <section className="reviews-section">
          <h2>Reviews</h2>
          <p className="reviews-intro">
            Read what visitors think about this place.
          </p>

          {reviewsError && (
            <p className="message error">{reviewsError}</p>
          )}

          {reviews.length === 0 ? (
            <p className="reviews-empty">
              No approved reviews yet. Be the first to share your experience.
            </p>
          ) : (
            <div className="reviews-list">
              {reviews.map((review) => (
                <article className="review-card" key={review.id}>
                  <div className="review-card-top">
                    <strong>{review.username || "User"}</strong>
                    <span className="review-stars">
                      {"★".repeat(Number(review.rating || 0))}
                      {"☆".repeat(5 - Number(review.rating || 0))}
                    </span>
                  </div>

                  <p>{review.comment || "No written comment."}</p>

                  <small>
                    {review.created_at
                      ? new Date(review.created_at).toLocaleDateString()
                      : ""}
                  </small>
                </article>
              ))}
            </div>
          )}
        </section>

        <div className="details-divider" />

        <section className="review-form-section">
          <h2>{myReview ? "Edit your review" : "Write a review"}</h2>

          {!accessToken ? (
            <p className="reviews-intro">
              Please sign in to submit a review.
              {" "}
              <button
                type="button"
                className="inline-action"
                onClick={onSignIn}
              >
                Sign in
              </button>
            </p>
          ) : (
            <>
              {myReview && (
                <div className="review-status">
                  <strong>Your review status:</strong>{" "}
                  <span className={`status-${myReview.status}`}>
                    {myReview.status || "pending"}
                  </span>

                  {myReview.status === "rejected" &&
                    myReview.rejection_reason && (
                      <p className="rejection-reason">
                        Reason: {myReview.rejection_reason}
                      </p>
                    )}
                </div>
              )}

              <form className="review-form" onSubmit={submitReview}>
                <label htmlFor="review-rating">Your rating</label>
                <select
                  id="review-rating"
                  value={rating}
                  onChange={(event) => setRating(event.target.value)}
                  required
                >
                  <option value="5">5 - Excellent</option>
                  <option value="4">4 - Very good</option>
                  <option value="3">3 - Good</option>
                  <option value="2">2 - Fair</option>
                  <option value="1">1 - Poor</option>
                </select>

                <label htmlFor="review-comment">Your comment</label>
                <textarea
                  id="review-comment"
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                  placeholder="Share your experience with this place..."
                  rows={4}
                />

                {reviewError && (
                  <p className="message error">{reviewError}</p>
                )}

                {reviewMessage && (
                  <p className="review-success">{reviewMessage}</p>
                )}

                <button
                  className="review-submit-button"
                  type="submit"
                  disabled={submitting}
                >
                  {submitting
                    ? "Submitting..."
                    : myReview
                      ? "Update review"
                      : "Submit review"}
                </button>
              </form>

              <p className="review-note">
                Reviews are checked by moderators before appearing publicly.
                Editing a review sends it for moderation again.
              </p>
            </>
          )}
        </section>
      </div>
    </section>
  );
}

export default PlaceDetails;
