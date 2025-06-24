# flake8: noqa: E501
# pylint: disable=broad-except
# pylint: disable=line-too-long

from io import BytesIO
import os
import logging
import sys

from flask import Flask, request, jsonify
from smb.SMBConnection import SMBConnection
from smb import smb_structs
from smb.base import OperationFailure

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

REQUIRED_ENV_VARS = [
    "SMB_HOST",
    "SMB_PORT",
    "SMB_USERNAME",
    "SMB_PASSWORD",
    "SMB_NAME",
    "SMB_REMOTE",
    "SMB_DOMAIN",
]

missing_env_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_env_vars:
    logging.log(
        logging.ERROR,
        "Missing required environment variables: %s",
        ", ".join(missing_env_vars),
    )
    sys.exit(1)

SMB_CONFIG = {
    "host": os.getenv("SMB_HOST"),
    "port": os.getenv("SMB_PORT"),
    "username": os.getenv("SMB_USERNAME"),
    "password": os.getenv("SMB_PASSWORD"),
    "my_name": os.getenv("SMB_NAME"),
    "remote_name": os.getenv("SMB_REMOTE"),
    "domain": os.getenv("SMB_DOMAIN"),
    "use_ntlm_v2": True,
    "is_direct_tcp": True,
    "share_path_prefix": "/",
}

SMB_CONNECTION: SMBConnection | None = None


def get_smb_connection() -> SMBConnection:
    """Establishes and returns a persistent SMB connection.
    If the existing connection is not valid, it attempts to re-establish it.
    """
    global SMB_CONNECTION

    if SMB_CONNECTION is not None:
        try:
            echo_data = b"ping_test_echo"
            response_data = SMB_CONNECTION.echo(echo_data, timeout=5)
            if response_data != echo_data:
                logging.log(
                    logging.WARNING,
                    "SMB echo response did not match sent data. Assuming connection issue. Attempting to reconnect.",
                )
                SMB_CONNECTION.close()
                SMB_CONNECTION = None
            else:
                logging.log(
                    logging.INFO, "Reusing existing SMB connection (echo successful)."
                )
                return SMB_CONNECTION
        except OperationFailure as op_e:
            logging.log(
                logging.WARNING,
                "Existing SMB connection failed during ping (%s). Attempting to reconnect.",
                op_e,
            )
            SMB_CONNECTION.close()
            SMB_CONNECTION = None
        except Exception as e:
            logging.log(
                logging.WARNING,
                "Unexpected error with existing SMB connection during ping (%s). Attempting to reconnect.",
                e,
            )
            if SMB_CONNECTION:
                SMB_CONNECTION.close()
            SMB_CONNECTION = None

    try:
        logging.log(
            logging.INFO,
            "Attempting to connect to SMB server: %s (%s:%d)",
            SMB_CONFIG["remote_name"],
            SMB_CONFIG["host"],
            SMB_CONFIG["port"],
        )
        smb_structs.SUPPORT_SMB2 = True

        conn = SMBConnection(
            username=SMB_CONFIG["username"],
            password=SMB_CONFIG["password"],
            my_name=SMB_CONFIG["my_name"],
            remote_name=SMB_CONFIG["remote_name"],
            domain=SMB_CONFIG["domain"],
            use_ntlm_v2=SMB_CONFIG["use_ntlm_v2"],
            is_direct_tcp=SMB_CONFIG["is_direct_tcp"],
        )

        conn.connect(SMB_CONFIG["host"], SMB_CONFIG["port"])
        SMB_CONNECTION = conn
        logging.log(logging.INFO, "Successfully established new SMB connection.")
        return SMB_CONNECTION
    except Exception as e:
        logging.log(logging.ERROR, "SMB connection failed: %s", e, exc_info=True)
        raise


def _full_smb_path(relative_path):
    """Constructs the full SMB path including the share path prefix."""
    if relative_path:
        relative_path = relative_path.lstrip("/")
    else:
        relative_path = ""

    if SMB_CONFIG["share_path_prefix"]:
        full_path = f"{SMB_CONFIG['share_path_prefix'].rstrip('/')}/{relative_path}"
    else:
        full_path = relative_path

    logging.log(logging.INFO, "Constructed full SMB path: %s", full_path)
    return full_path


@app.route("/hello")
def hello():
    """Simple health check endpoint."""
    return jsonify(message="Hello, World")


