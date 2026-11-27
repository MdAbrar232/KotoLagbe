
import { useEffect, useState } from "react";
import "./profile.css";

const API_URL = "http://127.0.0.1:8000/api/accounts";

function getInitials(name, username) {
  const value = (name || username || "U").trim();

  return value
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

function Profile({ accessToken }) {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({
    full_name: "",
    gender: "prefer_not_to_say",
    location: "",
    bio: "",
  });

  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadProfile() {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(`${API_URL}/profile/`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          signal: controller.signal,
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Could not load profile.");
        }

        setProfile(data);

        setForm({
          full_name: data.full_name || "",
          gender: data.gender || "prefer_not_to_say",
          location: data.location || "",
          bio: data.bio || "",
        });
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

    loadProfile();

    return () => controller.abort();
  }, [accessToken]);

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  async function handleSave(event) {
    event.preventDefault();

    setError("");
    setSuccess("");
    setSaving(true);

    try {
      const response = await fetch(`${API_URL}/profile/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          full_name: form.full_name.trim(),
          gender: form.gender,
          location: form.location.trim(),
          bio: form.bio.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        const message = Object.entries(data)
          .map(([field, messages]) =>
            `${field}: ${
              Array.isArray(messages) ? messages.join(" ") : messages
            }`
          )
          .join(" ");

        throw new Error(message || "Could not update profile.");
      }

      setProfile(data);
      setEditing(false);
      setSuccess("Your profile has been updated!");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function cancelEditing() {
    setForm({
      full_name: profile.full_name || "",
      gender: profile.gender || "prefer_not_to_say",
      location: profile.location || "",
      bio: profile.bio || "",
    });

    setEditing(false);
    setError("");
  }

  const genderLabels = {
    male: "Male",
    female: "Female",
    non_binary: "Non-binary",
    other: "Other",
    prefer_not_to_say: "Prefer not to say",
  };

  if (loading) {
    return (
      <section className="profile-page">
        <p className="profile-loading">Loading your profile...</p>
      </section>
    );
  }

  if (!profile) {
    return (
      <section className="profile-page">
        <p className="profile-error">
          {error || "Profile could not be loaded."}
        </p>
      </section>
    );
  }

  return (
    <section className="profile-page">
      <div className="profile-container">

        <div className="profile-top-heading">
          <div>
            <p className="profile-eyebrow">YOUR KOTOLAGBE SPACE</p>
            <h1>My Profile</h1>
            <p>Manage your identity in the community.</p>
          </div>

          {!editing && (
            <button
              className="profile-edit-button"
              onClick={() => {
                setEditing(true);
                setSuccess("");
                setError("");
              }}
            >
              Edit profile
            </button>
          )}
        </div>

        {error && <p className="profile-error">{error}</p>}
        {success && <p className="profile-success">{success}</p>}

        <div className="profile-card">

          <div className="profile-cover">
            <span>DISCOVER. CONNECT. EXPLORE.</span>
          </div>

          <div className="profile-main">

            <div className="profile-avatar">
              {getInitials(profile.full_name, profile.username)}
            </div>

            <div className="profile-identity">
              <h2>{profile.full_name || profile.username}</h2>
              <p>@{profile.username}</p>
              <span className="profile-location">
                <span>⌖</span>
                {profile.location || "Location not added"}
              </span>
            </div>

            {!editing && (
              <div className="profile-member-label">
                KotoLagbe Member
              </div>
            )}

          </div>

          <div className="profile-content">

            {editing ? (
              <form onSubmit={handleSave} className="profile-form">

                <h3>Edit your information</h3>

                <div className="profile-form-grid">

                  <div className="profile-field">
                    <label>Full name</label>
                    <input
                      name="full_name"
                      value={form.full_name}
                      onChange={handleChange}
                      maxLength={120}
                      required
                    />
                  </div>

                  <div className="profile-field">
                    <label>Username</label>
                    <input value={profile.username} disabled />
                  </div>

                  <div className="profile-field">
                    <label>Email address</label>
                    <input value={profile.email} disabled />
                  </div>

                  <div className="profile-field">
                    <label>Gender</label>
                    <select
                      name="gender"
                      value={form.gender}
                      onChange={handleChange}
                    >
                      <option value="prefer_not_to_say">
                        Prefer not to say
                      </option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="non_binary">Non-binary</option>
                      <option value="other">Other</option>
                    </select>
                  </div>

                  <div className="profile-field full-width">
                    <label>City / Location</label>
                    <input
                      name="location"
                      value={form.location}
                      onChange={handleChange}
                      maxLength={120}
                      placeholder="e.g. Dhanmondi, Dhaka"
                    />
                  </div>

                  <div className="profile-field full-width">
                    <label>About me</label>
                    <textarea
                      name="bio"
                      value={form.bio}
                      onChange={handleChange}
                      maxLength={300}
                      rows={4}
                      placeholder="Tell the community about yourself..."
                    />
                    <span className="profile-character-count">
                      {form.bio.length}/300
                    </span>
                  </div>

                </div>

                <div className="profile-form-actions">
                  <button
                    type="button"
                    className="profile-cancel-button"
                    onClick={cancelEditing}
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="profile-save-button"
                    disabled={saving}
                  >
                    {saving ? "Saving..." : "Save changes"}
                  </button>
                </div>

              </form>
            ) : (
              <>
                <div className="profile-about">
                  <h3>About me</h3>
                  <p>
                    {profile.bio ||
                      "This user hasn't written a bio yet. Tell the community something about yourself!"}
                  </p>
                </div>

                <div className="profile-details">
                  <h3>Personal information</h3>

                  <div className="profile-detail-grid">

                    <div className="profile-detail">
                      <span>Full name</span>
                      <strong>{profile.full_name || "Not provided"}</strong>
                    </div>

                    <div className="profile-detail">
                      <span>Username</span>
                      <strong>@{profile.username}</strong>
                    </div>

                    <div className="profile-detail">
                      <span>Email</span>
                      <strong>{profile.email}</strong>
                    </div>

                    <div className="profile-detail">
                      <span>Gender</span>
                      <strong>
                        {genderLabels[profile.gender] || "Not specified"}
                      </strong>
                    </div>

                    <div className="profile-detail">
                      <span>Location</span>
                      <strong>
                        {profile.location || "Not provided"}
                      </strong>
                    </div>

                  </div>
                </div>
              </>
            )}

          </div>
        </div>

        <div className="profile-note">
          Your profile is your identity in the KotoLagbe community.
          Share your interests and the places you love.
        </div>

      </div>
    </section>
  );
}

export default Profile;
