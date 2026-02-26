# Game Orchestrator

This service provides session management for games hosted as digital ocean droplets. This service provides an API for clients to create, join and end game sessions. 

## Features

* **Session Management**: Start, login, and end game sessions
* **Droplet Orchestration**: Create and manage DigitalOcean droplets on demand
* **Database Persistence**: SQLite database tracks active game sessions and droplet information
* **Health Monitoring**: Server heartbeat endpoint to track connected clients
* **Unique Session Tags**: Auto-generated 6-character share tags for session identification

## What's Included

- **`backend/`**: Core application modules
  - `database_manager.py`: SQLite ORM for game droplet data
  - `droplet_manager.py`: DigitalOcean API integration for droplet lifecycle
  - `constants.py`: API response keys and error messages
- **`api.py`**: FastAPI application with REST endpoints
- **`tests/`**:
  - `test_api.py`: API endpoint tests (8 tests)
  - `test_database_manager.py`: Database operations tests (7 tests)
  - `test_droplet_manager.py`: Droplet management tests (5 tests)
  - `test_orchestrator.py`: Integration flow tests (1 test)
- **`db/database_setup.py`**: Database schema initialization
- **`dockerfile`**: Docker image definition for the API
- **`entrypoint.sh`**: Container startup script that creates the database before running the API
- `requirements.py`: Libraries necessary to run the orchestrator
- `orchestrator_api.http`: test API with running instance 
- `run_app.ps1` : PS to run the orchestrator
- `run_tests.ps1`: PS script to run the tests

## Run Locally

### ...with Powershell

#### 1. Add variables to the a `.env` file in the project root:

```
DB_PATH=path/to/femquest.db
DIGITALOCEAN_TOKEN=your_digitalocean_api_token
DROPLET_TAG=your_droplet_tag
SNAPSHOT_ID=your_snapshot_id
DROPLET_REGION=your_region
DROPLET_SIZE=your_size
INTERNAL_HMAC_SECRET=your_internal_hmac_secret
SSL_CERTFILE=certs/server.crt
SSL_KEYFILE=certs/server.key
CORS_ALLOWED_ORIGINS=https://test.femquest.gamelabgraz,https://test.femquest.gamelabgraz.at,https://femquest.gamelabgraz.at
```

#### Internal server endpoint auth (HMAC)

Internal endpoints (`/server/end`, `/server/heartbeat`) require these headers:

- `Request-Timestamp` (or `Request_Timestamp`): current Unix timestamp (seconds)
- `Request-Signature` (or `Request_Signature`): hex HMAC-SHA256 over:

`METHOD + "\n" + PATH + "\n" + QUERY + "\n" + TIMESTAMP + "\n" + SHA256_HEX(BODY_BYTES)`

Using shared secret `INTERNAL_HMAC_SECRET`. Default allowed clock skew is 300 seconds.

Generate headers with helper script:

```powershell
./scripts/test_server_end.ps1 -Insecure -DropletIp 10.0.0.1
./scripts/test_server_heartbeat.ps1 -Insecure -DropletIp 10.0.0.1 -ConnectedClients 1
```

These scripts generate and apply `Request_Timestamp` and `Request_Signature` automatically.

#### 2. Create local TLS certs (development):

```powershell
mkdir certs -ErrorAction SilentlyContinue
openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 365 \
  -keyout certs/server.key -out certs/server.crt -subj "/CN=localhost"
```

If your machine does not have `openssl`, install it or generate equivalent cert/key files and place them at the paths configured by `SSL_CERTFILE` and `SSL_KEYFILE`.

#### 3. Run the app:

```powershell
.\run_app.ps1
```

This script creates a virtual environment, installs dependencies, creates the database if missing, and starts the API with TLS at `https://localhost:8000`.
Startup fails if `SSL_CERTFILE` or `SSL_KEYFILE` is missing.

### ... with Docker

#### 1. Add variables to the `.env` file in the project root (same as above).

#### 2. Build and run the image (the repo uses a lowercase `dockerfile`):

```powershell
docker build -f dockerfile -t game-orchestrator .
docker run -p 8000:8000 --env-file .env game-orchestrator
```

The container entrypoint will create the database if `DB_PATH` is set and the file does not exist.
TLS is required and startup fails if `SSL_CERTFILE` or `SSL_KEYFILE` is missing.

## Host On DigitalOcean

The simplest production setup is a Docker droplet with a bind-mounted database file.

### 1. Create a Docker droplet

- Create a Droplet using the Docker marketplace image.
- SSH into the droplet.

### 2. Deploy the service

```bash
git clone <your-repo-url>
cd GameOrchestrator

# Create a directory for persistent data
mkdir -p /opt/game-orchestrator/data

# Create .env with a container path for DB
cat <<EOF > .env
DB_PATH=/data/femquest.db
DIGITALOCEAN_TOKEN=your_digitalocean_api_token
DROPLET_TAG=your_droplet_tag
SNAPSHOT_ID=your_snapshot_id
DROPLET_REGION=your_region
DROPLET_SIZE=your_size
INTERNAL_HMAC_SECRET=your_internal_hmac_secret
SSL_CERTFILE=/app/certs/server.crt
SSL_KEYFILE=/app/certs/server.key
CORS_ALLOWED_ORIGINS=http://test.femquest.gamelabgraz,http://femquest.gamelabgraz.at
EOF

# Build and run
docker build -f dockerfile -t game-orchestrator .
docker run -d --name game-orchestrator -p 8000:8000 \
  --env-file .env \
  -v /opt/game-orchestrator/certs:/app/certs \
  -v /opt/game-orchestrator/data:/data \
  game-orchestrator
```

### 3. Open the port

Ensure port `8000` is open in your droplet firewall or security settings.

