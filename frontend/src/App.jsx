import TransportPage from "./transport/TransportPage.jsx";
import TransportDiscovery from "./transport/TransportDiscovery.jsx";
import { useEffect, useState } from "react";
import "./App.css";

import PlaceDetails from "./PlaceDetails";
import AdminPanel from "./AdminPanel";
import Profile from "./profile.jsx";
import Login from "./login.jsx";
import Register from "./register.jsx";

import { API_BASE } from "./services/api.js";

const API_URL = API_BASE + "/places";

function App() {
  const [places, setPlaces] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [favoriteLoading, setFavoriteLoading] = useState(false);
  const [favoriteError, setFavoriteError] = useState("");
  const [favoriteBusyIds, setFavoriteBusyIds] = useState(new Set());

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [ordering, setOrdering] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [page, setPage] = useState("home");
  const [selectedPlaceId, setSelectedPlaceId] = useState(null);

  const [username, setUsername] = useState(
    localStorage.getItem("username") || ""
  );

  const [accessToken, setAccessToken] = useState(
    localStorage.getItem("access") || ""
  );

  const [isStaff, setIsStaff] = useState(false);
  const [formUsername, setFormUsername] = useState("");

  const favoriteIds = new Set(favorites.map((place) => place.id));

  const activePage =
    (!accessToken &&
      (page === "admin" || page === "profile" || page === "favorites")) ||
    (page === "admin" && !isStaff)
      ? "home"
      : page;

  // Verify staff permissions.
  useEffect(() => {
    if (!accessToken) {
      return;
    }

    const controller = new AbortController();

    async function verifyStaff() {
      try {
        const response = await fetch(
          API_BASE + "/admin/stats/",
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
            signal: controller.signal,
          }
        );

        setIsStaff(response.ok);
      } catch (err) {
        if (err.name !== "AbortError") {
          setIsStaff(false);
        }
      }
    }

    verifyStaff();

    return () => controller.abort();
  }, [accessToken]);

  // Load places.
  useEffect(() => {
    const controller = new AbortController();

    if (activePage !== "home") return;
    async function fetchPlaces() {
      setLoading(true);
      setError("");

      const params = new URLSearchParams();

      if (search.trim()) params.set("search", search.trim());
      if (category) params.set("category", category);
      if (ordering) params.set("ordering", ordering);

      try {
        const response = await fetch(
          `${API_URL}/?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("Failed to load places.");
        }

        const data = await response.json();
        setPlaces(Array.isArray(data) ? data : data.results || []);
      } catch (err) {
        if (err.name !== "AbortError") {
          setError("Could not load places. Check that Django is running.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    const timeout = setTimeout(fetchPlaces, 250);

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [search, category, ordering, activePage]);

  // Load the logged-in user's favorites.
  useEffect(() => {
    if (!accessToken || !["home", "favorites", "details"].includes(activePage)) {
      return;
    }

    const controller = new AbortController();

    async function fetchFavorites() {
      setFavoriteLoading(true);
      setFavoriteError("");

      try {
        const response = await fetch(`${API_URL}/favorites/`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error("Could not load your favorites.");
        }

        const data = await response.json();
        setFavorites(Array.isArray(data) ? data : data.results || []);
      } catch (err) {
        if (err.name !== "AbortError") {
          setFavoriteError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setFavoriteLoading(false);
        }
      }
    }

    fetchFavorites();

    return () => controller.abort();
  }, [accessToken, activePage]);

  function openPage(nextPage) {
    setPage(nextPage);
  }

  function openPlace(placeId) {
    setSelectedPlaceId(placeId);
    setPage("details");
  }

  function handleLoginSuccess(data) {
    setAccessToken(data.access);
    setUsername(data.username);
    setPage("home");
  }

  function handleRegistered(registeredUsername) {
    setFormUsername(registeredUsername);
    setPage("login");
  }

  function handleLogout() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("username");

    setAccessToken("");
    setUsername("");
    setIsStaff(false);
    setFavorites([]);
    setFavoriteError("");
    setFormUsername("");
    setPage("home");
  }

  async function toggleFavorite(place) {
    if (!accessToken) {
      setPage("login");
      return;
    }

    if (favoriteBusyIds.has(place.id)) return;

    setFavoriteBusyIds((previous) => {
      const next = new Set(previous);
      next.add(place.id);
      return next;
    });

    setFavoriteError("");

    const alreadyFavorite = favoriteIds.has(place.id);

    try {
      const response = await fetch(
        alreadyFavorite
          ? `${API_URL}/favorites/${place.id}/`
          : `${API_URL}/favorites/`,
        {
          method: alreadyFavorite ? "DELETE" : "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            ...(alreadyFavorite
              ? {}
              : { "Content-Type": "application/json" }),
          },
          ...(alreadyFavorite
            ? {}
            : { body: JSON.stringify({ place: place.id }) }),
        }
      );

      if (!response.ok) {
        throw new Error(
          alreadyFavorite
            ? "Could not remove this favorite."
            : "Could not add this favorite."
        );
      }

      if (alreadyFavorite) {
        setFavorites((previous) =>
          previous.filter((item) => item.id !== place.id)
        );
      } else {
        setFavorites((previous) => {
          if (previous.some((item) => item.id === place.id)) {
            return previous;
          }
          return [...previous, place];
        });
      }
    } catch (err) {
      setFavoriteError(err.message);
    } finally {
      setFavoriteBusyIds((previous) => {
        const next = new Set(previous);
        next.delete(place.id);
        return next;
      });
    }
  }

  function renderPlaceCard(place) {
    const isFavorite = favoriteIds.has(place.id);
    const isBusy = favoriteBusyIds.has(place.id);

    return (
      <article
        className="place-card"
        key={place.id}
        onClick={() => openPlace(place.id)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openPlace(place.id);
          }
        }}
        role="button"
        tabIndex={0}
      >
        <div className="card-top">
          <span className="category">{place.category}</span>
          <span className="area">{place.area}</span>
        </div>

        <h3>{place.name}</h3>

        <p className="address">
          {place.address || place.area}
        </p>

        <p className="description">
          {place.description || "Discover this place in Dhaka."}
        </p>

        <div className="card-rating">
          {Number(place.review_count || 0) > 0
            ? `★ ${Number(place.average_rating).toFixed(1)} (${place.review_count} reviews)`
            : "No approved reviews yet"}
        </div>

        <div className="card-footer">
          <span className="price-label">Average price</span>
          <strong>
            {place.average_price != null
              ? `৳${Number(place.average_price).toLocaleString("en-BD")}`
              : "Not available"}
          </strong>
        </div>

        <button
          type="button"
          className={`favorite-toggle ${isFavorite ? "is-favorite" : ""}`}
          disabled={isBusy}
          aria-label={
            isFavorite ? "Remove from favorites" : "Add to favorites"
          }
          onClick={(event) => {
            event.stopPropagation();
            toggleFavorite(place);
          }}
        >
          {isBusy
            ? "Saving..."
            : isFavorite
              ? "♥ Saved"
              : "♡ Add to favorites"}
        </button>
      </article>
    );
  }

  return (
    <main className="app">
      <nav className="site-nav">
        <button
          className="brand-button"
          onClick={() => openPage("home")}
        >
          KotoLagbe<span>?</span>
        </button>

        <div className="nav-actions">
          {accessToken ? (
            <>
              <span className="welcome-user">
                Hi, {username}
              </span>

              <button
                className="nav-button"
                onClick={() => openPage("favorites")}
              >
                Favorites
              </button>

              <button
                className="nav-button"
                onClick={() => openPage("profile")}
              >
                My Profile
              </button>

              {isStaff && (
                <button
                  className="nav-button"
                  onClick={() => openPage("admin")}
                >
                  Admin Panel
                </button>
              )}

              <button
                className="nav-button"
                onClick={handleLogout}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <button
                className="nav-button"
                onClick={() => openPage("login")}
              >
                Sign in
              </button>

              <button
                className="nav-button nav-button-primary"
                onClick={() => openPage("register")}
              >
                Create account
              </button>
            </>
          )}
        </div>
      </nav>

      {activePage === "admin" && isStaff && <AdminPanel token={accessToken} username={username} onBack={() => openPage("home")} onSignIn={() => openPage("login")} />}

      {activePage === "profile" && accessToken && (
        <Profile accessToken={accessToken} />
      )}

      {activePage === "favorites" && accessToken && (
        <section className="favorites-page">
          <div className="section-heading">
            <div>
              <p className="eyebrow">YOUR COLLECTION</p>
              <h2>My Favorites</h2>
            </div>

            <span className="count">
              {favorites.length} saved
            </span>
          </div>

          {favoriteLoading && (
            <p className="message">Loading your favorites...</p>
          )}

          {favoriteError && (
            <p className="message error">{favoriteError}</p>
          )}

          {!favoriteLoading &&
            !favoriteError &&
            favorites.length === 0 && (
              <p className="message">
                You haven't saved any places yet. Explore places and
                add your favorites here.
              </p>
            )}

          {!favoriteLoading && favorites.length > 0 && (
            <div className="places-grid">
              {favorites.map(renderPlaceCard)}
            </div>
          )}

          <button
            className="back-button"
            onClick={() => openPage("home")}
          >
            ← Explore places
          </button>
        </section>
      )}

      {activePage === "details" && selectedPlaceId !== null && (
        <PlaceDetails
          key={selectedPlaceId}
          placeId={selectedPlaceId}
          onBack={() => openPage("home")}
          accessToken={accessToken}
          isFavorite={favoriteIds.has(selectedPlaceId)}
          onToggleFavorite={(place) => toggleFavorite(place)}
          onSignIn={() => openPage("login")}
        />
      )}

      {activePage === "home" && (
        <>
          <header className="hero">
            <p className="eyebrow">YOUR CITY, DISCOVERED</p>

            <h1>
              KotoLagbe<span>?</span>
            </h1>

            <p className="subtitle">
              Find places, explore neighbourhoods, and discover what things cost.
            </p>
          </header>

          <section className="places-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">EXPLORE DHAKA</p>
                <h2>Places worth knowing</h2>
              </div>

              <span className="count">
                {places.length} {places.length === 1 ? "place" : "places"}
              </span>
            </div>

            <div className="filters">
              <input
                type="search"
                placeholder="Search by place or area..."
                aria-label="Search by place name or area"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />

              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
              >
                <option value="">All categories</option>
                <option value="Cafe">Cafes</option>
                <option value="Restaurant">Restaurants</option>
              </select>

              <select
                value={ordering}
                onChange={(event) => setOrdering(event.target.value)}
              >
                <option value="">Default order</option>
                <option value="price">Price: low to high</option>
                <option value="-price">Price: high to low</option>
              </select>
            </div>

            {loading && (
              <p className="message">Discovering places...</p>
            )}

            {error && (
              <p className="message error">{error}</p>
            )}

            {favoriteError && (
              <p className="message error">{favoriteError}</p>
            )}

            {!loading && !error && places.length === 0 && (
              <p className="message">
                No places match your search.
              </p>
            )}

            {!error && (
              <div className="places-grid">
                {places.map(renderPlaceCard)}
              </div>
            )}
          </section>

          <TransportDiscovery onExplore={() => openPage("transport")} />
        </>
      )}

      {activePage === "transport" && (
        <TransportPage
          token={accessToken}
          onSignedIn={(data) => {
            handleLoginSuccess(data);
            openPage("transport");
          }}
          onRegister={() => openPage("register")}
          onBack={() => openPage("home")}
        />
      )}

      {activePage === "register" && (
        <Register
          onRegistered={handleRegistered}
          onSwitchToLogin={() => openPage("login")}
        />
      )}

      {activePage === "login" && (
        <Login
          initialUsername={formUsername}
          onLoginSuccess={handleLoginSuccess}
          onSwitchToRegister={() => openPage("register")}
        />
      )}

      <footer>
        <span>KotoLagbe?</span>
        <span>Discover more. Spend smarter.</span>
      </footer>
    </main>
  );
}

export default App;