@app.route("/list", methods=["GET"])
def list_files():
    """Lists files and directories in a given path on a specified SMB share."""
    path = request.args.get("path", "/")
    share_name = request.args.get("share_name")

    if not share_name:
        return jsonify({"error": "share_name parameter is required"}), 400

    full_path = _full_smb_path(path)
    logging.log(
        logging.INFO,
        "Listing files in SMB share '%s', path: '%s'",
        share_name,
        full_path,
    )

    try:
        conn = get_smb_connection()

        files = []
        file_list = conn.listPath(share_name, full_path)

        for item in file_list:
            if item.filename in [".", ".."]:
                continue

            item_path = os.path.join(path, item.filename).replace("\\", "/")
            files.append(
                {
                    "name": item.filename,
                    "path": item_path,
                    "size": item.file_size,
                    "is_dir": item.isDirectory,
                    "create_time": item.create_time,
                    "last_write_time": item.last_write_time,
                    "attributes": item.file_attributes,
                }
            )

        return jsonify(files)
    except Exception as e:
        logging.log(logging.ERROR, "Error listing files: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/create", methods=["POST"])
def create_file_or_directory():
    """Creates a new file or directory on the specified SMB share."""
    path = request.args.get("path")
    share_name = request.args.get("share_name")
    is_dir = request.args.get("isDir", "false").lower() == "true"

    if not path:
        return jsonify({"error": "path parameter is required"}), 400
    if not share_name:
        return jsonify({"error": "share_name parameter is required"}), 400

    full_path = _full_smb_path(path)

    try:
        conn = get_smb_connection()

        if is_dir:
            logging.log(
                logging.INFO,
                "Creating directory on share '%s': %s",
                share_name,
                full_path,
            )
            conn.createDirectory(share_name, full_path)
        else:
            logging.log(
                logging.INFO, "Creating file on share '%s': %s", share_name, full_path
            )
            file_content = request.data
            file_obj = BytesIO(file_content)
            conn.storeFile(share_name, full_path, file_obj)
            file_obj.close()

        return jsonify({"status": "success"})
    except Exception as e:
        logging.log(
            logging.ERROR, "Error creating file/directory: %s", e, exc_info=True
        )
        return jsonify({"error": str(e)}), 500


@app.route("/get", methods=["GET"])
def get_file():
    """Retrieves the content of a file from the specified SMB share."""
    path = request.args.get("path")
    share_name = request.args.get("share_name")

    if not path:
        return jsonify({"error": "Path parameter is required"}), 400
    if not share_name:
        return jsonify({"error": "share_name parameter is required"}), 400

    full_path = _full_smb_path(path)

    try:
        conn = get_smb_connection()
        file_obj = BytesIO()
        logging.log(
            logging.INFO, "Retrieving file from share '%s': %s", share_name, full_path
        )
        conn.retrieveFile(share_name, full_path, file_obj)
        file_content = file_obj.getvalue()
        file_obj.close()

        if path.lower().endswith((".json", ".txt", ".csv", ".log")):
            return file_content.decode("utf-8"), 200, {"Content-Type": "text/plain"}
        else:
            return (
                file_content,
                200,
                {
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": f'attachment; filename="{os.path.basename(path)}"',
                },
            )
    except Exception as e:
        logging.log(logging.ERROR, "Error getting file: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/rename", methods=["POST"])
def rename_file():
    """Renames a file or directory on the specified SMB share."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    old_path = data.get("path")
    new_path = data.get("newPath")
    share_name = data.get("share_name")

    if not old_path or not new_path:
        return jsonify({"error": "path and newPath are required in JSON body"}), 400
    if not share_name:
        return jsonify({"error": "share_name is required in JSON body"}), 400

    old_full_path = _full_smb_path(old_path)
    new_full_path = _full_smb_path(new_path)

    try:
        conn = get_smb_connection()
        logging.log(
            logging.INFO,
            "Renaming on share '%s': from %s to %s",
            share_name,
            old_full_path,
            new_full_path,
        )
        conn.rename(share_name, old_full_path, new_full_path)
        return jsonify({"status": "success"})
    except Exception as e:
        logging.log(
            logging.ERROR, "Error renaming file/directory: %s", e, exc_info=True
        )
        return jsonify({"error": str(e)}), 500


@app.route("/copy", methods=["POST"])
def copy_file():
    """Copies a file on the specified SMB share. SMB does not have a direct copy operation, so this involves reading and writing."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    source_path = data.get("path")
    destination_path = data.get("newPath")
    share_name = data.get("share_name")

    if not source_path or not destination_path:
        return jsonify({"error": "path and newPath are required in JSON body"}), 400
    if not share_name:
        return jsonify({"error": "share_name is required in JSON body"}), 400

    source_full_path = _full_smb_path(source_path)
    destination_full_path = _full_smb_path(destination_path)

    try:
        conn = get_smb_connection()
        logging.log(
            logging.INFO,
            "Copying file on share '%s': from %s to %s",
            share_name,
            source_full_path,
            destination_full_path,
        )

        file_obj = BytesIO()
        conn.retrieveFile(share_name, source_full_path, file_obj)
        file_content = file_obj.getvalue()
        file_obj.close()

        dest_file_obj = BytesIO(file_content)
        conn.storeFile(share_name, destination_full_path, dest_file_obj)
        dest_file_obj.close()

        return jsonify({"status": "success"})
    except Exception as e:
        logging.log(logging.ERROR, "Error copying file: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/move", methods=["POST"])
