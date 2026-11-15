
import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function TemporalAnalysis({ ra, dec }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runAnalysis() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const params = new URLSearchParams({
        ra: String(ra),
        dec: String(dec),
      });

      const response = await fetch(
        `${API}/api/temporal/analyze?${params}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Temporal analysis failed"
        );
      }

      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function fileUrl(filename) {
    if (!result) return "";

    return `${API}/api/temporal/files/${result.analysis_id}/${filename}`;
  }

  return (
    <section className="temporal-analysis" id="analysis">
      <div className="eyebrow">
        SCIENTIFIC IMAGE COMPARISON
      </div>

      <h2>Cosmic Change Analyzer</h2>

      <p>
        Align real NASA infrared observations using
        celestial coordinates and inspect candidate
        brightness differences.
      </p>

      <button
        type="button"
        className="secondary-button"
        onClick={runAnalysis}
        disabled={loading}
      >
        {loading
          ? "Analyzing NASA FITS Data..."
          : "Analyze Changes"}
      </button>

      {loading && (
        <p>
          Downloading and aligning original NASA
          infrared pixels. This may take a few minutes.
        </p>
      )}

      {error && (
        <p className="observation-error">{error}</p>
      )}

      {result && (
        <>
          <div className="discovery-grid">
            <div>
              <span>Aligned Frames</span>
              <strong>{result.frame_count}</strong>
            </div>

            <div>
              <span>Common Pixels</span>
              <strong>
                {result.comparison.common_pixels.toLocaleString()}
              </strong>
            </div>

            <div>
              <span>Candidate Difference Pixels</span>
              <strong>
                {result.comparison.candidate_pixels.toLocaleString()}
              </strong>
            </div>

            <div>
              <span>Detection Threshold</span>
              <strong>
                {result.comparison.threshold_sigma}σ
              </strong>
            </div>
          </div>

          <h3>WCS-Aligned Time-Lapse</h3>

          <img
            src={fileUrl("timelapse.gif")}
            alt="Aligned NASA SPHEREx time-lapse"
            className="temporal-result-image"
          />

          <p>
            <a
              href={fileUrl("timelapse.gif")}
              download="cosmic-find-timelapse.gif"
              target="_blank"
              rel="noreferrer"
            >
              Download Time-Lapse GIF
            </a>
          </p>

          
        <h3>Aligned Observation Comparison</h3>

        <p>
        Compare the first and last observations using the
        same celestial coordinate grid and brightness scale.
        </p>

        <div className="comparison-grid">
        <div className="comparison-card">
            <h4>First Observation</h4>

            <img
            src={fileUrl("frame_0.png")}
            alt="First WCS-aligned NASA SPHEREx observation"
            />

            <p>
            {result.frames[0]?.timestamp} UTC
            </p>
        </div>

        <div className="comparison-card">
            <h4>Last Observation</h4>

            <img
            src={fileUrl(
                `frame_${result.frame_count - 1}.png`
            )}
            alt="Last WCS-aligned NASA SPHEREx observation"
            />

            <p>
            {result.frames[result.frame_count - 1]?.timestamp} UTC
            </p>
        </div>
        </div>


          <h3>Candidate Difference Map</h3>

          <img
            src={fileUrl("difference.png")}
            alt="Candidate infrared brightness difference map"
            className="temporal-result-image"
          />

          <p className="data-disclaimer">
            Yellow pixels exceed the exploratory
            residual threshold. They do not represent
            confirmed astronomical discoveries.
          </p>

          <h3>Automated Scientific Summary</h3>

          <p>{result.summary}</p>

          <h3>Observation Brightness</h3>

          <div className="temporal-frame-list">
            {result.frames.map((frame) => (
              <div key={frame.index}>
                <strong>
                  Frame {frame.index + 1}
                </strong>

                <span>{frame.timestamp} UTC</span>

                <span>
                  Median: {frame.median_brightness}{" "}
                  {frame.unit || ""}
                </span>
              </div>
            ))}
          </div>

          <p className="data-disclaimer">
            {result.limitations}
          </p>
        </>
      )}
    </section>
  );
}
