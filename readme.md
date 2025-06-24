# SMB To API

**SMB To API** is a lightweight Flask-based REST API that provides file management operations over SMB (Windows file shares). It enables you to list, create, retrieve, rename, copy, move, and delete files or directories on a remote SMB server—making legacy file systems more accessible via HTTP.

GitHub: [https://github.com/supmir/SMBToAPI](https://github.com/supmir/SMBToAPI)

---

## 🚀 Quick Start

### 1. Set Up Environment Configuration

Begin by creating your `.env` file from the example provided:

```sh
cp .env.example .env
```

Open `.env` and configure your SMB connection details, such as:

```
SMB_HOST=your-smb-host
SMB_PORT=445
SMB_USERNAME=your-username
SMB_PASSWORD=your-password
SMB_SHARE=your-share-name
SMB_DOMAIN=optional-domain
```

These variables are used by the API both in local development and inside Docker containers.

---

### 2. Run Using Docker (Recommended)

If you have Docker installed, the easiest way to get up and running is by pulling the prebuilt image from Docker Hub.

**Pull the image:**

```sh
docker pull supmir/smb-to-api
```

**Run the container:**

```sh
docker run --env-file .env -p 5000:5000 supmir/smb-to-api
```

Once started, the API will be available at:
👉 **[http://localhost:5000](http://localhost:5000)**

---

## ✅ Supported Operations

### `GET /hello`

Simple health check endpoint. Returns a friendly JSON message.

---

### `GET /list`

List files and directories in a specific path on the SMB share.

**Query Parameters**:

- `share_name` (required): Name of the SMB share
- `path` (optional): Directory path to list (default is `/`)

---

### `POST /create`

Create a new file or directory on the SMB share.

**Query Parameters**:

- `share_name` (required): Name of the SMB share
- `path` (required): Path (including filename or folder name)
- `isDir` (optional): Set to `true` to create a directory (default is file)

**Request Body**:

- Raw binary data (only required when creating a file)

---

### `GET /get`

Download or preview a file from the SMB share.

**Query Parameters**:

- `share_name` (required): Name of the SMB share
- `path` (required): Path to the file

**Response**:

- Returns text/plain for `.json`, `.txt`, `.csv`, `.log`
- Returns `application/octet-stream` for all others, with `Content-Disposition` for download

---

<!-- ### `POST /rename`

Rename or move a file/directory within the same SMB share.

**JSON Body**:

```json
{
  "share_name": "your-share",
  "path": "/old/path",
  "newPath": "/new/path"
}
```

---

### `POST /copy`

Copy a file by downloading and re-uploading it under a new name.

**JSON Body**:

```json
{
  "share_name": "your-share",
  "path": "/source/file.txt",
  "newPath": "/dest/file_copy.txt"
}
```

> _Note: Only works for files (not folders). No native SMB copy, this reads and stores the file._
---

-->

### `POST /move`

Move a file or directory by copying and then deleting the original.

**Query Parameters**:

- `share_name` (required)
- `path` (required): Source path
- `newPath` (required): Destination path

> _Handles both files and directories._

---

### `POST /delete`

Delete a file or directory from the SMB share.

**Query Parameters**:

- `share_name` (required)
- `path` (required): Path to the file or directory to delete

> _Will attempt to delete as a file first. If that fails, it will attempt to delete as a directory._

---

## 🧱 Use Cases

- Expose legacy Windows shares over modern REST interfaces
- Integrate SMB storage into frontend dashboards
- Enable controlled remote access to internal file systems
