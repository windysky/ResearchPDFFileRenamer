import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_api_key():
    """Load OpenAI API key from APISetting.txt"""
    api_file = os.path.join(BASE_DIR, 'APISetting.txt')
    try:
        with open(api_file, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError(f"API key file not found: {api_file}")


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB per file
    ALLOWED_EXTENSIONS = {'pdf'}

    # User limits
    REGISTERED_USER_MAX_FILES = 30
    ANONYMOUS_MAX_FILES = 5
    ANONYMOUS_MAX_SUBMISSIONS_PER_YEAR = 5

    # LLM settings
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'openai')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-4o-mini')
    OPENAI_API_KEY = None  # Loaded lazily

    # For future local LLM support
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')

    @classmethod
    def init_app(cls, app):
        """Initialize app-specific config"""
        cls.OPENAI_API_KEY = load_api_key()
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
