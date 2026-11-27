export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api").replace(/\/+$/, "");

function errorMessage(data, status) {
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const messages = Object.entries(data).flatMap(([field, errors]) =>
      [errors].flat().filter((value) => typeof value === "string")
        .map((value) => field === "non_field_errors" ? value : field.replaceAll("_", " ") + ": " + value)
    );
    if (messages.length) return messages.join(" ");
  }
  return "Request failed (HTTP " + status + ").";
}

export async function apiRequest(path, { method = "GET", token, body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = "Bearer " + token;
  let payload = body;
  if (body !== undefined && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    payload = typeof body === "string" ? body : JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(API_BASE + path, { method, headers, body: payload, signal });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Could not reach KotoLagbe. Check your connection and try again.", { cause: error });
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(errorMessage(data, response.status));
    error.status = response.status;
    throw error;
  }
  if (data === null) throw new Error("The server returned an unreadable response.");
  return data;
}
