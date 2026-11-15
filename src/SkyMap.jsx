
import { useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8000";

const WIDTH = 1000;
const HEIGHT = 500;

function normalizeRa(ra) {
  return ((Number(ra) % 360) + 360) % 360;
}

function project(ra, dec) {
  return {
    x: (1 - normalizeRa(ra) / 360) * WIDTH,
    y: ((90 - Number(dec)) / 180) * HEIGHT,
  };
}

export default function SkyMap({ onSelectCoordinates }) {
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(`${API}/api/observations`);

        if (!response.ok) {
          throw new Error("Unable to load NASA observations");
        }

        const data = await response.json();

        if (!cancelled) {
          setObservations(data.observations || []);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  const polygons = useMemo(() => {
    return observations.flatMap((observation) => {
      if (!Array.isArray(observation.corners)) {
        return [];
      }

      const corners = observation.corners.map(
        ([ra, dec]) => project(ra, dec)
      );

      // Avoid drawing polygons across the RA 0/360 seam.
      const xs = corners.map((point) => point.x);

      if (Math.max(...xs) - Math.min(...xs) > WIDTH / 2) {
        return [];
      }

      return [{
        observation,
        points: corners
          .map((point) => `${point.x},${point.y}`)
          .join(" "),
      }];
    });
  }, [observations]);

  function handleMapClick(event) {
    const svg = event.currentTarget;
    const rect = svg.getBoundingClientRect();

    const x = ((event.clientX - rect.left) / rect.width) * WIDTH;
    const y = ((event.clientY - rect.top) / rect.height) * HEIGHT;

    const ra = normalizeRa((1 - x / WIDTH) * 360);
    const dec = 90 - (y / HEIGHT) * 180;

    setSelected({ center_ra: ra, center_dec: dec });
    onSelectCoordinates(ra, dec);
  }

  function selectObservation(observation) {
    setSelected(observation);
    onSelectCoordinates(
      observation.center_ra,
      observation.center_dec
    );
  }

  const raLines = Array.from(
    { length: 13 },
    (_, i) => i * 30
  );

  const decLines = [-60, -30, 0, 30, 60];

  return (
    <div className="sky-map-panel">
      <div className="sky-map-header">
        <div>
          <div className="eyebrow">CELESTIAL COORDINATE MAP</div>
          <h2>Explore the Sky</h2>
          <p>
            Explore actual NASA SPHEREx observation
            footprints using celestial coordinates.
          </p>
        </div>
      </div>

      {loading && <p>Loading NASA observation map...</p>}

      {error && (
        <p className="observation-error">{error}</p>
      )}

      <div className="sky-map-toolbar">
        <button
          type="button"
          onClick={() => setZoom((z) => Math.min(z + 0.5, 3))}
        >
          Zoom +
        </button>

        <button
          type="button"
          onClick={() => setZoom((z) => Math.max(z - 0.5, 1))}
        >
          Zoom -
        </button>

        <button
          type="button"
          onClick={() => setZoom(1)}
        >
          Reset
        </button>
      </div>

      <div className="sky-map-container offline-sky-map">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="xMidYMid meet"
          onClick={handleMapClick}
          style={{
            width: "100%",
            height: "100%",
            cursor: "crosshair",
          }}
        >
          <rect
            width={WIDTH}
            height={HEIGHT}
            fill="#080d1d"
          />

          <g
            transform={`translate(${WIDTH / 2} ${HEIGHT / 2}) scale(${zoom}) translate(${-WIDTH / 2} ${-HEIGHT / 2})`}
          >
            {raLines.map((ra) => {
              const x = project(ra, 0).x;

              return (
                <g key={`ra-${ra}`}>
                  <line
                    x1={x}
                    y1={0}
                    x2={x}
                    y2={HEIGHT}
                    stroke="#28324b"
                    strokeWidth="1"
                  />

                  <text
                    x={x + 5}
                    y={18}
                    fill="#8796b7"
                    fontSize="12"
                  >
                    {ra}°
                  </text>
                </g>
              );
            })}

            {decLines.map((dec) => {
              const y = project(0, dec).y;

              return (
                <g key={`dec-${dec}`}>
                  <line
                    x1={0}
                    y1={y}
                    x2={WIDTH}
                    y2={y}
                    stroke="#28324b"
                    strokeWidth="1"
                  />

                  <text
                    x={8}
                    y={y - 5}
                    fill="#8796b7"
                    fontSize="12"
                  >
                    {dec}°
                  </text>
                </g>
              );
            })}

            {polygons.map(({ observation, points }) => {
              const center = project(
                observation.center_ra,
                observation.center_dec
              );

              return (
                <g
                  key={observation.id}
                  onClick={(event) => {
                    event.stopPropagation();
                    selectObservation(observation);
                  }}
                  style={{ cursor: "pointer" }}
                >
                  <polygon
                    points={points}
                    fill="#a78bfa"
                    fillOpacity="0.25"
                    stroke="#c4b5fd"
                    strokeWidth="2"
                  />

                  <circle
                    cx={center.x}
                    cy={center.y}
                    r={5}
                    fill="#f5d0fe"
                  />
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {selected && (
        <div className="sky-map-selection">
          <strong>Selected Coordinates</strong>
          <p>
            RA: {Number(selected.center_ra).toFixed(6)}°
            {" | "}
            Dec: {Number(selected.center_dec).toFixed(6)}°
          </p>
        </div>
      )}

      <p className="data-disclaimer">
        Displaying {observations.length} indexed NASA
        SPHEREx observations on an equirectangular
        celestial coordinate map. This is a coordinate
        visualization, not a photographic sky survey.
        Coverage is limited to the indexed observations.
      </p>
    </div>
  );
}
