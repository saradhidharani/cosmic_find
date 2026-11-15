
import { useEffect, useState } from "react";
import "./App.css";
import SkyMap from "./SkyMap";
import ObservationTimeline from "./ObservationTimeline";
import TemporalAnalysis from "./TemporalAnalysis";

const API = "http://127.0.0.1:8000";

const targets = [
  {
    name: "Barnard's Star",
    type: "Nearby red dwarf",
    ra: 269.452,
    dec: 4.693,
    description: "A nearby star with measurable proper motion.",
  },
  {
    name: "Epsilon Indi B",
    type: "Brown dwarf system",
    ra: 331.042,
    dec: -56.785,
    description: "A nearby substellar system.",
  },
  {
    name: "WISE 0855",
    type: "Cold brown dwarf",
    ra: 133.795,
    dec: -7.245,
    description: "An extremely cold brown dwarf.",
  },
  {
    name: "RW Aurigae",
    type: "Young stellar system",
    ra: 76.954,
    dec: 30.401,
    description: "A young variable stellar system.",
  },
  {
    name: "R Draconis",
    type: "Variable star",
    ra: 240.396,
    dec: 66.801,
    description: "A pulsating variable star.",
  },
  {
    name: "NASA SPHEREx Sample",
    type: "Verified infrared observation",
    ra: 327.985123,
    dec: -48.703783,
    description:
      "A verified observation from NASA's SPHEREx public archive.",
  },
];

