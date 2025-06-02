document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded and parsed');

    // Helper function for API calls
    async function fetchData(url, options = {}) {
        try {
            const response = await fetch(url, options);
            // Try to parse JSON even for errors, as our API returns JSON errors
            const responseData = await response.json().catch(() => null);

            if (!response.ok) {
                const errorMessage = responseData && responseData.message ? responseData.message : response.statusText;
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorMessage}`);
            }
            return responseData; // Already parsed
        } catch (error) {
            console.error('Fetch error:', error.name, error.message);
            alert(`Error: ${error.message}`);
            return null; 
        }
    }

    // Get references to HTML elements
    const startServerBtn = document.getElementById('startServerBtn');
    const stopServerBtn = document.getElementById('stopServerBtn');
    const restartServerBtn = document.getElementById('restartServerBtn');
    const consoleOutput = document.getElementById('consoleOutput');
    const commandInput = document.getElementById('commandInput');
    const sendCommandBtn = document.getElementById('sendCommandBtn');
    const fileUploadInput = document.getElementById('fileUploadInput');
    const uploadFileBtn = document.getElementById('uploadFileBtn');
    const fileListDiv = document.getElementById('fileList');
    const serverStatusSpan = document.getElementById('serverStatus'); 
    const backupServerBtn = document.getElementById('backupServerBtn'); // Added backup button

    // --- Server Control Event Listeners ---
    if (startServerBtn) {
        startServerBtn.addEventListener('click', async () => {
            const data = await fetchData('/start_server', { method: 'POST' });
            if (data) {
                alert(data.message || 'Request processed.');
                fetchServerStatus(); // Update status after action
            }
        });
    }

    if (stopServerBtn) {
        stopServerBtn.addEventListener('click', async () => {
            const data = await fetchData('/stop_server', { method: 'POST' });
            if (data) {
                alert(data.message || 'Request processed.');
                fetchServerStatus(); 
            }
        });
    }

    if (restartServerBtn) {
        restartServerBtn.addEventListener('click', async () => {
            const data = await fetchData('/restart_server', { method: 'POST' });
            if (data) {
                alert(data.message || 'Request processed.');
                fetchServerStatus();
            }
        });
    }

    // --- Console Functions ---
    if (sendCommandBtn && commandInput) {
        sendCommandBtn.addEventListener('click', async () => {
            const commandValue = commandInput.value.trim();
            if (commandValue) {
                const data = await fetchData('/send_command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: commandValue })
                });
                if (data) {
                    alert(data.message || 'Command sent.');
                    commandInput.value = ''; // Clear input
                    setTimeout(fetchConsoleLog, 500); // Fetch log shortly after sending command
                }
            } else {
                alert('Please enter a command.');
            }
        });
    }

    async function fetchConsoleLog() {
        if (!consoleOutput) return;
        const data = await fetchData('/get_console_log');
        if (data && data.log !== undefined) {
            consoleOutput.textContent = data.log;
            // Auto-scroll to bottom
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        } else if (data && data.status === "error") {
            consoleOutput.textContent = `Error fetching log: ${data.message}`;
        }
    }

    async function fetchServerStatus() {
        if (!serverStatusSpan) return;
        const data = await fetchData('/get_server_status');
        if (data && data.server_status !== undefined) {
            serverStatusSpan.textContent = data.server_status;
        } else if (data && data.status === "error") {
            serverStatusSpan.textContent = `Error: ${data.message}`;
        } else {
            serverStatusSpan.textContent = "Unknown";
        }
    }

    // Periodic fetching
    setInterval(fetchConsoleLog, 5000); // every 5 seconds
    setInterval(fetchServerStatus, 5000); // every 5 seconds

    // Initial fetches
    fetchConsoleLog();
    fetchServerStatus();

    // --- File Management ---
    if (uploadFileBtn && fileUploadInput) {
        uploadFileBtn.addEventListener('click', async () => {
            const file = fileUploadInput.files[0];
            if (!file) {
                alert('Please select a file to upload.');
                return;
            }
            const formData = new FormData();
            formData.append('file', file);
            
            // Example for subdir - you might get this from another input
            // const subdirValue = document.getElementById('uploadSubdirInput')?.value;
            // if (subdirValue) {
            //     formData.append('subdir', subdirValue);
            // }

            const data = await fetchData('/upload_file', {
                method: 'POST',
                body: formData 
                // Content-Type is automatically set by browser for FormData
            });

            if (data) {
                alert(data.message || 'File upload processed.');
                fileUploadInput.value = ''; // Clear file input
                fetchFileList(); // Refresh file list
            }
        });
    }
    
    let currentPath = ""; // Keep track of the current path in file list

    async function fetchFileList(path = '') {
        if (!fileListDiv) return;
        const data = await fetchData(`/list_files?path=${encodeURIComponent(path)}`);
        if (data && data.files && data.directories) {
            fileListDiv.innerHTML = ''; // Clear current list
            currentPath = data.current_path || ""; // Update current path

            // Optional: Add a "Go Up" button if not in root
            if (currentPath) {
                const parentPath = currentPath.substring(0, currentPath.lastIndexOf(currentPath.includes('/') ? '/' : '\\'));
                const upButton = document.createElement('div');
                upButton.className = 'file-item directory';
                upButton.textContent = '⬆️ .. (Go Up)';
                upButton.addEventListener('click', () => fetchFileList(parentPath));
                fileListDiv.appendChild(upButton);
            }
            
            data.directories.forEach(dir => {
                const dirElement = document.createElement('div');
                dirElement.className = 'file-item directory';
                dirElement.textContent = `📁 ${dir}`;
                const nextPath = currentPath ? `${currentPath}/${dir}` : dir;
                dirElement.dataset.path = nextPath;
                dirElement.addEventListener('click', () => fetchFileList(nextPath));
                fileListDiv.appendChild(dirElement);
            });

            data.files.forEach(file => {
                const fileElement = document.createElement('div');
                fileElement.className = 'file-item file';
                const filePath = currentPath ? `${currentPath}/${file}` : file;
                fileElement.dataset.path = filePath;
                
                const fileNameSpan = document.createElement('span');
                fileNameSpan.textContent = `📄 ${file}`;
                fileElement.appendChild(fileNameSpan);

                const downloadLink = document.createElement('a');
                downloadLink.href = `/download_file/${encodeURIComponent(filePath)}`;
                downloadLink.textContent = 'Download';
                downloadLink.setAttribute('download', ''); // Suggests download with original filename
                fileElement.appendChild(downloadLink);
                
                fileListDiv.appendChild(fileElement);
            });

        } else if (data && data.status === "error") {
            fileListDiv.innerHTML = `<p>Error listing files: ${data.message}</p>`;
        } else {
            fileListDiv.innerHTML = '<p>Could not load file list.</p>';
        }
    }

    // Initial file list load
    if (fileListDiv) { // Check if the element exists before calling
      fetchFileList();
    }

    // --- Backup Event Listener ---
    if (backupServerBtn) {
        backupServerBtn.addEventListener('click', async () => {
            // Optional: Add confirmation dialog
            // if (!confirm('Are you sure you want to create a backup? This might take a moment.')) {
            //     return;
            // }
            
            alert('Starting backup... This might take a moment.'); // Give immediate feedback

            const data = await fetchData('/backup_server', { method: 'POST' });
            if (data) {
                alert(data.message || 'Backup request processed.');
                // Optionally, refresh a list of backups if displayed on the page
                // For example, if backups are listed in the file browser under a 'backups' path:
                // if (data.status === 'success' && currentPath.startsWith('backups')) {
                //    fetchFileList(currentPath); 
                // } else if (data.status === 'success') {
                //    fetchFileList(); // Or fetch a specific backup root listing
                // }
            }
        });
    }

});
