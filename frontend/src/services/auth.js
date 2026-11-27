
const API_URL = "http://127.0.0.1:8000/api/accounts";

async function apiRequest(endpoint, body) {
  const response = await fetch(`${API_URL}/${endpoint}/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    if (data.detail) {
      throw new Error(data.detail);
    }

    const message = Object.entries(data)
      .map(([field, errors]) =>
        `${field}: ${
          Array.isArray(errors) ? errors.join(" ") : errors
        }`
      )
      .join(" ");

    throw new Error(message || "Something went wrong.");
  }

  return data;
}

export function loginUser(username, password) {
  return apiRequest("login", { username, password });
}

export function registerUser(userData) {
  return apiRequest("register", userData);
}
