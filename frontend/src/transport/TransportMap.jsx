
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";

import "leaflet/dist/leaflet.css";

// Import marker images explicitly for Vite
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// Create an explicit Leaflet marker icon
const locationIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export default function TransportMap({
  locations = [],
  onSelectLocation,
}) {
  // Only display locations with valid coordinates
  const validLocations = locations.filter((location) => {
    const latitude = Number(location.latitude);
    const longitude = Number(location.longitude);

    return (
      Number.isFinite(latitude) &&
      Number.isFinite(longitude) &&
      latitude >= -90 &&
      latitude <= 90 &&
      longitude >= -180 &&
      longitude <= 180
    );
  });

  return (
    <div className="transport-map">
      <MapContainer
        center={[23.8103, 90.4125]}
        zoom={12}
        scrollWheelZoom={true}
        style={{
          height: "450px",
          width: "100%",
          borderRadius: "10px",
        }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {validLocations.map((location) => (
          <Marker
            key={location.id}
            position={[
              Number(location.latitude),
              Number(location.longitude),
            ]}
            icon={locationIcon}
          >
            <Popup>
              <div>
                <strong>{location.name}</strong>

                {location.area && <p>{location.area}</p>}

                {onSelectLocation && (
                  <button
                    type="button"
                    onClick={() => onSelectLocation(location)}
                  >
                    Select this location
                  </button>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
