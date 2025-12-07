import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, current_user

from backend.config import Config
from backend.models.user import db, User
from backend.routes.auth import auth_bp
from backend.routes.admin import admin_bp
from backend.routes.upload import upload_bp


def create_app():
    """Application factory"""
    app = Flask(
        __name__,
        template_folder='../frontend/templates',
        static_folder='../frontend/static'
    )

    # Load config
    app.config.from_object(Config)
    Config.init_app(app)

    # Initialize extensions
    CORS(app, supports_credentials=True)
    db.init_app(app)

    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('main.login'))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(upload_bp)

    # Main routes (for serving HTML pages)
    from flask import Blueprint
    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def index():
        return render_template('index.html')

    @main_bp.route('/login')
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('main.index'))
        return render_template('login.html')

    @main_bp.route('/register')
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('main.index'))
        return render_template('register.html')

    @main_bp.route('/admin')
    def admin():
        if not current_user.is_authenticated or not current_user.is_admin:
            return redirect(url_for('main.login'))
        return render_template('admin.html')

    app.register_blueprint(main_bp)

    # Create database tables
    with app.app_context():
        db.create_all()
        # Create default admin user if none exists
        create_default_admin()

    return app


def create_default_admin():
    """Create a default admin user if no admin exists"""
    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        admin = User(
            email='admin@example.com',
            is_approved=True,
            is_admin=True
        )
        admin.set_password('admin123')  # Change this in production!
        db.session.add(admin)
        db.session.commit()
        print("Default admin created: admin@example.com / admin123")


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
