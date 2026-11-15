
import { useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8000";

function imageUrl(observation) {
  return `${API}/api/observations/image?${new URLSearchParams({
    key: observation.file_key,
  })}`;
}

function formatDate(date) {
  if (!date) return "Unknown timestamp";

  const parsed = new Date(date + (date.endsWith("Z") ? "" : "Z"));

  return Number.isNaN(parsed.getTime())
    ? date
    : parsed.toLocaleString("en-IN", {
        timeZone: "UTC",
        dateStyle: "medium",
        timeStyle: "medium",
      }) + " UTC";
}

export default function ObservationTimeline({ ra, dec }) {
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1200);

  useEffect(() => {
    const controller = new AbortController();

    async function loadTimeline() {
      const rightAscension = Number(ra);
      const declination = Number(dec);

      if (
        !Number.isFinite(rightAscension) ||
        !Number.isFinite(declination) ||
        rightAscension < 0 ||
        rightAscension >= 360 ||
        declination < -90 ||
        declination > 90
      ) {
        setObservations([]);
        return;
      }

      setLoading(true);
      setError("");
      setPlaying(false);
      setFrame(0);

      try {
        const params = new URLSearchParams({
          ra: String(rightAscension),
          dec: String(declination),
        });

        const response = await fetch(
          `${API}/api/observations/search?${params}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("Unable to load observation timeline");
        }

        const data = await response.json();

        setObservations(
          [...(data.matches || [])].sort((a, b) =>
            String(a.observation_date || "").localeCompare(
              String(b.observation_date || "")
            )
          )
        );
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadTimeline();

    return () => controller.abort();
  }, [ra, dec]);

  const distinctDates = useMemo(
    () =>
      new Set(
        observations
          .map((observation) => observation.observation_date)
          .filter(Boolean)
      ).size,
    [observations]
  );

  const canAnimate =
    observations.length >= 2 && distinctDates >= 2;

  useEffect(() => {
    if (!playing || !canAnimate) return;

    const timer = setInterval(() => {
      setFrame((current) =>
        (current + 1) % observations.length
      );
    }, speed);

    return () => clearInterval(timer);
  }, [playing, canAnimate, observations.length, speed]);

  const active = observations[frame];

  return (
    <section className="timeline-panel" id="timeline">
      <div className="eyebrow">
        SPHEREX TEMPORAL EXPLORER
      </div>

      <h2>NASA Observation Timeline</h2>

      <p>
        Explore real infrared observations covering
        RA {ra}°, Dec {dec}°.
      </p>

      {loading && <p>Loading observation timeline...</p>}

      {error && (
        <p className="observation-error">{error}</p>
      )}

      {!loading && observations.length === 0 && (
        <p>
          No indexed NASA observations cover these
          coordinates.
        </p>
      )}

      {!loading && observations.length > 0 && (
        <>
          <div className="timeline-stats">
            <span>
              Observations: <strong>{observations.length}</strong>
            </span>

            <span>
              Distinct timestamps: <strong>{distinctDates}</strong>
            </span>
          </div>

          {active && (
            <div className="timeline-image-wrapper">
              <img
                key={active.file_key}
                src={imageUrl(active)}
                alt="Real NASA SPHEREx infrared observation"
                className="timeline-image"
              />

              <div className="timeline-date">
                {formatDate(active.observation_date)}
              </div>
            </div>
          )}

          <div className="timeline-controls">
            <button
              type="button"
              onClick={() => {
                setPlaying(false);
                setFrame((current) =>
                  Math.max(0, current - 1)
                );
              }}
              disabled={frame === 0}
            >
              Previous
            </button>

            <button
              type="button"
              onClick={() => setPlaying((value) => !value)}
              disabled={!canAnimate}
            >
              {playing ? "Pause" : "Play Time-Lapse"}
            </button>

            <button
              type="button"
              onClick={() => {
                setPlaying(false);
                setFrame((current) =>
                  Math.min(
                    observations.length - 1,
                    current + 1
                  )
                );
              }}
              disabled={frame >= observations.length - 1}
            >
              Next
            </button>

            <select
              value={speed}
              onChange={(event) =>
                setSpeed(Number(event.target.value))
              }
            >
              <option value={2000}>Slow</option>
              <option value={1200}>Normal</option>
              <option value={500}>Fast</option>
            </select>
          </div>

          <input
            type="range"
            min="0"
            max={Math.max(0, observations.length - 1)}
            value={frame}
            onChange={(event) => {
              setPlaying(false);
              setFrame(Number(event.target.value));
            }}
            disabled={observations.length < 2}
            className="timeline-slider"
          />

          <p className="data-disclaimer">
            Frame {frame + 1} of {observations.length}.
            Detector: {active?.detector ?? "Unknown"}.
            Each frame is a real NASA SPHEREx image.
          </p>

          {!canAnimate && (
            <p className="timeline-warning">
              A genuine time-lapse needs at least two
              observations with different timestamps
              covering the same coordinates.
              The current index does not provide
              enough observations for this location.
            </p>
          )}

          {canAnimate && (
            <p className="data-disclaimer">
              This is a timestamped image sequence,
              not an aligned scientific difference
              analysis. Changes in framing, detector,
              or brightness scaling may affect
              appearance.
            </p>
          )}
        </>
      )}
    </section>
  );
}