function App() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(targets[5]);
  const [ra, setRa] = useState("327.985123");
  const [dec, setDec] = useState("-48.703783");

  const [matches, setMatches] = useState([]);
  const [activeObservation, setActiveObservation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const [zoom, setZoom] = useState(1);
  const [indexStatus, setIndexStatus] = useState(null);
  const [indexing, setIndexing] = useState(false);

  const filteredTargets = targets.filter((target) =>
    target.name.toLowerCase().includes(search.toLowerCase())
  );

  async function searchObservations(nextRa, nextDec) {
    const numericRa = Number(nextRa);
    const numericDec = Number(nextDec);

    if (
      !Number.isFinite(numericRa) ||
      !Number.isFinite(numericDec) ||
      String(nextRa).trim() === "" ||
      String(nextDec).trim() === "" ||
      numericRa < 0 ||
      numericRa >= 360 ||
      numericDec < -90 ||
      numericDec > 90
    ) {
      setError("Enter valid RA (0–360°) and Dec (-90° to 90°).");
      return;
    }

    setLoading(true);
    setError("");
    setMatches([]);
    setActiveObservation(null);
    setSearched(false);
    setZoom(1);

    try {
      const url =
        `${API}/api/observations/search?` +
        new URLSearchParams({
          ra: String(numericRa),
          dec: String(numericDec),
        });

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`NASA search API returned ${response.status}`);
      }

      const data = await response.json();

      setMatches(data.matches || []);
      setActiveObservation(data.matches?.[0] || null);
      setSearched(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function chooseTarget(target) {
    setSelected(target);
    setRa(String(target.ra));
    setDec(String(target.dec));

    searchObservations(target.ra, target.dec);

    document.getElementById("observations")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  async function refreshIndexStatus() {
    try {
      const response = await fetch(
        `${API}/api/observations/index/status`
      );

      if (!response.ok) return;

      const data = await response.json();

      setIndexStatus(data);
      setIndexing(data.status === "running");
    } catch {
      // Keep the existing status when the backend is unavailable.
    }
  }

  async function expandIndex() {
    try {
      setError("");

      const response = await fetch(
        `${API}/api/observations/index?limit=16`,
        { method: "POST" }
      );

      if (!response.ok) {
        throw new Error("Unable to start NASA indexing.");
      }

      setIndexing(true);
      await refreshIndexStatus();
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    searchObservations(327.985123, -48.703783);
    refreshIndexStatus();
  }, []);

  useEffect(() => {
    if (!indexing) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `${API}/api/observations/index/status`
        );

        if (!response.ok) return;

        const data = await response.json();

        setIndexStatus(data);

        if (data.status !== "running") {
          setIndexing(false);
        }
      } catch {
        // Try again on the next poll.
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [indexing]);

  const imageUrl = activeObservation
    ? `${API}/api/observations/image?${new URLSearchParams({
        key: activeObservation.file_key,
      })}`
    : "";

  return (
    <div className="app">
      <header className="navbar">
        <a href="#explore" className="brand">
          <span className="brand-icon">✦</span>
          Cosmic<span>Find</span>
        </a>

        <nav className="nav-links">
          <a href="#explore">Explore</a>
          <a href="#targets">Targets</a>
          <a href="#sky-map">Sky Map</a>
          <a href="#observations">Observations</a>
          <a href="#about">About</a>
        </nav>
      </header>

      <main>
        <section className="hero" id="explore">
          <div className="eyebrow">NASA SPHEREx DATA EXPLORER</div>

          <h1>
            Explore the Universe.
            <br />
            <span>Discover What Changes.</span>
          </h1>

          <p>
            Search real NASA SPHEREx infrared observations,
            explore astronomical targets, and investigate
            the sky through scientific data.
          </p>

          <a className="primary-button" href="#targets">
            Start Exploring →
          </a>
        </section>

        <section className="targets-section" id="targets">
          <div className="section-heading">
            <div>
              <div className="eyebrow">EXPLORE THE SKY</div>
              <h2>Astronomical Targets</h2>
              <p>
                Select a target to search our indexed NASA
                SPHEREx observations.
              </p>
            </div>
          </div>

          <div className="explorer-layout">
            <div className="target-panel">
              <div className="search-box">
                <span>⌕</span>
                <input
                  type="text"
                  placeholder="Search astronomical targets..."
                  value={search}
                  onChange={(event) =>
                    setSearch(event.target.value)
                  }
                />
              </div>

              <div className="target-list">
                {filteredTargets.map((target) => (
                  <button
                    key={target.name}
                    className={`target-item ${
                      selected.name === target.name
                        ? "active"
                        : ""
                    }`}
                    onClick={() => chooseTarget(target)}
                  >
                    <span className="target-symbol">✧</span>

                    <span className="target-info">
                      <strong>{target.name}</strong>
                      <small>{target.type}</small>
                    </span>

                    <span className="target-arrow">↗</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="detail-panel">
              <div className="eyebrow">SELECTED TARGET</div>

              <h2>{selected.name}</h2>

              <p>{selected.description}</p>

              <div className="coordinates-grid">
                <div>
                  <small>RIGHT ASCENSION</small>
                  <strong>{selected.ra}°</strong>
                </div>

                <div>
                  <small>DECLINATION</small>
                  <strong>{selected.dec}°</strong>
                </div>
              </div>

              <button
                className="secondary-button"
                onClick={() => chooseTarget(selected)}
              >
                Search NASA Observations →
              </button>
            </div>
          </div>
        </section>

        <section className="sky-map-section" id="sky-map">
          <SkyMap
            onSelectCoordinates={(mapRa, mapDec) => {
              setRa(mapRa.toFixed(6));
              setDec(mapDec.toFixed(6));

              searchObservations(mapRa, mapDec);

              document
                .getElementById("observations")
                ?.scrollIntoView({ behavior: "smooth" });
            }}
          />
        </section>

        <section
          className="nasa-observation"
          id="observations"
        >
          <div className="section-heading">
            <div>
              <div className="eyebrow">REAL NASA DATA</div>
              <h2>SPHEREx Observation Explorer</h2>

              <p>
                Search by sky coordinates and view verified
                NASA infrared observation images.
              </p>
            </div>
          </div>

          <div className="coordinate-search">
            <h3>Search Sky Coordinates</h3>

            <div className="coordinate-inputs">
              <label>
                Right Ascension (degrees)
                <input
                  type="number"
                  min="0"
                  max="359.999999"
                  step="any"
                  value={ra}
                  onChange={(event) =>
                    setRa(event.target.value)
                  }
                />
              </label>

              <label>
                Declination (degrees)
                <input
                  type="number"
                  min="-90"
                  max="90"
                  step="any"
                  value={dec}
                  onChange={(event) =>
                    setDec(event.target.value)
                  }
                />
              </label>

              <button
                className="primary-button"
                disabled={loading}
                onClick={() => searchObservations(ra, dec)}
              >
                {loading ? "Searching..." : "Search NASA"}
              </button>
            </div>

            <p className="data-disclaimer">
              Searches only our limited local index of
              real NASA observations. No match does not
              mean the target was never observed.
            </p>
          </div>

          {error && (
            <p className="observation-error">
              {error}
            </p>
          )}

          {loading && (
            <p>Searching verified SPHEREx footprints...</p>
          )}

          {searched && !loading && (
            <div className="search-results-summary">
              <strong>{matches.length}</strong>
              {" "}matching observation(s) found
              in the indexed dataset.
            </div>
          )}

          {matches.length > 1 && (
            <div className="observation-selector">
              {matches.map((observation, index) => (
                <button
                  key={observation.id}
                  className={
                    activeObservation?.id === observation.id
                      ? "active"
                      : ""
                  }
                  onClick={() => {
                    setActiveObservation(observation);
                    setZoom(1);
                  }}
                >
                  Observation {index + 1}
                  {" · "}
                  {observation.observation_date || "Unknown date"}
                </button>
              ))}
            </div>
          )}

          {activeObservation && (
            <div className="observation-details">
              <div className="nasa-image-container">
                <div className="image-toolbar">
                  <strong>SPHEREx Infrared Image</strong>

                  <label>
                    Zoom: {zoom.toFixed(1)}×
                    <input
                      type="range"
                      min="1"
                      max="3"
                      step="0.1"
                      value={zoom}
                      onChange={(event) =>
                        setZoom(Number(event.target.value))
                      }
                    />
                  </label>

                  <button
                    className="secondary-button"
                    onClick={() => setZoom(1)}
                  >
                    Reset
                  </button>
                </div>

                <div className="image-viewport">
                  <img
                    src={imageUrl}
                    alt="Real NASA SPHEREx infrared observation"
                    className="nasa-image"
                    style={{
                      transform: `scale(${zoom})`,
                      transformOrigin: "center center",
                    }}
                  />
                </div>

                <p className="image-caption">
                  Actual infrared pixel data from NASA/IPAC
                  SPHEREx, rendered as a grayscale image.
                  This observation's WCS footprint contains
                  the searched sky coordinates.
                </p>
              </div>

              <div className="observation-metadata">
                <h3>Observation Details</h3>

                <p>
                  <strong>Source:</strong>{" "}
                  {activeObservation.source}
                </p>

                <p>
                  <strong>Dataset:</strong>{" "}
                  {activeObservation.dataset}
                </p>

                <p>
                  <strong>Observation date:</strong>{" "}
                  {activeObservation.observation_date || "Unknown"}
                </p>

                <p>
                  <strong>Center RA:</strong>{" "}
                  {activeObservation.center_ra}°
                </p>

                <p>
                  <strong>Center Dec:</strong>{" "}
                  {activeObservation.center_dec}°
                </p>

                <p>
                  <strong>Detector:</strong>{" "}
                  {activeObservation.detector ?? "Unknown"}
                </p>

                <p>
                  <strong>Resolution:</strong>{" "}
                  {activeObservation.width} ×{" "}
                  {activeObservation.height}
                </p>

                <p>
                  <strong>Brightness unit:</strong>{" "}
                  {activeObservation.brightness_unit}
                </p>
              </div>
            </div>
          )}

          {searched &&
            !loading &&
            matches.length === 0 && (
              <div className="no-observations">
                <h3>No indexed observations found</h3>
                <p>
                  This target does not fall inside the
                  observations currently indexed.
                  Expand the index to search more available
                  NASA FITS files.
                </p>
              </div>
            )}

          <div className="index-controls">
            <h3>NASA Observation Index</h3>

            <p>
              Indexed observations:{" "}
              <strong>
                {indexStatus?.indexed_count ?? "Loading..."}
              </strong>
            </p>

            <button
              className="secondary-button"
              disabled={indexing}
              onClick={expandIndex}
            >
              {indexing
                ? "Indexing NASA Observations..."
                : "Expand NASA Observation Index"}
            </button>

            <p className="data-disclaimer">
              Indexing scans a limited subset of NASA's
              public QR3 archive and may take several minutes.
            </p>

            {!indexing && (
              <button
                className="text-button"
                onClick={refreshIndexStatus}
              >
                Refresh Index Status
              </button>
            )}
          </div>
        </section>
     
        <section className="live-demo-section" id="live-demo">
          <div className="live-demo-content">
            <div className="eyebrow">
              VERIFIED NASA DATA DEMONSTRATION
            </div>

            <h2>See the Universe Change Over Time</h2>

            <p>
              Explore four overlapping NASA SPHEREx infrared
              observations captured on May 14, 2026.
              Compare WCS-aligned images, inspect candidate
              brightness differences, and generate a real
              astronomical time-lapse.
            </p>

            <div className="live-demo-details">
              <span>4 NASA observations</span>
              <span>Same sky coordinates</span>
              <span>WCS-aligned comparison</span>
            </div>

            <button
              type="button"
              className="live-demo-button"
              onClick={() => {
              const demoRa = 321.194433;
              const demoDec = 24.18167;

              // Update coordinate inputs.
              setRa(String(demoRa));
              setDec(String(demoDec));

              // Search the verified overlapping observations.
              searchObservations(demoRa, demoDec);

              // Navigate immediately to the timeline.
              window.location.hash = "timeline";

              document
                .getElementById("timeline")
                ?.scrollIntoView({
                  behavior: "smooth",
                  block: "start",
                });
            }}
            >
              Launch Live NASA Demo
            </button>
          </div>
        </section>

        <ObservationTimeline ra={ra} dec={dec} />
        <TemporalAnalysis ra={ra} dec={dec} />

        <section className="about-section" id="about">
          <div className="eyebrow">OUR MISSION</div>

          <h2>Making Space Data Accessible</h2>

          <p>
            Cosmic Find helps students, researchers, and
            curious explorers discover astronomical
            observations through an intuitive interface.
          </p>

          <p>
            Built using real publicly available NASA/IPAC
            SPHEREx infrared observation data.
          </p>
        </section>
      </main>

      <footer>
        Cosmic Find · NASA Space Apps Challenge 2026
        <br />
        Independent educational prototype using NASA/IPAC data.
      </footer>
    </div>
  );
}

export default App;
