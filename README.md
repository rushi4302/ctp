# Civic Intelligence Platform 🏙️

An intelligent, end-to-end civic engagement and municipal resolution platform. Citizens can report neighborhood grievances with photos, GPS coordinates, and descriptions. The system automatically validates locations, extracts EXIF metadata, runs offline multimodal AI models (XLM-RoBERTa for complaint text and MobileNet TFLite for civic issue images), and routes reports to municipal authorities for verification, action, and resolution.

---

## Architecture Overview

```mermaid
flowchart TD
    Citizen([Citizen App - Flutter]) -->|Report + Image + GPS| FastAPI[FastAPI Backend :8000]
    FastAPI --> Storage[Secure Local Storage /uploads]
    FastAPI --> EXIF[EXIF Metadata & GPS Extraction]
    FastAPI --> LocationVal[Location & Geofence Validator]
    FastAPI --> AIService[Multimodal AI Engine]
    
    subgraph AI Engine
        AIService --> XLM[XLM-RoBERTa NLP Classifier]
        AIService --> TFLite[Civic MobileNet TFLite]
        AIService --> YOLO[Pretrained YOLOv8n]
    end
    
    FastAPI --> PostgreSQL[(PostgreSQL :5432)]
    PostgreSQL --> Admin([Municipal Authority Dashboard])
    Admin -->|Status Transitions & Remarks| FastAPI
```

---

## Key Features

1. **Citizen Experience**:
   - Authentication (Registration, JWT Login, Password Reset, Secure Session).
   - Issue reporting with camera capture or gallery selection.
   - GPS coordinate acquisition and address geocoding.
   - Real-time AI category recommendation ("AI Auto-Detect").
   - Feed of community issues, personal submitted reports ("My Reports"), and interactive map.
   - Community upvoting (strictly 1 vote per user) and discussion comments.

2. **Multimodal Civic AI Engine**:
   - **XLM-RoBERTa Civic Classifier**: Classifies grievance text across key municipal categories (`Pothole/Road Damage`, `Garbage`, `Water Leakage`, `Streetlight Issue`, `Drainage Problem`, `Traffic Issue`).
   - **Civic TFLite Classifier**: Classifies issue photos into civic categories (`Pothole/Road Damage`, `Garbage`, `Drainage Problem`).
   - **Lazy Loading & In-Memory Caching**: Heavy models are initialized on demand and cached; inference runs without reloading 1GB weights per request.
   - **Graceful Fallbacks**: Explicit error handling and fallback states if models are temporarily unavailable.

3. **Image & Location Pipeline**:
   - MIME validation (JPEG, PNG) and file size limits (configurable, default 10MB).
   - Safe UUID filename generation preventing directory traversal attacks.
   - EXIF GPS extraction (`DateTimeOriginal`, GPS coordinates in decimal degrees).
   - **Location Validation Engine**:
     - `VALID`: Coordinates inside jurisdiction and consistent with photo EXIF.
     - `MISSING_METADATA`: Photo lacks GPS (report is accepted and marked for manual review).
     - `FLAGGED_FOR_REVIEW`: Photo EXIF GPS differs from submitted device GPS beyond threshold (default 500m) or is outside municipal target boundary.
     - `INVALID`: Malformed or out-of-range latitude/longitude.

4. **Municipal Governance & Administrative Portal**:
   - Real-time municipal dashboard displaying jurisdiction stats (Total, Submitted, Verified, In Progress, Resolved, Rejected, Flagged).
   - Category distribution statistics.
   - Filterable report management table.
   - Formal status transition workflows:
     - `SUBMITTED` ➔ `VERIFIED` ➔ `IN_PROGRESS` ➔ `RESOLVED` / `REJECTED` / `FLAGGED`.
   - Immutable audit logging: every status transition records a `ReportStatusLog` with timestamp, officer identity, and official remark.

---

## Technology Stack

