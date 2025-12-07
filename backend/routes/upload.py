from flask import Blueprint, request, jsonify, send_file, current_app, after_this_request
from flask_login import current_user
from backend.services.pdf_service import PDFService, PDFExtractionError
from backend.services.llm_service import LLMService, LLMError
from backend.services.file_service import FileService, FileServiceError
from backend.utils.rate_limiter import RateLimiter
from backend.config import Config
import os

upload_bp = Blueprint('upload', __name__, url_prefix='/api')


def get_llm_service():
    """Get LLM service instance"""
    return LLMService(
        provider=Config.LLM_PROVIDER,
        api_key=Config.OPENAI_API_KEY,
        model=Config.LLM_MODEL
    )


def get_file_service():
    """Get file service instance"""
    return FileService(Config.UPLOAD_FOLDER)


def get_rate_limiter():
    """Get rate limiter instance"""
    return RateLimiter(Config.ANONYMOUS_MAX_SUBMISSIONS_PER_YEAR)


@upload_bp.route('/upload', methods=['POST'])
def upload_files():
    """
    Upload and process PDF files.
    Handles concurrent uploads via session-based folders.
    """
    # Check if files were uploaded
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    if not files or len(files) == 0:
        return jsonify({'error': 'No files selected'}), 400

    # Filter out empty file inputs
    files = [f for f in files if f.filename]
    if not files:
        return jsonify({'error': 'No valid files provided'}), 400

    # Determine max files based on user type
    if current_user.is_authenticated:
        max_files = Config.REGISTERED_USER_MAX_FILES
    else:
        max_files = Config.ANONYMOUS_MAX_FILES
        # Check rate limit for anonymous users
        rate_limiter = get_rate_limiter()
        can_submit, error_msg, remaining = rate_limiter.check_limit()
        if not can_submit:
            return jsonify({'error': error_msg}), 429

    if len(files) > max_files:
        return jsonify({
            'error': f'Maximum {max_files} files allowed per submission'
        }), 400

    # Initialize services
    file_service = get_file_service()
    pdf_service = PDFService()
    llm_service = get_llm_service()

    # Create unique session folder for this upload (concurrent user isolation)
    session_folder = file_service.create_session_folder()

    try:
        processed_files = []
        errors = []

        for uploaded_file in files:
            # Validate file extension
            if not uploaded_file.filename.lower().endswith('.pdf'):
                errors.append({
                    'file': uploaded_file.filename,
                    'error': 'Not a PDF file'
                })
                continue

            # Save file to session folder
            filepath = file_service.save_uploaded_file(uploaded_file, session_folder)

            # Validate PDF
            is_valid, error_msg = pdf_service.validate_pdf(filepath)
            if not is_valid:
                errors.append({
                    'file': uploaded_file.filename,
                    'error': error_msg
                })
                try:
                    os.remove(filepath)
                except OSError:
                    pass  # File will be cleaned up with session folder
                continue

            try:
                # Extract text from PDF (only first 1-2 pages, up to abstract)
                text = pdf_service.extract_text(filepath)

                # Get filename from LLM
                new_filename = llm_service.generate_filename(text)

                processed_files.append((filepath, new_filename))

            except PDFExtractionError as e:
                errors.append({
                    'file': uploaded_file.filename,
                    'error': str(e)
                })
            except LLMError as e:
                errors.append({
                    'file': uploaded_file.filename,
                    'error': f'Failed to process: {str(e)}'
                })

        if not processed_files:
            # No files were successfully processed
            file_service.cleanup_session_immediate(session_folder)
            return jsonify({
                'error': 'No files could be processed',
                'details': errors
            }), 400

        # Process files (rename and possibly zip)
        result_path, is_zip = file_service.process_files(processed_files)

        # Record submission for anonymous users
        if not current_user.is_authenticated:
            rate_limiter = get_rate_limiter()
            rate_limiter.record_submission()

        # Schedule cleanup after sending file
        @after_this_request
        def cleanup(response):
            file_service.cleanup_session(session_folder, delay_seconds=30)
            return response

        # Determine download filename and mimetype
        download_name = os.path.basename(result_path)
        if is_zip:
            mimetype = 'application/zip'
        else:
            mimetype = 'application/pdf'

        # Send file with automatic download headers
        response = send_file(
            result_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name
        )

        # Add headers to indicate processing info
        response.headers['X-Files-Processed'] = str(len(processed_files))
        response.headers['X-Files-Errors'] = str(len(errors))

        return response

    except FileServiceError as e:
        file_service.cleanup_session_immediate(session_folder)
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        file_service.cleanup_session_immediate(session_folder)
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@upload_bp.route('/limits', methods=['GET'])
def get_limits():
    """Get current user's upload limits"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'max_files': Config.REGISTERED_USER_MAX_FILES,
            'remaining_submissions': None  # Unlimited for registered users
        })
    else:
        rate_limiter = get_rate_limiter()
        remaining = rate_limiter.get_remaining_submissions()
        return jsonify({
            'authenticated': False,
            'max_files': Config.ANONYMOUS_MAX_FILES,
            'remaining_submissions': remaining,
            'max_submissions_per_year': Config.ANONYMOUS_MAX_SUBMISSIONS_PER_YEAR
        })
