import { useEffect, useState } from "react";

export default function PhotoPreview({ photo, token }) {
  const [preview, setPreview] = useState(null);
  const [failedSource, setFailedSource] = useState(null);
  const privatePhoto = photo.status !== "approved";
  const url = photo.image_url;
  useEffect(() => {
    if (!privatePhoto || !token) return;
    const controller = new AbortController();
    let objectUrl;
    async function load() {
      try {
        const response = await fetch(url, {
          headers: { Authorization: "Bearer " + token }, signal: controller.signal
        });
        if (!response.ok) throw new Error("Photo unavailable.");
        const bytes = await response.blob();
        if (!controller.signal.aborted) {
          objectUrl = URL.createObjectURL(bytes);
          setPreview({ url, token, src: objectUrl });
        }
      } catch {
        if (!controller.signal.aborted) setPreview({ url, token, error: true });
      }
    }
    load();
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [privatePhoto, url, token]);
  const current = preview?.url === url && preview?.token === token ? preview : null;
  if (privatePhoto && !current?.src) {
    return <span>{current?.error ? "Photo unavailable." : "Loading photo…"}</span>;
  }
  const src = privatePhoto ? current.src : url;
  if (failedSource === src) return <span role="status">Photo unavailable.</span>;
  return <img src={src} alt={photo.caption || "Photo of " + photo.place_name}
    onError={() => setFailedSource(src)} loading="lazy" className="place-photo-image" />;
}
