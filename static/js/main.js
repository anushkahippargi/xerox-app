document.addEventListener('DOMContentLoaded', () => {
    // File Upload Logic
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('document');
    const uploadForm = document.getElementById('uploadForm');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const submitBtn = document.getElementById('uploadBtn');
    
    // Panels
    const uploadPanel = document.getElementById('upload-panel');
    const successPanel = document.getElementById('success-panel');
    
    // Status tracking
    let pollInterval = null;
    let currentToken = null;

    if (dropArea && fileInput) {
        // Drag and drop events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            dropArea.classList.add('dragover');
        }

        function unhighlight(e) {
            dropArea.classList.remove('dragover');
        }

        dropArea.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            fileInput.files = files;
            updateFileName();
        }

        fileInput.addEventListener('change', updateFileName);

        function updateFileName() {
            if (fileInput.files.length > 0) {
                fileNameDisplay.textContent = `Selected: ${fileInput.files[0].name}`;
            } else {
                fileNameDisplay.textContent = '';
            }
        }

        // Form Submission
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (fileInput.files.length === 0) {
                alert('Please select a file to print.');
                return;
            }

            const formData = new FormData(uploadForm);
            
            // UI Loading state
            const originalBtnHtml = submitBtn.innerHTML;
            submitBtn.innerHTML = '<div class="loader"></div> Processing...';
            submitBtn.disabled = true;

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showSuccessPanel(data.token, data.qr_code);
                } else {
                    alert(data.error || 'Failed to upload document');
                    submitBtn.innerHTML = originalBtnHtml;
                    submitBtn.disabled = false;
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred during upload.');
                submitBtn.innerHTML = originalBtnHtml;
                submitBtn.disabled = false;
            }
        });
    }

    function showSuccessPanel(token, qrBase64) {
        uploadPanel.classList.add('hidden');
        successPanel.classList.remove('hidden');
        
        document.getElementById('tokenDisplay').textContent = token;
        document.getElementById('qrDisplay').src = 'data:image/png;base64,' + qrBase64;
        
        currentToken = token;
        startStatusPolling();
    }

    function startStatusPolling() {
        if (!currentToken) return;
        
        const statusBadge = document.getElementById('liveStatus');
        const loader = document.getElementById('statusLoader');
        
        loader.classList.remove('hidden');
        
        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/status/${currentToken}`);
                if (response.ok) {
                    const data = await response.json();
                    
                    // Update classes
                    statusBadge.className = `status-badge ${data.status.toLowerCase()}`;
                    statusBadge.textContent = data.status;
                    
                    if (data.status === 'Completed') {
                        loader.classList.add('hidden');
                        clearInterval(pollInterval);
                        if (window.Notification && Notification.permission === "granted") {
                            new Notification("Print Completed!", {
                                body: `Your document for token ${currentToken} is ready for pickup.`
                            });
                        }
                    }
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 3000); // Check every 3 seconds
    }

    // Request Notification Permission (if available)
    if (window.Notification && Notification.permission !== "denied") {
        Notification.requestPermission();
    }
});
