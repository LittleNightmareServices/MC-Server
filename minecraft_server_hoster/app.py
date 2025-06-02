from flask import Flask, render_template, jsonify, request, send_from_directory
import os
from werkzeug.utils import secure_filename
# Updated import to reflect __init__.py
# Now handler includes create_backup, and file_manager is separate
from server_management import handler, file_manager 

app = Flask(__name__)

# Configure Upload Folder
UPLOAD_FOLDER_NAME = 'uploads' # Relative to app.py's directory for simplicity here
app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER_NAME))
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start_server', methods=['POST'])
def start_server_route():
    # Example: get params if your UI sends them
    # data = request.get_json()
    # jar_file = data.get('jar_file', 'server.jar')
    # server_dir_name = data.get('server_dir_name', handler.DEFAULT_SERVER_DIR_NAME)
    # memory_mb = data.get('memory_mb', 1024)
    # result = handler.start_server(jar_file, server_dir_name, memory_mb)
    # For now, using defaults from handler.py, but specifying the dummy script name
    result = handler.start_server(jar_file="dummy_server.sh")
    return jsonify(result)

@app.route('/stop_server', methods=['POST'])
def stop_server_route():
    result = handler.stop_server()
    return jsonify(result)

@app.route('/restart_server', methods=['POST'])
def restart_server_route():
    stop_result = handler.stop_server()
    if stop_result.get("status") == "error" and "not running" not in stop_result.get("message", ""):
        # If stopping failed for a reason other than "not running", report error
        return jsonify(status="error", message=f"Failed to stop server for restart: {stop_result.get('message')}")

    # Proceed to start, potentially after a short delay
    # import time
    # time.sleep(2) # Give it a moment if needed

    # Assuming default start parameters for now
    start_result = handler.start_server() 
    if start_result.get("status") == "success":
        return jsonify(status="success", message="Server restarting...")
    else:
        return jsonify(status="error", message=f"Server stopped, but failed to start: {start_result.get('message')}")


@app.route('/send_command', methods=['POST'])
def send_command_route():
    data = request.get_json()
    command = data.get('command')
    if not command:
        return jsonify(status="error", message="Command not provided."), 400
    result = handler.send_minecraft_command(command)
    return jsonify(result)

@app.route('/get_console_log', methods=['GET'])
def get_console_log_route():
    # server_dir_name = request.args.get('server_dir_name', handler.DEFAULT_SERVER_DIR_NAME)
    # lines = request.args.get('lines', 50, type=int)
    # log_content = handler.read_console_log(server_dir_name, lines)
    log_content = handler.read_console_log() # Using defaults for now
    return jsonify(status="success", log=log_content)

@app.route('/get_server_status', methods=['GET'])
def get_server_status_route():
    status = handler.get_server_status()
    return jsonify(status="success", server_status=status)


# --- File Management Routes ---

@app.route('/upload_file', methods=['POST'])
def upload_file_route():
    if 'file' not in request.files:
        return jsonify(status="error", message="No file part"), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(status="error", message="No selected file"), 400
    
    subdir = request.form.get('subdir', '') # e.g. server_name/plugins
    # For now, basic upload to UPLOAD_FOLDER. Subdir logic would be in handler.
    
    # filename = secure_filename(file.filename)
    # destination_path = os.path.join(app.config['UPLOAD_FOLDER'], subdir, filename)
    # os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    
    # Placeholder call - actual saving logic will be in handler.handle_upload
    # For this step, we assume handler.handle_upload will take the file object
    # and the *intended final filename/subdir within a managed area*.
    # Let's simplify the call for now, assuming handler takes care of secure_filename and path construction.
    
    # This is a conceptual call, actual implementation of handler.handle_upload will determine exact params.
    # For now, let's assume it takes the file stream and the desired filename, and an optional subdir within its managed space.
    s_filename = secure_filename(file.filename) # Still good to secure it here before passing
    
    # Call the new handler function
    result = file_manager.handle_upload(
        file_storage=file, 
        destination_folder=app.config['UPLOAD_FOLDER'], 
        sub_directory=subdir
    )
    
    if result.get("status") == "success":
        return jsonify(status="success", message=result.get("message"), filename=result.get("filename"), path=result.get("path"))
    else:
        return jsonify(status="error", message=result.get("message", "Upload failed")), 500


