from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from backend.models.user import db, User

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    """List all users"""
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({
        'users': [user.to_dict() for user in users]
    })


@admin_bp.route('/pending', methods=['GET'])
@admin_required
def list_pending():
    """List users pending approval"""
    users = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
    return jsonify({
        'users': [user.to_dict() for user in users]
    })


@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@admin_required
def approve_user(user_id):
    """Approve a user"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_approved = True
    db.session.commit()

    return jsonify({
        'message': f'User {user.email} approved',
        'user': user.to_dict()
    })


@admin_bp.route('/reject/<int:user_id>', methods=['POST'])
@admin_required
def reject_user(user_id):
    """Reject and delete a user"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.is_admin:
        return jsonify({'error': 'Cannot reject admin users'}), 400

    email = user.email
    db.session.delete(user)
    db.session.commit()

    return jsonify({
        'message': f'User {email} rejected and removed'
    })


@admin_bp.route('/toggle-admin/<int:user_id>', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.id == current_user.id:
        return jsonify({'error': 'Cannot change your own admin status'}), 400

    user.is_admin = not user.is_admin
    db.session.commit()

    return jsonify({
        'message': f'Admin status toggled for {user.email}',
        'user': user.to_dict()
    })
