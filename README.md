
# Cosmic Find
### Explore the Universe. Discover What Changes.

Cosmic Find is an interactive web application that helps users
explore real NASA SPHEREx infrared observations, investigate
astronomical targets, and compare images of the same sky region
captured at different times.

Built as an independent project for the NASA Space Apps
Challenge 2026.

## Project Overview

NASA's SPHEREx mission provides valuable infrared observations
of the universe. However, astronomical FITS files, celestial
coordinates, and scientific image processing can be difficult
for beginners to understand.

Cosmic Find makes this data more accessible through an
interactive, beginner-friendly web interface.

Users can:
- Search the sky using celestial coordinates.
- Explore astronomical targets.
- View real NASA infrared images.
- Examine observations captured at different times.
- Generate WCS-aligned astronomical time-lapses.
- Investigate candidate brightness differences.

## Key Features

### 1. Astronomical Target Explorer
Explore predefined astronomical targets including:
- Barnard's Star
- Epsilon Indi B
- WISE 0855
- RW Aurigae
- R Draconis

### 2. Interactive Celestial Coordinate Map
Visualize the footprints of indexed SPHEREx observations
using right ascension and declination.

The map uses an equirectangular coordinate visualization,
not a photographic sky survey.

### 3. NASA Observation Search
Search indexed observations by:
- Right Ascension (RA)
- Declination (Dec)

The application uses FITS World Coordinate System (WCS)
information to determine whether an observation covers
the requested sky position.

### 4. Real NASA Infrared Image Viewer
Display actual NASA SPHEREx FITS pixel data as grayscale
images with zoom controls and observation metadata.

### 5. Observation Timeline
Explore multiple observations covering the same sky region.

Features include:
- Previous and Next controls
- Play and Pause
- Playback speed selection
- Frame navigation
- Observation timestamps

### 6. Cosmic Change Analyzer
Compare multiple observations using scientific image
processing techniques.

The analyzer:
- Reads real SPHEREx FITS pixel data.
- Uses celestial WCS coordinates for image alignment.
- Resamples images onto a common coordinate grid.
- Generates aligned image frames.
- Creates an animated GIF.
- Calculates exploratory image differences.
- Highlights candidate residual pixels.
- Produces an automated scientific summary.

## Verified Demonstration

Demo coordinates:

Right Ascension: 321.194433°
Declination: 24.181670°

Dataset: NASA/IPAC SPHEREx QR3
Observation date: May 14, 2026

Results from the indexed demonstration dataset:

- Matching observations: 4
- WCS-aligned frames: 4
- Common pixels: 65,516
- Candidate residual pixels: 2,949
- Exploratory threshold: 5 sigma

These residual pixels are not confirmed astronomical
discoveries. They may include instrumental noise,
calibration differences, and image-processing artifacts.

## Technology Stack

### Frontend
- React
- Vite
- JavaScript
- HTML
- CSS

### Backend
- Python
- FastAPI
- Uvicorn

### Scientific Processing
- Astropy
- NumPy
- Pillow
- FITS
- World Coordinate System (WCS)

### Data Source
NASA/IPAC public SPHEREx infrared observation archive.

## Project Structure

cosmic_find/
├── backend/
│   ├── main.py
│   ├── archive.py
│   ├── image_processor.py
│   └── temporal_analysis.py
├── src/
│   ├── App.jsx
│   ├── App.css
│   ├── SkyMap.jsx
│   ├── ObservationTimeline.jsx
│   └── TemporalAnalysis.jsx
├── package.json
└── README.md

## Installation and Setup

### Prerequisites

- Node.js and npm
- Python 3.10 or later
- Internet connection for retrieving NASA data

### 1. Clone the Repository

git clone YOUR_GITHUB_REPOSITORY_URL

cd cosmic_find

Replace YOUR_GITHUB_REPOSITORY_URL with the actual
repository URL after publishing the project.

### 2. Install Frontend Dependencies

npm install

### 3. Install Backend Dependencies

cd backend

python -m venv .venv

On Windows:

.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" requests numpy astropy Pillow

### 4. Start the Backend

From the backend directory:

.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

Backend URL:
http://127.0.0.1:8000

API documentation:
http://127.0.0.1:8000/docs

### 5. Start the Frontend

Open another terminal in the project root:

npm.cmd install

npm.cmd run dev

Frontend URL:
http://localhost:5173

## How to Try the Demo

1. Open Cosmic Find in your browser.
2. Scroll to "See the Universe Change Over Time".
3. Click "Launch Live NASA Demo".
4. Explore the four matching SPHEREx observations.
5. Use Play Time-Lapse to view the observation sequence.
6. Click Analyze Changes in Cosmic Change Analyzer.
7. Inspect the WCS-aligned GIF and candidate difference map.
8. Review the automated scientific summary.

## Scientific Limitations

Cosmic Find is an exploratory educational prototype.

- The indexed dataset is a limited subset of NASA observations.
- A missing search result does not imply NASA never observed
  that sky region.
- The timeline does not independently align its full-frame images.
- The scientific comparison uses WCS-based resampling.
- Difference thresholding does not constitute source detection.
- The analysis does not perform full PSF matching, background
  matching, uncertainty propagation, or artifact rejection.
- Candidate brightness differences are not confirmed discoveries.

## Future Improvements

- Expand coverage to more SPHEREx observations and detectors.
- Integrate additional astronomical catalogs.
- Add source detection and photometric measurements.
- Improve artifact rejection and uncertainty analysis.
- Provide accessible educational explanations.
- Support deployment for public use.

## Data Attribution

Astronomical observation data:
NASA/IPAC SPHEREx public archive.

Cosmic Find is an independent educational prototype and
is not an official NASA application.

## NASA Space Apps Challenge 2026

Project: Cosmic Find

Mission: Make real astronomical data easier to explore
and support educational investigation of changes in
infrared observations.
