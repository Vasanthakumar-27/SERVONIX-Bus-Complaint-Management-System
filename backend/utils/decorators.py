"""Authentication decorators"""
from functools import wraps
from flask import jsonify
from auth.utils import require_role
from .helpers import get_token_from_request


def get_current_user():
    """Get current authenticated user (any role)"""
    token = get_token_from_request()
    return require_role(token, ['user', 'admin', 'head'])


def require_user_auth():
    """Require user, admin, or head authentication"""
    token = get_token_from_request()
    return require_role(token, ['user', 'admin', 'head'])


def require_admin_auth():
    """Require admin or head authentication"""
    token = get_token_from_request()
    return require_role(token, ['admin', 'head'])


def require_head_auth():
    """Require head authentication"""
    token = get_token_from_request()
    return require_role(token, ['head'])
