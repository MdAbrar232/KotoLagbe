const BASE_URL = "http://127.0.0.1:8000/api/transport/";
export const emptyRoute = { origin: "", destination: "", transport_mode: "" };

function responseMessage(data, status) {
  if (status === 401) return "Your session has expired. Sign in again to continue.";
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const messages = Object.entries(data).flatMap(([field, errors]) =>
      Array.isArray(errors) ? [field.replaceAll("_", " ") + ": " + errors.join(" ")] : []
    );
    if (messages.length) return messages.join(" ");
  }
  return "The transport request failed (HTTP " + status + ").";
}

export async function transportRequest(path, { method = "GET", token, body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = "Bearer " + token;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(BASE_URL + path, {
      method, headers, signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Could not reach the transport service. Check your connection and try again.", { cause: error });
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(responseMessage(data, response.status));
    error.status = response.status;
    throw error;
  }
  if (!data) throw new Error("The transport service returned an unreadable response.");
  return data;
}