@app.route('/download_file/<path:filename>', methods=['GET'])
def download_file_route(filename):
    # For now, assumes files are directly in UPLOAD_FOLDER or UPLOAD_FOLDER/subdir
    # Future: handler might provide a secure way to get files from various managed locations.
    
    # Path traversal is handled by prepare_download_path
    target_file_abs_path = file_manager.prepare_download_path(app.config['UPLOAD_FOLDER'], filename)
    
    if target_file_abs_path:
        # send_from_directory needs directory and the filename part
        directory_part = os.path.dirname(target_file_abs_path)
        filename_part = os.path.basename(target_file_abs_path)
        return send_from_directory(directory_part, filename_part, as_attachment=True)
    else:
        return jsonify(status="error", message="File not found or access denied."), 404


@app.route('/list_files', methods=['GET'])
def list_files_route():
    path_param = request.args.get('path', '') # Relative path within UPLOAD_FOLDER
    
    # Path traversal is handled by list_files_in_directory
    result = file_manager.list_files_in_directory(app.config['UPLOAD_FOLDER'], path_param)
    
    if result.get("status") == "success":
        return jsonify(
            status="success", 
            files=result.get("files"), 
            directories=result.get("directories"), 
            current_path=result.get("current_path")
        )
    else:
        return jsonify(status="error", message=result.get("message")), 404 # Or other appropriate code

@app.route('/backup_server', methods=['POST'])
def backup_server_route():
    # server_dir_name could be a parameter from request.json if supporting multiple instances
    # For now, assume default:
    # Assuming create_backup is now part of the handler module as per previous steps
    result = handler.create_backup(server_dir_name="default_server") 
    if result.get("status") == "success":
        return jsonify(result)
    else:
        # Consider more specific error codes if known (e.g., 404 if instance not found)
        return jsonify(result), 500 # Internal Server Error for backup failure


if __name__ == '__main__':
    # This is important for relative imports if you run app.py directly
    # For production, you'd use a WSGI server like Gunicorn
    # from minecraft_server_hoster.server_management import handler
    
    # Create a dummy server script for local testing if it doesn't exist
    # This is just for convenience when running app.py directly
    dummy_script_name = "dummy_server.sh"
    dummy_script_path = os.path.join(handler.DEFAULT_SERVER_PATH, dummy_script_name)
    if not os.path.exists(dummy_script_path):
        print(f"Creating dummy server script at {dummy_script_path} for testing app.py...")
        # Ensure the directory exists first
        os.makedirs(handler.DEFAULT_SERVER_PATH, exist_ok=True)
        with open(dummy_script_path, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("set -x\n") # Enable command tracing
            f.write("cd \"$(dirname \"$0\")\"\n") # Change directory to the script's own location
            f.write("echo 'Dummy Server Script Starting...'\n") # Output to its stdout
            f.write("trap 'echo \"[DUMMY app.py] SIGTERM received, stopping.\"; exit 0' SIGTERM\n")
            f.write("echo 'Entering command loop...'\n") # Output to its stdout
            f.write("while true; do\n")
            f.write("  read -r cmd\n") # Use -r
            f.write("  if [ -n \"$cmd\" ]; then\n") # Only echo if command is not empty
            f.write("    echo \"CMD_RECEIVED: $cmd\"\n") # Output to its stdout
            f.write("  fi\n")
            f.write("  if [ \"$cmd\" == \"stop\" ]; then\n")
            f.write("    echo 'STOP_CMD_RECEIVED. Exiting.'\n") # Output to its stdout
            f.write("    exit 0\n")
            f.write("  fi\n")
            f.write("  sleep 0.1\n") # Prevent tight loop if read isn't blocking
            f.write("done\n")
        os.chmod(dummy_script_path, 0o755) # Make it executable
        # No longer need to import os here as it's at the top

    app.run(host='0.0.0.0', port=5000, debug=True)
