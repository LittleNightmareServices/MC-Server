import subprocess
import os
import shutil
import time
import datetime

# --- Global Variables (Conceptual for a single server instance for now) ---
SERVER_PROCESS = None

# Base directory for all server instances
BASE_SERVER_INSTANCES_DIR = os.path.abspath("minecraft_server_hoster/server_instances")

# Default server instance - specific paths will be constructed in functions
DEFAULT_SERVER_DIR_NAME = "default_server"
DEFAULT_SERVER_PATH = os.path.join(BASE_SERVER_INSTANCES_DIR, DEFAULT_SERVER_DIR_NAME)
DEFAULT_LOGS_DIR = os.path.join(DEFAULT_SERVER_PATH, "logs")

# Ensure the default server directory and its logs subdirectory exist
os.makedirs(DEFAULT_SERVER_PATH, exist_ok=True)
os.makedirs(DEFAULT_LOGS_DIR, exist_ok=True)

# --- Server Management Functions ---

def start_server(jar_file="server.jar", server_dir_name=DEFAULT_SERVER_DIR_NAME, memory_mb=1024):
    global SERVER_PROCESS

    server_path = os.path.join(BASE_SERVER_INSTANCES_DIR, server_dir_name)
    jar_path = os.path.join(server_path, jar_file)
    log_dir = os.path.join(server_path, "logs") # For completeness, though Popen output handles current log

    os.makedirs(server_path, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True) # Ensure log directory for this specific instance also exists

    if not os.path.exists(jar_path):
        return {"status": "error", "message": f"Server JAR not found at {jar_path}."}

    if SERVER_PROCESS is None or SERVER_PROCESS.poll() is not None:
        if jar_path.endswith(".jar"):
            command = ["java", f"-Xmx{memory_mb}M", f"-Xms{memory_mb}M", "-jar", jar_path, "nogui"]
        else: # Assume it's an executable script for our dummy server
            command = [jar_path]
        
        try:
            # Note: For live console streaming to web UI, this needs more sophisticated handling (e.g., threads, websockets)
            # For now, stdout/stderr go to files or can be read via SERVER_PROCESS.stdout if needed by another function.
            # The actual latest.log will be written by the Minecraft server itself.
            SERVER_PROCESS = subprocess.Popen(
                command,
                cwd=server_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, # Capture output
                stderr=subprocess.STDOUT, # Redirect stderr to stdout
                text=True,
                bufsize=1, # Line buffered
                universal_newlines=True,
                # stderr=subprocess.PIPE # Keep separate for initial error check
            )
            # Quick check for immediate errors (optional, for debugging)
            # time.sleep(0.5) # Give it a fraction of a second
            # if SERVER_PROCESS.poll() is not None:
            #     out, err = SERVER_PROCESS.communicate()
            #     error_message = f"Server process terminated immediately. stdout: {out}, stderr: {err}"
            #     SERVER_PROCESS = None # Clear it
            #     return {"status": "error", "message": error_message}
                
            return {"status": "success", "message": f"Server starting in {server_path}..."}
        except Exception as e:
            return {"status": "error", "message": f"Failed to start server: {str(e)}"}
    else:
        return {"status": "error", "message": "Server is already running."}

def stop_server():
    global SERVER_PROCESS
    if SERVER_PROCESS and SERVER_PROCESS.poll() is None: # Server is running
        try:
            SERVER_PROCESS.stdin.write("stop\n")
            SERVER_PROCESS.stdin.flush()
        except Exception as e:
            # Handle broken pipe if process died unexpectedly
            print(f"Error sending 'stop' command: {e}. Forcing termination.")

        # Wait for graceful shutdown
        for _ in range(10): # Try for 10 seconds
            if SERVER_PROCESS.poll() is not None:
                break
            time.sleep(1)
        
        if SERVER_PROCESS.poll() is None: # Still running
            print("Server did not stop gracefully, terminating...")
            SERVER_PROCESS.terminate()
            time.sleep(5) # Wait for termination
            if SERVER_PROCESS.poll() is None: # Still running
                print("Server did not terminate, killing...")
                SERVER_PROCESS.kill()
        
        SERVER_PROCESS = None
        return {"status": "success", "message": "Server stopped."}
    else:
        SERVER_PROCESS = None # Ensure it's None if it was found to be not running
        return {"status": "error", "message": "Server is not running."}

def get_server_status():
    global SERVER_PROCESS
    if SERVER_PROCESS:
        poll_result = SERVER_PROCESS.poll()
        if poll_result is None:
            return "running"
        else:
            output = ""
            try:
                # Attempt to read any output the process might have generated before exiting
                # stdout is a pipe, read non-blockingly or with timeout if possible,
                # but communicate() is simpler for a one-off after process termination.
                # SERVER_PROCESS.stdout is TextIOWrapper, so it's text.
                # communicate() should be called only once.
                if hasattr(SERVER_PROCESS, '_communicated'): # crude check if communicated before
                     output = "[already communicated]"
                elif SERVER_PROCESS.stdout:
                    # stdout_data, stderr_data = SERVER_PROCESS.communicate(timeout=1) # timeout helps prevent hangs
                    # output = f"stdout: {stdout_data}, stderr: {stderr_data}"
                    # For now, let's assume stdout contains merged output due to stderr=subprocess.STDOUT
                    stdout_data = SERVER_PROCESS.stdout.read() # This might be empty if already read
                    output = f"output: {stdout_data}"
                    SERVER_PROCESS._communicated = True # mark it
            except Exception as e:
                output = f"[Error reading output: {str(e)}]"
            
            # SERVER_PROCESS = None # It's stopped, clear it for next start
            return f"stopped (exit code: {poll_result}, {output})"
    return "stopped"


