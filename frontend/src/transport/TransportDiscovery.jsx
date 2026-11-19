import "./TransportDiscovery.css";

export default function TransportDiscovery({ onExplore }) {
  return (
    <section className="transport-discovery" aria-labelledby="transport-discovery-title">
      <div>
        <h2 id="transport-discovery-title">Getting around Dhaka</h2>
        <p>Check fares reported by riders before you head out.</p>
      </div>
      <button type="button" onClick={onExplore}>
        Explore transport fares <span aria-hidden="true">→</span>
      </button>
    </section>
  );
}
