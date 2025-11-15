# Temporal Event Prediction API

Application for predicting temporal intervals for recurrent events

---

## Work in Progress

This repository contains work-in-progress code and is not production-ready.
Use at your own risk, and expect frequent change.

---

## Description

This API allows for the prediction of time intervals (start and end) during which recurrent temporal events take place on specific dates.

### Use Cases:

- predict employee work schedules
- Forecasting business opening/closing hours
- Anticipating time slots of availability
- Any recurrent event that has a start and an end time

---

## Features

- Complete isolation: Each session is isolated (data, models, cache)
- Multiple formats: Support for YYYY-MM-DD and DD/MM/YYYY
- Temporal Features: Week of month, week of the year, month, day of the year, weekday occurrence rate, weekday occurrence count, stddev gap between events, periodicity_score
- Robust Predictions: Returns NA if the prediction is not reliable

## Installation

### Prerequisites

- Python **3.12+**
- [Poetry](https://python-poetry.org/)

```bash
git clone https://github.com/EnamSon/work-time-prediction.git
cd work-time-prediction
poetry install
```

---

## Run the server

The server runs at http://127.0.0.1:8000 by default

```bash
poetry run work-time-prediction
```

You can specify another host IP or another port with optional arguments `--host` or `--port`.

---

## Usage workflow

1. Create a session

    ```bash
    SESSION_ID=$(curl -s -X POST "http://127.0.0.1:8000/api/session/create" | jq -r '.session_id')
    echo $SESSION_ID
    ```

### Response:
    ```json
    {
    "session_id": "a1b2c3d4e5f6...",
    "message": "Session created successfully..."
    }
    ```

---

2. Train the model

    ```bash
    curl -X POST "http://127.0.0.1:8000/api/train/" \
    -H "X-Session-ID: $SESSION_ID" \
    -F "file=@data.csv" \
    -F "id_column=ID" \
    -F "date_column=Date" \
    -F "start_time_column=Start Time" \
    -F "end_time_column=End Time"
    ```

### Excepted CSV Format

    ```csv
    ID,Date,Start Time,End Time
    1,2025-01-15,08:30,17:00
    1,2025-01-16,09:00,17:30
    2,2025-01-15,07:45,16:00
    ```

### Supported Date Formats:

- YYYY-MM-DD (ISO): 2025-01-15
- DD/MM/YYYY (European): 15/01/2025

### Response:

    ```json
    {
    "message": "Model trained successfully",
    "session_id": "a1b2c3d4e5f6...",
    "data_points": 1500,
    "entities": 25,
    "trained_at": "2025-01-15T10:30:00"
    }
    ```

---

3. Make predictions

    ```bash
    curl -X POST "http://127.0.0.1:8000/api/predict/" \
    -H "X-Session-ID: $SESSION_ID" \
    -H "Content-Type: application/json" \
    -d '{
        "id": "1",
        "target_date": "23/12/2025",
        "window_size": 3
    }'
    ```

### Response

    ```json
    {
    "predictions": [
        {
        "date": "22/12/2025",
        "weekday": "mon",
        "start_time": "08:30",
        "end_time": "17:00",
        "historical": true
        },
        {
        "date": "23/12/2025",
        "weekday": "tue",
        "start_time": "08:45",
        "end_time": "17:15",
        "historical": false
        },
        {
        "date": "24/12/2025",
        "weekday": "wed",
        "start_time": "NA",
        "end_time": "NA",
        "historical": false
        }
    ]
    }
    ```

### Legend

- historical: true: Actual historical data
- historical: false: ML prediction
- "NA": Unreliable prediction (rejected)
- weekday: mon, tue, wed, thu, fri, sat, sun

---

## Endpoints:

- GET /api/: Summarize the temporal event prediction API

    ```bash
    curl "http://127.0.0.1:8000/api/"
    ```

- POST /api/session/create/: Create new session and return the session id

    ```bash
    curl -X POST "http://127.0.0.1:8000/api/session/create/"
    ```    

- GET /api/session/info: Get session informations

    ```bash
    curl "http://127.0.0.1:8000/api/session/info/" \
    -H "accept: application/json" \
    -H "X-Session-ID: 188f9fe92fc4fdbd3bcde0e882860bc38af48f6d0f07016f86fdef8d7ff8c672"
    ```

- DELETE /api/session/delete/

    ```bash
    curl "http://127.0.0.1:8000/api/session/delete/" \
    -H "X-Session-ID: 188f9fe92fc4fdbd3bcde0e882860bc38af48f6d0f07016f86fdef8d7ff8c672"
    ```

- POST /api/session/cleanup: Clean up expired sessions (admin)

    ```bash
    curl -X POST "http://127.0.0.1:8000/api/session/cleanup" \
    -H "X-Admin-Token: kJ3mN8pQ2rT5vX9zA1bC4dE6fG8hI0jK1lM3nO5pQ7rS9tU1vW3xY5zA"
    ```

- GET /api/session/cache-info: Get cache info (admin)

    ```bash
    curl -X GET "http://127.0.0.1:8000/api/session/cache-info" \
    -H "X-Admin-Token: kJ3mN8pQ2rT5vX9zA1bC4dE6fG8hI0jK1lM3nO5pQ7rS9tU1vW3xY5zA"

- POST /api/session/clear-cache: Clear cache (admin)

    ```bash
    curl -X POST "http://127.0.0.1:8000/api/session/cache-clear" \
    -H "X-Admin-Token: kJ3mN8pQ2rT5vX9zA1bC4dE6fG8hI0jK1lM3nO5pQ7rS9tU1vW3xY5zA"
    ```

- POST /api/train_models: upload csv, store datas in sqlite database, train model

    ```bash
    curl -X POST "http://127.0.0.1:8000/api/train_models/" \
        -H "X-Session-ID: 188f9fe92fc4fdbd3bcde0e882860bc38af48f6d0f07016f86fdef8d7ff8c672" \
        -F "file=@/path/to/your/file.csv" \
        -F "id_column=YOUR_ID_COLUMN_NAME" \
        -F "date_column=YOUR_DATE_COLUMN_NAME" \
        -F "start_time_column=YOUR_START_TIME_COLUMN_NAME" \
        -F "end_time_column=YOUR_END_TIME_COLUMN_NAME"
    ```

- POST /api/predict: get predictions

    ```bash
    curl -X POST "http://127.0.0.1:8000/api/predict/" \
        -H "X-Session-ID: 188f9fe92fc4fdbd3bcde0e882860bc38af48f6d0f07016f86fdef8d7ff8c672" \
        -H "Content-Type: application/json" \
        -d '{"id": "1", "target_date": "25/12/2025", "window_size": 30}'
    ```

---

## Admin Configuration

**Environnement variable:** ADMIN_TOKEN

### Developement Mode (default)

If ADMIN_TOKEN is not defined, the application generates an ephemeral token every time it starts:
    ```bash
    poetry run work-time-prediction
    ```

#### Console Output

    ```
    2025-11-15 19:08:07 - work_time_prediction.security - WARNING - Development mode enable
    2025-11-15 19:08:07 - work_time_prediction.security - WARNING - Ephemeral admin token generated: dDH8wMr6hG6gUgdiL3SKyS_bsqSufg1Q_AGnh2sSpvY
    2025-11-15 19:08:07 - work_time_prediction.security - WARNING - For production, define: export ADMIN_TOKEN='your-secure-token'
    ```

### Production Mode

1. Generate a secure token and define the variable:

    ```bash
    export ADMIN_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    ```

2. Launch the server:

```bash
poetry run work-time-prediction
```

#### Console Output

    ```
    2025-11-15 20:35:53 - work_time_prediction.security - INFO - Admin token load from environnement variable ADMIN_TOKEN
    ```

---

## Architecture

### Directory Structure

    ```
    $HOME/work_time_prediction/
    ├── data/
    │   └── sessions/
    │       ├── sessions.db                    # Main DB (sessions, quotas, logs)
    │       └── {session_id}/                  # Folder per session
    │           ├── metadata.json              # Model metadata
    │           ├── model_arrival.pkl          # Start time model
    │           ├── model_departure.pkl        # End time model
    │           ├── encoder.pkl                # Encoder + ID mapping
    │           └── data.db                    # Training data
    ├── logs/
        ├── app.log
        ├── security.log
        └── quotas.log
    ```

---

### Database

1. Main Database (sessions.db)
Contains metadata for all sessions.

- Tables:
    - sessions: User sessions
    - ip_quotas: Quotas and rate limiting by IP
    - security_logs: Security event logs
- Views:
    - activate_sessions: Non-expired sessions
    - expired_sessions: Session to be cleaned up
    - ip_statistics: statistics by IP
    - suspicious_ips: IPs with violations
    - system_statistics: Global statistics

2. Per-session databases ({session_id}/data.db)
Each session has its own isolated database.

- Tables:
    - schedule_data: Work schedule data

---

### Technologies

- Web framework: FastAPI
- ORM: SQLAlchemy
- ML: scikit-learn (RandomForestRegressor)
- Database: SQLite
- Cache: LRU Cache (cachetools)

---

### Data Flow

1. Session Creation
    1. Client -> POST /api/session/create
    2. SessionManager.create_session()
        - Generates secure session_id (SHA256)
        - Create record in sessions.db
        - Create directory sessions/{session_id}/
        - initializes empty data.db
    3. Returns session_id to the client

2. Training
    1. Client -> POST /api/train_models/ (CSV + column mapping)
    2. load_data_from_csv(csv, mapping)
        - Transformation: Custom columns -> standardized columns
        - Cleaning and validation
    3. save_data_to_db(df, session_id)
    4. train_models(session_id)
        - Loads data from data.db
        - Encodes IDs
        - Trains RandomForestRegressor (start time)
        - Trains RandomForestRegressor (end time)
        - Returns ModelState
    5. session_manager.save_model(session_id, model_state)
        - Saves model_arrival.pkl
        - Saves model_departure.pkl
        - Saves encoder.pkl
        - Saves metadata.json
        - Caches (LRU)
    6. Returns training statistics

3. Prediction
    1. Client -> POST /api/predict/ (id, date, window_size)
    2. session_manager.load_model(session_id)
        - Hit -> Returns ModelState from cache
        - Miss -> Loads from disk + caches
    3. generate_predictions(model_state, session_id, id, dates)
        - Retrieves historical data from data.db
        - Identifies dates to predict (non-historical)
        - Generates ML predictions  
        - Combines historical + predictions

---

## Security

- Tokens: SHA256, 64-character (32 bytes)
- Expiration: Sessions are automatically cleaned up when expired
- Logs: All events are traced (IP, action, timestamp)
- Rate Limiting: Configurable quotas per IP
- Banning: Suspicious IPs are automatically banned

---

## Cache and Performance

### LRU Model Cache
- _model_cache: LRUCache[session_id -> ModelState]
- Capacity: 50 models (configurable with MAX_MODELS_IN_CACHE)
- Eviction: Least Recently Used
- Benefit: Avoids reloading models from disk

### Optimization
- SQL Indexes: On all frequently queried columns
- Materialized Views: Used for statistics
- Bulk Insert: pandas.to_sql() for fast data insertion
- Lazy Loading: Models are loaded only when necessary

---

## API Documentation

Interactive Documentation is available at:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## TODO

- add summarize dataset api
- make tests
- clean code (always)

## License

MIT