def move_file():
    """Moves a file or directory on the SMB share by copying and then deleting the source."""

    source_path = request.args.get("path")
    destination_path = request.args.get("newPath")
    share_name = request.args.get("share_name")

    if not source_path or not destination_path:
        return (
            jsonify({"error": "Query parameters 'path' and 'newPath' are required"}),
            400,
        )
    if not share_name:
        return jsonify({"error": "Query parameter 'share_name' is required"}), 400

    source_full_path = _full_smb_path(source_path)
    destination_full_path = _full_smb_path(destination_path)

    try:
        conn = get_smb_connection()
        logging.info(
            "Moving file on share '%s': %s → %s",
            share_name,
            source_full_path,
            destination_full_path,
        )

        file_obj = BytesIO()
        conn.retrieveFile(share_name, source_full_path, file_obj)
        file_content = file_obj.getvalue()
        file_obj.close()

        dest_file_obj = BytesIO(file_content)
        conn.storeFile(share_name, destination_full_path, dest_file_obj)
        dest_file_obj.close()

        try:
            logging.info(
                "Deleting original file on share '%s': %s", share_name, source_full_path
            )
            conn.deleteFiles(share_name, source_full_path)
        except Exception as file_delete_error:
            logging.warning(
                "Failed to delete %s as file on share '%s': %s. Trying as directory...",
                source_full_path,
                share_name,
                file_delete_error,
            )
            try:
                conn.deleteDirectory(share_name, source_full_path)
            except Exception as dir_delete_error:
                logging.error(
                    "Failed to delete %s after moving: %s",
                    source_full_path,
                    dir_delete_error,
                    exc_info=True,
                )
                raise IOError(
                    f"File moved to {destination_full_path} but could not delete original {source_full_path}. (File error: {file_delete_error}, Dir error: {dir_delete_error})"
                ) from dir_delete_error

        return jsonify({"status": "success"})

    except Exception as e:
        logging.error("Error moving file: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/delete", methods=["POST"])
def delete_file():
    """Deletes a file or directory on the SMB share."""

    path_to_delete = request.args.get("path")
    share_name = request.args.get("share_name")

    if not path_to_delete:
        return (
            jsonify({"error": "Query parameters 'path' is required"}),
            400,
        )
    if not share_name:
        return jsonify({"error": "Query parameter 'share_name' is required"}), 400

    full_path = _full_smb_path(path_to_delete)

    try:
        conn = get_smb_connection()
        try:
            logging.info(
                "Attempting to delete file on share '%s': %s",
                share_name,
                full_path,
            )
            conn.deleteFiles(share_name, full_path)
        except Exception as file_delete_error:
            logging.warning(
                "Failed to delete %s as file on share '%s': %s. Trying as directory...",
                full_path,
                share_name,
                file_delete_error,
            )
            try:
                logging.info(
                    "Attempting to delete directory on share '%s': %s",
                    share_name,
                    full_path,
                )
                conn.deleteDirectory(share_name, full_path)
            except Exception as dir_delete_error:
                logging.error(
                    "Failed to delete %s as directory on share '%s': %s",
                    full_path,
                    share_name,
                    dir_delete_error,
                    exc_info=True,
                )
                raise FileNotFoundError(
                    f"Could not delete {full_path} on share '{share_name}'. It might be a non-empty directory or a permission issue. (File error: {file_delete_error}, Dir error: {dir_delete_error})"
                ) from dir_delete_error

        return jsonify({"status": "success"})
    except Exception as e:
        logging.error("Error deleting file/directory: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.teardown_appcontext
def close_connections():
    """Closes the SMB connection when the application context tears down."""
    global SMB_CONNECTION
    if SMB_CONNECTION is not None:
        logging.log(logging.INFO, "Closing SMB connection.")
        SMB_CONNECTION.close()
        SMB_CONNECTION = None


if __name__ == "__main__":
    if not SMB_CONFIG["password"]:
        logging.critical("SMB_PASSWORD environment variable is not set. Exiting.")
        exit(1)

    try:
        get_smb_connection()
    except Exception as e:
        logging.critical(
            "Failed to establish initial SMB connection: %s. The app will start, but SMB operations may fail until connection is established.",
            e,
        )

    app.run(host="0.0.0.0", port=5000, debug=True)
