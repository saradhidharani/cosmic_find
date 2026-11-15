
"""Cosmic Find API — NASA SPHEREx observation explorer."""

from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from temporal_analysis import analyze_region, analysis_file

from archive import (
    SAMPLE_KEY,
    contains,
    ensure_sample,
    inspect,
    load_index,
    public_record,
    refresh_index,
)
from image_processor import generate_observation_image


executor = ThreadPoolExecutor(max_workers=2)
_index_lock = Lock()
_index_running = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    executor.shutdown(wait=False)


app = FastAPI(
    title="Cosmic Find API",
    description="Explore real NASA SPHEREx infrared observations.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "application": "Cosmic Find",
        "message": "Welcome to Cosmic Find API!",
        "status": "running",
        "version": "2.0.0",
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "indexed_observations": len(load_index()),
    }


@app.get("/api/observations/sample")
def sample_observation():
    try:
        records = ensure_sample()
        record = next(
            item for item in records
            if item["id"] == SAMPLE_KEY
        )
        return {
            **public_record(record),
            "data_status": "real_nasa_observation",
            "is_latest": False,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"NASA archive unavailable: {exc}",
        )


@app.get("/api/observations/sample/image")
def sample_image():
    try:
        records = ensure_sample()
        record = next(
            item for item in records
            if item["id"] == SAMPLE_KEY
        )
        path = generate_observation_image(
            SAMPLE_KEY,
            record,
        )
        return FileResponse(
            path,
            media_type="image/png",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )


@app.get("/api/observations")
def observations():
    records = load_index()

    return {
        "observations": [
            public_record(r) for r in records
        ],
        "count": len(records),
        "coverage": (
            "Limited indexed NASA SPHEREx observations. "
            "Not a complete archive search."
        ),
    }


@app.get("/api/observations/search")
def search_observations(
    ra: float = Query(..., ge=0, lt=360),
    dec: float = Query(..., ge=-90, le=90),
):
    try:
        records = ensure_sample()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    matches = [
        public_record(record)
        for record in records
        if contains(record, ra, dec)
    ]

    return {
        "query": {
            "ra": ra,
            "dec": dec,
        },
        "matches": matches,
        "count": len(matches),
        "indexed_count": len(records),
        "coverage": (
            "Matches only observations in the local "
            "limited index, not the full SPHEREx archive."
        ),
    }


@app.get("/api/observations/image")
def observation_image(
    key: str = Query(...),
):
    records = load_index()

    record = next(
        (r for r in records if r["id"] == key),
        None,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Observation is not in the local index",
        )

    try:
        path = generate_observation_image(
            key,
            record,
        )

        return FileResponse(
            path,
            media_type="image/png",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to render NASA image: {exc}",
        )



def _background_index(limit: int):
    global _index_running

    try:
        print("NASA indexing started...", flush=True)

        result = refresh_index(limit)

        print("NASA indexing result:", result, flush=True)

    except Exception as exc:
        print(
            f"NASA indexing failed: {type(exc).__name__}: {exc}",
            flush=True,
        )

    finally:
        with _index_lock:
            _index_running = False

        print("NASA indexing finished.", flush=True)



@app.post("/api/observations/index")
def start_index(
    limit: int = Query(16, ge=1, le=24),
):
    global _index_running

    with _index_lock:
        if _index_running:
            return {
                "status": "already_running",
                "indexed_count": len(load_index()),
            }

        _index_running = True

    try:
        executor.submit(
            _background_index,
            limit,
        )
    except Exception:
        with _index_lock:
            _index_running = False
        raise

    return {
        "status": "started",
        "indexed_count": len(load_index()),
        "message": (
            "Indexing NASA observations in the background. "
            "Check /api/observations/index/status for progress."
        ),
    }


@app.get("/api/observations/index/status")
def index_status():
    with _index_lock:
        running = _index_running

    return {
        "status": "running" if running else "idle",
        "indexed_count": len(load_index()),
        "coverage": (
            "Limited QR3 archive subset; "
            "not full-sky coverage."
        ),
    }

@app.get("/api/temporal/analyze")
def temporal_analyze(
    ra: float = Query(..., ge=0, lt=360),
    dec: float = Query(..., ge=-90, le=90),
):
    try:
        return analyze_region(ra, dec)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Temporal analysis failed: {exc}",
        )


@app.get("/api/temporal/files/{analysis_id}/{filename}")
def temporal_file(analysis_id: str, filename: str):
    try:
        path = analysis_file(analysis_id, filename)

        media_type = (
            "image/gif"
            if filename.endswith(".gif")
            else "image/png"
        )

        return FileResponse(
            path,
            media_type=media_type,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )
