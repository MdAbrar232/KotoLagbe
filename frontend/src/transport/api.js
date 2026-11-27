import { apiRequest } from "../services/api.js";

export const emptyRoute = { origin: "", destination: "", transport_mode: "" };

export function transportRequest(path, options) {
  return apiRequest("/transport/" + path, options);
}
