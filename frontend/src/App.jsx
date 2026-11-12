
import { useEffect, useState } from "react";
import "./App.css";

import PlaceDetails from "./PlaceDetails";
import AdminPanel from "./AdminPanel";
import Profile from "./profile.jsx";
import Login from "./login.jsx";
import Register from "./register.jsx";

function App() {
  const [places, setPlaces] = useState([]);
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

  // Verify staff permissions
  useEffect(() => {
    if (!accessToken) {
      setIsStaff(false);
      return;
    }

    const controller = new AbortController();

    async function verifyStaff() {
      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/admin/stats/",
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

  // Protect private pages
  useEffect(() => {
    if (!accessToken && (page === "admin" || page === "profile")) {
      setPage("home");
    }

    if (page === "admin" && !isStaff) {
      setPage("home");
    }
  }, [page, accessToken, isStaff]);

  // Load places
  useEffect(() => {
    const controller = new AbortController();

    async function fetchPlaces() {
      setLoading(true);
      setError("");

      const params = new URLSearchParams();

      if (search.trim()) params.set("search", search.trim());
      if (category) params.set("category", category);
      if (ordering) params.set("ordering", ordering);

      try {
        const response = await fetch(
          `http://127.0.0.1:8000/api/places/?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("Failed to load places.");
        }

        const data = await response.json();
        setPlaces(data);
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
  }, [search, category, ordering]);

  function openPage(nextPage) {
    setPage(nextPage);
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
    setFormUsername("");
    setPage("home");
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

      {page === "admin" && isStaff && <AdminPanel />}

      {page === "profile" && accessToken && (
        <Profile accessToken={accessToken} />
      )}

      {page === "details" && selectedPlaceId !== null && (
        <PlaceDetails
          placeId={selectedPlaceId}
          onBack={() => openPage("home")}
        />
      )}

      {page === "home" && (
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

            {!loading && !error && places.length === 0 && (
              <p className="message">
                No places match your search.
              </p>
            )}

            {!error && (
              <div className="places-grid">
                {places.map((place) => (
                  <article
                    className="place-card"
                    key={place.id}
                    onClick={() => {
                      setSelectedPlaceId(place.id);
                      openPage("details");
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedPlaceId(place.id);
                        openPage("details");
                      }
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="card-top">
                      <span className="category">
                        {place.category}
                      </span>

                      <span className="area">
                        {place.area}
                      </span>
                    </div>

                    <h3>{place.name}</h3>

                    <p className="address">
                      {place.address || place.area}
                    </p>

                    <p className="description">
                      {place.description || "Discover this place in Dhaka."}
                    </p>

                    <div className="card-footer">
                      <span className="price-label">
                        Average price
                      </span>

                      <strong>
                        {place.average_price != null
                          ? `৳${Number(place.average_price).toLocaleString("en-BD")}`
                          : "Not available"}
                      </strong>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {page === "register" && (
        <Register
          onRegistered={handleRegistered}
          onSwitchToLogin={() => openPage("login")}
        />
      )}

      {page === "login" && (
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
