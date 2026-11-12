
import { useState } from "react";
import { loginUser } from "./services/auth.js";
import "./Auth.css";

function Login({
  initialUsername = "",
  onLoginSuccess,
  onSwitchToRegister,
}) {
  const [username, setUsername] = useState(initialUsername);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSubmitting(true);

    try {
      const data = await loginUser(username.trim(), password);

      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("username", data.username);

      onLoginSuccess(data);

    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-layout">

        <div className="auth-intro">
          <span className="auth-brand">KotoLagbe<span>?</span></span>

          <div>
            <p className="auth-kicker">WELCOME BACK</p>

            <h1>
              The city is
              <br />
              waiting for you.
            </h1>

            <p className="auth-intro-text">
              Pick up where you left off. Discover new places,
              catch up with the community, and share your next adventure.
            </p>
          </div>

          <div className="auth-features">
            <span>Discover</span>
            <span>Connect</span>
            <span>Explore</span>
          </div>
        </div>

        <div className="auth-form-card login-card">
          <div className="auth-heading">
            <p className="auth-kicker">YOUR COMMUNITY AWAITS</p>
            <h2>Welcome back.</h2>
            <p>Sign in to your KotoLagbe account.</p>
          </div>

          <form onSubmit={handleSubmit} className="auth-fields">

            <div className="auth-field full-width">
              <label>Username</label>
              <input
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Enter your username"
                autoComplete="username"
                required
              />
            </div>

            <div className="auth-field full-width">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                required
              />
            </div>

            {error && (
              <p className="auth-alert error full-width">{error}</p>
            )}

            <button
              type="submit"
              className="auth-primary-button full-width"
              disabled={submitting}
            >
              {submitting ? "Signing in..." : "Sign in →"}
            </button>
          </form>

          <p className="auth-bottom-text">
            New to KotoLagbe?{" "}
            <button type="button" onClick={onSwitchToRegister}>
              Create an account
            </button>
          </p>
        </div>
      </div>
    </section>
  );
}

export default Login;
