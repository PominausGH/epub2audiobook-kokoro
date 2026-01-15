"""
Authentication Module
Session-based auth for the web app.
"""

from functools import wraps
from flask import request, redirect, url_for, session, g

from .database import get_session_user, create_session, delete_session, get_user_by_id


def get_current_user():
    """Get current logged-in user from session."""
    if hasattr(g, 'current_user'):
        return g.current_user

    user = None
    session_id = session.get('session_id')
    if session_id:
        user = get_session_user(session_id)

    g.current_user = user
    return user


def login_user(user):
    """Log in a user by creating a session."""
    session_id = create_session(user.id)
    session['session_id'] = session_id
    session.permanent = True


def logout_user():
    """Log out the current user."""
    session_id = session.get('session_id')
    if session_id:
        delete_session(session_id)
    session.pop('session_id', None)


def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return redirect(url_for('login', next=request.url))
        if not user.is_admin:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function
