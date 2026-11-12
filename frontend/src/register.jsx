
import { useState } from "react";
import { registerUser } from "./services/auth.js";
import "./Auth.css";

function Register({ onRegistered, onSwitchToLogin }) {
  const [form, setForm] = useState({
    full_name: "",
    username: "",
    email: "",
    gender: "prefer_not_to_say",
    location: "",
    bio: "",
    password: "",
    confirmPassword: "",
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (form.password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    setSubmitting(true);

    try {
      await registerUser({
        full_name: form.full_name.trim(),
        username: form.username.trim(),
        email: form.email.trim(),
        gender: form.gender,
        location: form.location.trim(),
        bio: form.bio.trim(),
        password: form.password,
      });

      setSuccess("Welcome to KotoLagbe! Your account is ready.");

      setTimeout(() => {
        onRegistered(form.username.trim());
      }, 1000);

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
            <p className="auth-kicker">YOUR CITY. YOUR COMMUNITY.</p>

            <h1>
              Your city has
              <br />
              stories to tell.
            </h1>

            <p className="auth-intro-text">
              Discover hidden places, share your experiences,
              and connect with people who love exploring their city.
            </p>
          </div>

          <div className="auth-features">
            <span>Explore places</span>
            <span>Share discoveries</span>
            <span>Meet your community</span>
          </div>
        </div>

        <div className="auth-form-card">
          <div className="auth-heading">
            <p className="auth-kicker">BECOME A MEMBER</p>
            <h2>Create your account</h2>
            <p>Tell us a little about yourself.</p>
          </div>

          <form onSubmit={handleSubmit} className="auth-fields">

            <div className="auth-field full-width">
              <label>Full name</label>
              <input
                name="full_name"
                value={form.full_name}
                onChange={handleChange}
                placeholder="Your full name"
                maxLength={120}
                required
              />
            </div>

            <div className="auth-field">
              <label>Username</label>
              <input
                name="username"
                value={form.username}
                onChange={handleChange}
                placeholder="Choose a username"
                autoComplete="username"
                required
              />
            </div>

            <div className="auth-field">
              <label>Email address</label>
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </div>

            <div className="auth-field">
              <label>Gender</label>
              <select
                name="gender"
                value={form.gender}
                onChange={handleChange}
              >
                <option value="prefer_not_to_say">Prefer not to say</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="non_binary">Non-binary</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="auth-field">
              <label>City / Location</label>
              <input
                name="location"
                value={form.location}
                onChange={handleChange}
                placeholder="e.g. Dhanmondi, Dhaka"
                maxLength={120}
                required
              />
            </div>

            <div className="auth-field full-width">
              <label>Your bio</label>
              <textarea
                name="bio"
                value={form.bio}
                onChange={handleChange}
                placeholder="Tell the community something about yourself..."
                maxLength={300}
                rows={3}
              />
              <span className="character-count">
                {form.bio.length}/300
              </span>
            </div>

            <div className="auth-field">
              <label>Password</label>
              <input
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                placeholder="At least 8 characters"
                autoComplete="new-password"
                minLength={8}
                required
              />
            </div>

            <div className="auth-field">
              <label>Confirm password</label>
              <input
                name="confirmPassword"
                type="password"
                value={form.confirmPassword}
                onChange={handleChange}
                placeholder="Repeat password"
                autoComplete="new-password"
                required
              />
            </div>

            {error && (
              <p className="auth-alert error full-width">{error}</p>
            )}

            {success && (
              <p className="auth-alert success full-width">{success}</p>
            )}

            <button
              type="submit"
              className="auth-primary-button full-width"
              disabled={submitting}
            >
              {submitting ? "Creating account..." : "Join KotoLagbe →"}
            </button>
          </form>

          <p className="auth-bottom-text">
            Already a member?{" "}
            <button type="button" onClick={onSwitchToLogin}>
              Sign in
            </button>
          </p>
        </div>
      </div>
    </section>
  );
}

export default Register;
