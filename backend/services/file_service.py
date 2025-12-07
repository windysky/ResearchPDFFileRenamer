import os
import shutil
import uuid
import zipfile
import threading
from typing import List, Tuple
from datetime import datetime


class FileService:
    """Service for file operations: rename, zip, cleanup"""

    def __init__(self, upload_folder: str):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    def create_session_folder(self) -> str:
        """
        Create a unique folder for this upload session.
        Uses UUID to ensure concurrent users don't interfere.

        Returns:
            Path to the session folder
        """
        session_id = str(uuid.uuid4())
        session_folder = os.path.join(self.upload_folder, session_id)
        os.makedirs(session_folder, exist_ok=True)
        return session_folder

    def save_uploaded_file(self, file, session_folder: str) -> str:
        """
        Save an uploaded file to the session folder.

        Returns:
            Path to the saved file
        """
        # Use original filename but sanitize it
        filename = self._sanitize_filename(file.filename)
        filepath = os.path.join(session_folder, filename)

        # Handle duplicate filenames
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{base}_{counter}{ext}"
            filepath = os.path.join(session_folder, filename)
            counter += 1

        file.save(filepath)
        return filepath

    def rename_file(self, original_path: str, new_filename: str) -> str:
        """
        Rename a file with the new filename.

        Returns:
            Path to the renamed file
        """
        folder = os.path.dirname(original_path)
        new_path = os.path.join(folder, new_filename)

        # Handle duplicate filenames
        base, ext = os.path.splitext(new_filename)
        counter = 1
        while os.path.exists(new_path) and new_path != original_path:
            new_filename = f"{base}_{counter}{ext}"
            new_path = os.path.join(folder, new_filename)
            counter += 1

        os.rename(original_path, new_path)
        return new_path

    def create_zip(self, files: List[str], session_folder: str) -> str:
        """
        Create a ZIP archive containing all processed files.

        Returns:
            Path to the ZIP file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"renamed_papers_{timestamp}.zip"
        zip_path = os.path.join(session_folder, zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filepath in files:
                arcname = os.path.basename(filepath)
                zipf.write(filepath, arcname)

        return zip_path

    def cleanup_session(self, session_folder: str, delay_seconds: int = 30):
        """
        Schedule cleanup of session folder after a delay.
        Runs in a separate thread to not block the response.
        """
        def do_cleanup():
            import time
            time.sleep(delay_seconds)
            try:
                if os.path.exists(session_folder):
                    shutil.rmtree(session_folder)
            except Exception:
                pass  # Ignore cleanup errors

        cleanup_thread = threading.Thread(target=do_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()

    def cleanup_session_immediate(self, session_folder: str):
        """Immediately clean up session folder"""
        try:
            if os.path.exists(session_folder):
                shutil.rmtree(session_folder)
        except Exception:
            pass

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to remove dangerous characters"""
        # Remove path separators and null bytes
        filename = os.path.basename(filename)
        # Remove potentially dangerous characters
        dangerous_chars = ['..', '/', '\\', '\x00', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        return filename or 'unnamed.pdf'

    def get_file_size(self, filepath: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(filepath)

    def process_files(self, files: List[Tuple[str, str]]) -> Tuple[str, bool]:
        """
        Process a list of (original_path, new_filename) tuples.
        Renames files and creates ZIP if multiple files.

        Returns:
            Tuple of (result_path, is_zip)
        """
        renamed_files = []
        session_folder = os.path.dirname(files[0][0]) if files else None

        for original_path, new_filename in files:
            new_path = self.rename_file(original_path, new_filename)
            renamed_files.append(new_path)

        if len(renamed_files) > 1:
            # Multiple files - create ZIP
            zip_path = self.create_zip(renamed_files, session_folder)
            return zip_path, True
        elif len(renamed_files) == 1:
            # Single file - return directly
            return renamed_files[0], False
        else:
            raise FileServiceError("No files to process")


class FileServiceError(Exception):
    """Custom exception for file service errors"""
    pass
