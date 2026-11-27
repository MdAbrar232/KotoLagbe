import { useApiData } from "../services/useApiData.js";

export function useTransportList(path) {
  return useApiData(path ? "/transport/" + path : null);
}
