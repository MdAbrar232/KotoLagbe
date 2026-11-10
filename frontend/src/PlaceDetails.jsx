
import { useEffect, useState } from "react";
import "./PlaceDetails.css";

const API_URL = "http://127.0.0.1:8000/api/places";

function PlaceDetails({ placeId, onBack }) {
  const [place, setPlace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchPlace = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(`${API_URL}/${placeId}/`);

        if (!response.ok) {
          throw new Error("Could not find this place.");
        }

        const data = await response.json();
        setPlace(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPlace();
  }, [placeId]);

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

        <p className="details-address">{place.address}</p>

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
      </div>
    </section>
  );
}

export default PlaceDetails;
