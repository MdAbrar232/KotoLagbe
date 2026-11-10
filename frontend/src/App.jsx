import PlaceDetails from "./PlaceDetails";
import { useEffect, useState } from "react";
import "./App.css";
import AdminPanel from "./AdminPanel";

const API_URL = "http://127.0.0.1:8000/api/accounts";

function getErrorMessage(data) {
  if (!data) return "Something went wrong. Please try again.";

  if (typeof data === "string") return data;

  if (data.detail) return data.detail;

  return Object.entries(data)
    .map(([field, messages]) => {
      const message = Array.isArray(messages)
        ? messages.join(" ")
        : String(messages);
      return `${field}: ${message}`;
    })
    .join(" ");
}

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

  const [formUsername, setFormUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authSuccess, setAuthSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Load places from Django
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

  // Clear messages when changing pages
  function openPage(nextPage) {
    setPage(nextPage);
    setAuthError("");
    setAuthSuccess("");
    setPassword("");
    setConfirmPassword("");
  }

  // Register a new user
  async function handleRegister(event) {
    event.preventDefault();
    setAuthError("");
    setAuthSuccess("");

    if (password !== confirmPassword) {
      setAuthError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setAuthError("Password must contain at least 8 characters.");
      return;
    }

    setSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/register/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: formUsername.trim(),
          email: email.trim(),
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(getErrorMessage(data));
      }

      setAuthSuccess("Account created successfully! You can now sign in.");
      setPassword("");
      setConfirmPassword("");

      setTimeout(() => {
        setFormUsername(data.username || formUsername.trim());
        openPage("login");
      }, 1000);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  // Log in an existing user
  async function handleLogin(event) {
    event.preventDefault();
    setAuthError("");
    setAuthSuccess("");
    setSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/login/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: formUsername.trim(),
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(getErrorMessage(data));
      }

      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("username", data.username);

      setAccessToken(data.access);
      setUsername(data.username);
      setPassword("");
      setAuthSuccess("Login successful!");

      setTimeout(() => {
        openPage("home");
      }, 700);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  // Log out
  function handleLogout() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("username");

    setAccessToken("");
    setUsername("");
    setPassword("");
    setAuthSuccess("");
    setAuthError("");
    openPage("home");
  }

  return (
    <main className="app">
      <nav className="site-nav">
        <button className="brand-button" onClick={() => openPage("home")}>
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
  		onClick={() => openPage("admin")}
		>
  		Admin Panel
		</button>
              <button className="nav-button" onClick={handleLogout}>
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
	{page === "admin" && <AdminPanel />}

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
            <h1>KotoLagbe<span>?</span></h1>
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
                aria-label="Filter by category"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
              >
                <option value="">All categories</option>
                <option value="Cafe">Cafes</option>
                <option value="Restaurant">Restaurants</option>
              </select>

              <select
                aria-label="Sort by price"
                value={ordering}
                onChange={(event) => setOrdering(event.target.value)}
              >
                <option value="">Default order</option>
                <option value="price">Price: low to high</option>
                <option value="-price">Price: high to low</option>
              </select>
            </div>

            {loading && <p className="message">Discovering places...</p>}
            {error && <p className="message error">{error}</p>}

            {!loading && !error && places.length === 0 && (
              <p className="message">No places match your search.</p>
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
                      <span className="category">{place.category}</span>
                      <span className="area">{place.area}</span>
                    </div>

                    <h3>{place.name}</h3>
                    <p className="address">{place.address || place.area}</p>
                    <p className="description">
                      {place.description || "Discover this place in Dhaka."}
                    </p>

                    <div className="card-footer">
                      <span className="price-label">Average price</span>
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
        <section className="auth-section">
          <div className="auth-card">
            <p className="eyebrow">JOIN KOTOLAGBE</p>
            <h2>Create your account</h2>
            <p className="auth-description">
              Create an account to get started with KotoLagbe.
            </p>

            <form onSubmit={handleRegister} className="auth-form">
              <label htmlFor="register-username">Username</label>
              <input
                id="register-username"
                type="text"
                placeholder="Choose a username"
                value={formUsername}
                onChange={(event) => setFormUsername(event.target.value)}
                autoComplete="username"
                required
              />

              <label htmlFor="register-email">Email address</label>
              <input
                id="register-email"
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
              />

              <label htmlFor="register-password">Password</label>
              <input
                id="register-password"
                type="password"
                placeholder="At least 8 characters"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
              />

              <label htmlFor="confirm-password">Confirm password</label>
              <input
                id="confirm-password"
                type="password"
                placeholder="Enter your password again"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                required
              />

              {authError && <p className="auth-message error">{authError}</p>}
              {authSuccess && (
                <p className="auth-message success">{authSuccess}</p>
              )}

              <button
                type="submit"
                className="auth-submit"
                disabled={submitting}
              >
                {submitting ? "Creating account..." : "Create account"}
              </button>
            </form>

            <p className="auth-switch">
              Already have an account?{" "}
              <button onClick={() => openPage("login")}>Sign in</button>
            </p>
          </div>
        </section>
      )}

      {page === "login" && (
        <section className="auth-section">
          <div className="auth-card">
            <p className="eyebrow">WELCOME BACK</p>
            <h2>Sign in</h2>
            <p className="auth-description">
              Sign in to continue exploring KotoLagbe.
            </p>

            <form onSubmit={handleLogin} className="auth-form">
              <label htmlFor="login-username">Username</label>
              <input
                id="login-username"
                type="text"
                placeholder="Enter your username"
                value={formUsername}
                onChange={(event) => setFormUsername(event.target.value)}
                autoComplete="username"
                required
              />

              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />

              {authError && <p className="auth-message error">{authError}</p>}
              {authSuccess && (
                <p className="auth-message success">{authSuccess}</p>
              )}

              <button
                type="submit"
                className="auth-submit"
                disabled={submitting}
              >
                {submitting ? "Signing in..." : "Sign in"}
              </button>
            </form>

            <p className="auth-switch">
              Don't have an account?{" "}
              <button onClick={() => openPage("register")}>
                Create account
              </button>
            </p>
          </div>
        </section>
      )}

      <footer>
        <span>KotoLagbe?</span>
        <span>Discover more. Spend smarter.</span>
      </footer>
    </main>
  );
}

export default App;