# --- Backup Management ---
BACKUPS_DIR = os.path.abspath("minecraft_server_hoster/backups")
os.makedirs(BACKUPS_DIR, exist_ok=True)

def create_backup(server_dir_name="default_server", backup_base_name="backup"):
    """
    Creates a zip backup of the specified server instance directory.
    """
    server_instance_path = os.path.join(BASE_SERVER_INSTANCES_DIR, server_dir_name)

    if not os.path.exists(server_instance_path) or not os.path.isdir(server_instance_path):
        return {"status": "error", "message": f"Server instance '{server_dir_name}' not found at {server_instance_path}."}

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_filename_stem = f"{backup_base_name}-{server_dir_name}-{timestamp}"
    # archive_path_without_ext is where shutil will place the archive.
    # shutil.make_archive automatically adds the extension (e.g., .zip)
    archive_path_name_for_shutil = os.path.join(BACKUPS_DIR, backup_filename_stem)

    try:
        # root_dir should be the parent of the directory we want to archive.
        # base_dir is the name of the directory to archive.
        # Example: to archive server_instances/default_server,
        # root_dir = server_instances
        # base_dir = default_server
        
        root_dir_for_archive = os.path.dirname(server_instance_path)
        base_dir_to_archive = os.path.basename(server_instance_path)

        # shutil.make_archive returns the full path to the created archive
        archive_full_path = shutil.make_archive(
            base_name=archive_path_name_for_shutil, 
            format='zip', 
            root_dir=root_dir_for_archive,
            base_dir=base_dir_to_archive
        )
        
        actual_backup_filename = os.path.basename(archive_full_path) # e.g., backup-default_server-20231027-123456.zip
        
        return {"status": "success", 
                "message": f"Backup created: {actual_backup_filename}", 
                "backup_file": actual_backup_filename}
    except Exception as e:
        return {"status": "error", "message": f"Backup creation failed: {str(e)}"}


def read_console_log(server_dir_name=DEFAULT_SERVER_DIR_NAME, lines=50):
    log_path = os.path.join(BASE_SERVER_INSTANCES_DIR, server_dir_name, "logs", "latest.log")
    
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r') as f:
                log_lines = f.readlines()
            return "".join(log_lines[-lines:])
        except Exception as e:
            return f"Error reading log file: {str(e)}"
    else:
        # Check if the server process itself has any output (e.g. if server failed before creating latest.log)
        # This is a very basic way to get some output if latest.log isn't there yet.
        # A better system would pipe Popen's stdout to a file AND to a live stream.
        if SERVER_PROCESS and SERVER_PROCESS.stdout:
            # Non-blocking read attempt - this is not robust for continuous logging
            # For a real scenario, a separate thread would read SERVER_PROCESS.stdout
            try:
                # This is just a snapshot, not a live log.
                # And reading directly from PIPE like this can be problematic.
                # For now, we are mostly relying on latest.log
                return "Log file not found, and live process output reading is not fully implemented here. Check server directory."
            except Exception as e:
                return f"Log file not found. Error attempting to read process stdout: {str(e)}"
        return "Log file not found."


def send_minecraft_command(command, server_dir_name=DEFAULT_SERVER_DIR_NAME): # server_dir_name not used yet with single SERVER_PROCESS
    global SERVER_PROCESS
    if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
        try:
            SERVER_PROCESS.stdin.write(command + "\n")
            SERVER_PROCESS.stdin.flush()
            return {"status": "success", "message": f"Command '{command}' sent."}
        except Exception as e:
            return {"status": "error", "message": f"Failed to send command: {str(e)}"}
    else:
        return {"status": "error", "message": "Server is not running or command input is not available."}

# Example of how you might create a dummy server.jar for testing:
# if __name__ == '__main__':
#     # Create a dummy server.jar in the default server instance directory
#     # This is NOT a real Minecraft server jar.
#     dummy_jar_path = os.path.join(DEFAULT_SERVER_PATH, "server.jar")
#     if not os.path.exists(dummy_jar_path):
#         print(f"Creating dummy server.jar at {dummy_jar_path} for testing...")
#         with open(dummy_jar_path, 'w') as f:
#             f.write("#!/bin/bash\n")
#             f.write("echo 'Dummy Minecraft Server Started. Type stop to exit.'\n")
#             f.write("mkdir -p logs\n")
#             f.write("touch logs/latest.log\n")
#             f.write("echo '[DUMMY] Server Log Initialized' > logs/latest.log\n")
#             f.write("while true; do\n")
#             f.write("  read cmd\n")
#             f.write("  echo \"[DUMMY] CMD: $cmd\" >> logs/latest.log\n")
#             f.write("  if [ \"$cmd\" == \"stop\" ]; then\n")
#             f.write("    echo 'Dummy Minecraft Server Stopping.'\n")
#             f.write("    exit 0\n")
#             f.write("  fi\n")
#             f.write("done\n")
#         os.chmod(dummy_jar_path, 0o755) # Make it executable
#     else:
#         print(f"Dummy server.jar already exists at {dummy_jar_path}")

#     # Test functions (optional, run this file directly)
#     # print(start_server(jar_file="server.jar"))
#     # time.sleep(2)
#     # print(get_server_status())
#     # print(send_minecraft_command("say Hello from test"))
#     # time.sleep(1)
#     # print(read_console_log())
#     # print(stop_server())
#     # print(get_server_status())
