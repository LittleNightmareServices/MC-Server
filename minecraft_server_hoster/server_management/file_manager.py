import os
import shutil
from werkzeug.utils import secure_filename

def handle_upload(file_storage, destination_folder, sub_directory=""):
    """
    Handles file uploads, saving the file to a specified destination.

    Args:
        file_storage: The FileStorage object from request.files.
        destination_folder: The base folder for uploads.
        sub_directory: Optional subdirectory path to append to destination_folder.

    Returns:
        A dictionary with status and message.
    """
    if file_storage and file_storage.filename:
        filename = secure_filename(file_storage.filename)
        
        # Ensure sub_directory is relative and secure
        # For example, split by '/' or '\' and rejoin, disallowing '..'
        safe_sub_directory_parts = []
        if sub_directory:
            parts = sub_directory.split(os.sep)
            for part in parts:
                if part == "..": # Disallow path traversal
                    continue
                safe_sub_directory_parts.append(part)
        safe_sub_directory = os.path.join(*safe_sub_directory_parts) if safe_sub_directory_parts else ""

        target_path_directory = os.path.join(destination_folder, safe_sub_directory)
        target_path_file = os.path.join(target_path_directory, filename)

        try:
            os.makedirs(target_path_directory, exist_ok=True)
            file_storage.save(target_path_file)
            return {"status": "success", 
                    "message": "File uploaded successfully.", 
                    "filename": filename, 
                    "path": os.path.relpath(target_path_file, destination_folder)} # Return relative path
        except Exception as e:
            return {"status": "error", "message": f"Could not save file: {str(e)}"}
    else:
        return {"status": "error", "message": "No file provided or filename is empty."}

def list_files_in_directory(base_path, sub_path=""):
    """
    Lists files and directories within a given path, with security checks.

    Args:
        base_path: The root directory to list from.
        sub_path: The relative path within base_path to list.

    Returns:
        A dictionary with status, files, directories, and current_path.
    """
    abs_base_path = os.path.abspath(base_path)
    current_path_to_return = sub_path 

    if os.path.isabs(sub_path) or ".." in sub_path.split(os.sep):
        if sub_path: 
            return {"status": "error", "message": "Access denied. Invalid path."}
        # If sub_path is empty and valid (e.g. just ""), it means list base_path
        target_dir = abs_base_path
        current_path_to_return = "" # Root of base_path
    else:
        # sub_path is relative and doesn't contain ".." by itself.
        target_dir = os.path.abspath(os.path.join(abs_base_path, sub_path))
        # current_path_to_return remains sub_path

    # Final security check: ensure the resolved target_dir is within abs_base_path
    if not target_dir.startswith(abs_base_path):
        return {"status": "error", "message": "Access denied. Attempted path traversal."}

    if os.path.exists(target_dir) and os.path.isdir(target_dir):
        try:
            items = os.listdir(target_dir)
            files = [item for item in items if os.path.isfile(os.path.join(target_dir, item))]
            directories = [item for item in items if os.path.isdir(os.path.join(target_dir, item))]
            return {"status": "success", "files": files, "directories": directories, "current_path": current_path_to_return}
        except OSError as e:
            return {"status": "error", "message": f"Error listing directory: {str(e)}"}
    else:
        return {"status": "error", "message": "Directory not found."}

def prepare_download_path(base_download_folder, requested_filename):
    """
    Prepares and validates the full path for a file download.

    Args:
        base_download_folder: The root directory from which files can be downloaded.
        requested_filename: The filename (potentially with subdirectories) requested.

    Returns:
        The full, validated path to the file, or None if invalid/not found.
    """
    abs_base_download_folder = os.path.abspath(base_download_folder)

    # Ensure requested_filename is not absolute and does not contain '..' (path traversal)
    # Also, disallow empty filenames.
    if not requested_filename or os.path.isabs(requested_filename) or ".." in requested_filename.split(os.sep):
        return None

    # Construct the naive path
    full_path = os.path.join(abs_base_download_folder, requested_filename)
    # Normalize it to resolve any relative path components like '.' and to get the true absolute path
    full_path = os.path.abspath(full_path)

    # Security Check: Ensure the normalized full_path is still within the base_download_folder
    if not full_path.startswith(abs_base_download_folder):
        return None 

    if os.path.exists(full_path) and os.path.isfile(full_path):
        return full_path
    else:
        return None
