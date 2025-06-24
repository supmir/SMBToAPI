# SMB To API

A simple Flask-based REST API for interacting with SMB (Windows file share) servers. This API allows you to list, create, retrieve, rename, copy, move, and delete files or directories on a remote SMB share.

GitHub Repository: https://github.com/supmir/SMBToAPI

## Quick Start

### 1. Configure Environment Variables

First, you'll need to set up your environment variables. Copy the example environment file and edit it with your SMB and proxy settings. This file will be used whether you build locally or pull from Docker Hub.

```sh
cp .env.example .env
```

Open the .env file and edit it with your SMB credentials and settings (e.g., SMB_HOST, SMB_USERNAME, SMB_PASSWORD).

### 2. Run with Docker from Docker Hub

This is the quickest way to get started if you have Docker installed. You can pull the pre-built image directly from Docker Hub.

Pull the SMBToAPI image from Docker Hub (assuming 'supmir/smb-to-api' is the image name)

```sh
docker pull supmir/smb-to-api
```

Run the container, mounting your .env file for configuration and mapping port 5000

```sh
docker run --env-file .env -p 5000:5000 supmir/smb-to-api
```

The API will be available at http://localhost:5000 once it's running.
