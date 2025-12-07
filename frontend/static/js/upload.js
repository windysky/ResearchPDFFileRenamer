// Upload handling with drag-and-drop support

class PDFUploader {
    constructor() {
        this.files = [];
        this.maxFiles = 5; // Default, will be updated from server

        // DOM elements
        this.dropzone = document.getElementById('dropzone');
        this.fileInput = document.getElementById('file-input');
        this.fileList = document.getElementById('file-list');
        this.filesUl = document.getElementById('files-ul');
        this.clearBtn = document.getElementById('clear-btn');
        this.uploadBtn = document.getElementById('upload-btn');
        this.progressSection = document.getElementById('progress-section');
        this.progressFill = document.getElementById('progress-fill');
        this.progressText = document.getElementById('progress-text');
        this.errorSection = document.getElementById('error-section');
        this.errorMessage = document.getElementById('error-message');
        this.successSection = document.getElementById('success-section');
        this.limitsInfo = document.getElementById('limits-info');

        this.init();
    }

    init() {
        this.loadLimits();
        this.setupEventListeners();
    }

    async loadLimits() {
        try {
            const response = await fetch('/api/limits', { credentials: 'include' });
            const data = await response.json();

            this.maxFiles = data.max_files;

            if (data.authenticated) {
                this.limitsInfo.textContent = `You can upload up to ${data.max_files} PDF files per submission.`;
            } else {
                this.limitsInfo.innerHTML = `
                    Guest mode: ${data.max_files} files per submission,
                    ${data.remaining_submissions} of ${data.max_submissions_per_year} submissions remaining this year.
                    <a href="/register">Register</a> for unlimited access.
                `;
            }
        } catch (error) {
            console.error('Failed to load limits:', error);
            this.limitsInfo.textContent = 'Upload your PDF files to rename them automatically.';
        }
    }

    setupEventListeners() {
        // Click to open file dialog
        this.dropzone.addEventListener('click', () => this.fileInput.click());

        // File input change
        this.fileInput.addEventListener('change', (e) => this.handleFiles(e.target.files));

        // Drag and drop
        this.dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropzone.classList.add('dragover');
        });

        this.dropzone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            this.dropzone.classList.remove('dragover');
        });

        this.dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropzone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });

        // Clear button
        this.clearBtn.addEventListener('click', () => this.clearFiles());

        // Upload button
        this.uploadBtn.addEventListener('click', () => this.uploadFiles());
    }

    handleFiles(fileList) {
        const newFiles = Array.from(fileList).filter(file => {
            // Only accept PDFs
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                this.showError(`${file.name} is not a PDF file`);
                return false;
            }
            // Check for duplicates
            if (this.files.some(f => f.name === file.name)) {
                return false;
            }
            return true;
        });

        // Check max files limit
        if (this.files.length + newFiles.length > this.maxFiles) {
            this.showError(`Maximum ${this.maxFiles} files allowed`);
            return;
        }

        this.files = [...this.files, ...newFiles];
        this.updateFileList();
        this.hideError();
        this.hideSuccess();
    }

    updateFileList() {
        if (this.files.length === 0) {
            this.fileList.style.display = 'none';
            return;
        }

        this.fileList.style.display = 'block';
        this.filesUl.innerHTML = this.files.map((file, index) => `
            <li>
                <span class="file-name">${this.escapeHtml(file.name)}</span>
                <span class="file-size">${this.formatSize(file.size)}</span>
                <button class="file-remove" onclick="uploader.removeFile(${index})">&times;</button>
            </li>
        `).join('');
    }

    removeFile(index) {
        this.files.splice(index, 1);
        this.updateFileList();
    }

    clearFiles() {
        this.files = [];
        this.fileInput.value = '';
        this.updateFileList();
        this.hideError();
        this.hideSuccess();
    }

    async uploadFiles() {
        if (this.files.length === 0) {
            this.showError('Please select at least one PDF file');
            return;
        }

        // Show progress
        this.showProgress();
        this.uploadBtn.disabled = true;
        this.clearBtn.disabled = true;

        // Create form data
        const formData = new FormData();
        this.files.forEach(file => {
            formData.append('files', file);
        });

        // Generate browser fingerprint for rate limiting
        const fingerprint = this.generateFingerprint();

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'X-Browser-Fingerprint': fingerprint
                },
                body: formData
            });

            if (response.ok) {
                // Success - download the file
                const blob = await response.blob();
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'renamed_papers.zip';

                if (contentDisposition) {
                    const match = contentDisposition.match(/filename="?(.+)"?/);
                    if (match) {
                        filename = match[1].replace(/"/g, '');
                    }
                }

                // Trigger automatic download
                this.downloadBlob(blob, filename);

                // Show success message
                this.hideProgress();
                this.showSuccess();
                this.clearFiles();

                // Reload limits (for anonymous users, count decreased)
                this.loadLimits();
            } else {
                const data = await response.json();
                this.hideProgress();
                this.showError(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.hideProgress();
            this.showError('Network error. Please try again.');
        } finally {
            this.uploadBtn.disabled = false;
            this.clearBtn.disabled = false;
        }
    }

    downloadBlob(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    showProgress() {
        this.progressSection.style.display = 'block';
        this.errorSection.style.display = 'none';
        this.successSection.style.display = 'none';
        this.progressText.textContent = 'Processing your files...';
    }

    hideProgress() {
        this.progressSection.style.display = 'none';
    }

    showError(message) {
        this.errorSection.style.display = 'block';
        this.errorMessage.textContent = message;
        this.successSection.style.display = 'none';
    }

    hideError() {
        this.errorSection.style.display = 'none';
    }

    showSuccess() {
        this.successSection.style.display = 'block';
        this.errorSection.style.display = 'none';
    }

    hideSuccess() {
        this.successSection.style.display = 'none';
    }

    formatSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    generateFingerprint() {
        // Simple browser fingerprint based on available properties
        const components = [
            navigator.userAgent,
            navigator.language,
            screen.width + 'x' + screen.height,
            new Date().getTimezoneOffset(),
            navigator.hardwareConcurrency || 'unknown',
            navigator.platform
        ];
        return this.hashCode(components.join('|'));
    }

    hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash).toString(16);
    }
}

// Initialize uploader when DOM is ready
let uploader;
document.addEventListener('DOMContentLoaded', () => {
    uploader = new PDFUploader();
});