- **Backend**: FastAPI, Python 3.12/3.14, SQLAlchemy 2.0, Alembic, Pydantic v2, Python-Jose (JWT), Passlib (Bcrypt).
- **Database**: PostgreSQL 17 (Docker container `civic_postgres`).
- **AI / ML**: PyTorch, HuggingFace Transformers (XLM-RoBERTa), Google LiteRT / TFLite, Ultralytics YOLOv8, Pillow.
- **Frontend**: Flutter 3.47 (Dart 3.13), Flutter Riverpod, GoRouter, Dio, Flutter Secure Storage, Google Maps Flutter, Geolocator, Image Picker.
- **DevOps**: Docker, Docker Compose, Pytest.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # Auth, Reports, Municipality, AI
│   │   ├── core/              # Config, Security, Roles, Constants
│   │   ├── dependencies/      # DB, Auth, Role guards
│   │   ├── models/            # SQLAlchemy models (User, Report, Media, StatusLog, Comment, Upvote)
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── services/          # ReportService, AIService, ExifService, LocationService, StorageService
│   │   └── validators/        # Image & Location validators
│   ├── migrations/            # Alembic database migrations
│   ├── tests/                 # Full pytest suite (Auth, Reports, Upload, Location, AI)
│   └── uploads/               # Safe local media storage
├── frontend/
│   ├── lib/
│   │   ├── app/router/        # GoRouter routes and auth redirect guards
│   │   ├── core/              # ApiClient, TokenStorage, AppColors, ApiConstants
│   │   ├── features/
│   │   │   ├── auth/          # Login, Register, Forgot Password
│   │   │   ├── feed/          # Home Dashboard, My Reports, Report Detail
│   │   │   ├── post/          # Create Report (Camera, GPS, AI Suggestion)
│   │   │   ├── maps/          # Interactive map & proximity list
│   │   │   └── municipality/  # Admin Portal, Stats, Status Transitions
│   │   └── shared/models/     # Data models with JSON deserialization
│   └── test/                  # Widget and model unit tests
├── ai/
│   ├── model/                 # civic_nlp_model (XLM-RoBERTa), civic_model.tflite, labels.txt
│   └── test_images/           # Sample test images for validation
└── docker-compose.yml         # PostgreSQL and Backend orchestration
```

---

## Setup & Getting Started

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+ / Python 3.12
- Flutter SDK 3.24+ (Installed on system)

### 2. Environment Variables
Create `backend/.env` (or copy from `.env.example`):
```env
APP_NAME="Civic Intelligence Platform"
APP_VERSION="1.0.0"
DEBUG=true

# PostgreSQL Connection
DATABASE_URL=postgresql://civic_admin:civic_password@localhost:5432/civic_db

# JWT Security
JWT_SECRET_KEY=your-secure-jwt-secret-key-at-least-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# Storage & Uploads
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_BYTES=10485760

# Location Geofence (Pune Urban Area)
CIVIC_TARGET_CITY=Pune
CIVIC_LAT_MIN=18.25
CIVIC_LAT_MAX=18.75
CIVIC_LON_MIN=73.65
CIVIC_LON_MAX=74.15
LOCATION_DISCREPANCY_THRESHOLD_METERS=500.0
```

### 3. Database & Migrations
Ensure the PostgreSQL container is running:
```bash
docker compose up -d postgres
```

Run Alembic migrations:
```bash
cd backend
./venv/bin/alembic current
./venv/bin/alembic heads
./venv/bin/alembic upgrade head
```

### 4. Running the Backend
From the project root:
```bash
cd backend
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API Documentation will be available at: `http://localhost:8000/docs`

### 5. Running the Flutter Frontend
From the `frontend` directory:
```bash
cd frontend
flutter pub get
flutter run -d chrome     # Run on Web
# or
flutter run -d macos      # Run on macOS Desktop
# or
flutter run               # Run on connected iOS/Android device
```

---

## Testing

### Backend Test Suite
Run the 33 comprehensive unit and integration tests:
```bash
PYTHONPATH=backend ./backend/venv/bin/pytest -v backend/tests
```
Tests cover:
- User registration, duplicate checks, password validation.
- Login and JWT authentication.
- Role-based permissions (Citizen, Municipality, Admin).
- Report creation (JSON & multipart image upload).
- Unauthorized editing prevention.
- Image MIME and size validation, path traversal prevention.
- EXIF GPS extraction and location discrepancy calculations.
- AI NLP text classification, TFLite image inference, multimodal consensus.
- Comments and upvote toggling.
- Municipal statistics.

### Flutter Test Suite
Run Flutter unit and widget tests:
```bash
cd frontend
flutter test
```

Static analysis:
```bash
cd frontend
flutter analyze
```

---

## Complete End-to-End Demo Workflow

1. **Citizen Registration & Login**:
   - Register a new citizen account at `/register` or login at `/login`.
2. **Creating a Report**:
   - Tap **"Report Issue"** (+ button).
   - Enter title and description (e.g., *"Large crater pothole on FC road"*).
   - Attach a photo via Camera or Gallery.
   - Tap **"Detect"** under Multimodal Civic AI — notice the AI model automatically categorizes the grievance as `Pothole/Road Damage` with high confidence!
   - Tap **"Get Current GPS"** to record coordinates.
   - Tap **"Submit Civic Report"**.
3. **Automated Pipeline Processing**:
   - Backend validates image format and saves with a safe UUID in `/uploads`.
   - EXIF data is extracted; location is compared against submitted coordinates.
   - Status is initialized to `SUBMITTED`, initial `ReportStatusLog` is recorded.
4. **Community Engagement**:
   - Citizens can view the report on the Feed or Map.
   - Upvote the issue (enforced 1 upvote per user).
   - Add discussion comments.
5. **Municipal Review & Status Transition**:
   - Municipal officer logs in and visits the **Municipal Governance Portal** (`/municipality`).
   - Reviews live stats and filters jurisdiction issues.
   - Opens report `#1`, inspects AI confidence and location validation status (`VALID`).
   - Clicks **"Update Status"**, selects `VERIFIED` and inputs remark: *"Assigned road inspection unit"*.
   - When roadwork completes, transitions status to `RESOLVED` with remark: *"Tarmac resurfacing completed"*.
6. **Citizen Confirmation**:
   - Citizen opens report detail and sees the updated green `RESOLVED` badge and the complete chronological audit timeline in the **Status Timeline**.