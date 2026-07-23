"""
Authentication helpers.
"""

from functools import wraps
from flask import session, redirect, url_for


def admin_required(f):
    """Decorator: redirect to admin login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated
