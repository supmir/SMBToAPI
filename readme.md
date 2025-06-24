# SMB To API

A simple Flask-based REST API for interacting with SMB (Windows file share) servers. This API allows you to list, create, retrieve, rename, copy, move, and delete files or directories on a remote SMB share.

## Quick Start

### 1. Clone the repository

```sh
git clone <your-repo-url>
cd relay
```

### 2. Configure Environment Variables

Copy the example environment file and edit it with your SMB and proxy settings:

```sh
cp .env.example .env
# Edit .env with your SMB credentials and settings
```

### 3. Build and Run with Docker

```sh
docker build -t smb-relay .
docker run --env-file .env -p 5000:5000 smb-relay
```

### 4. Or Run Locally (Python)

Install dependencies and start the app:

```sh
pip install -r requirements.txt
python app.py
```

The API will be available at [http://localhost:5000](http://localhost:5000).

---
