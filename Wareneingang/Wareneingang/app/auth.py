from functools import wraps

from flask import flash, redirect, request, session, url_for


LAGER_ROLE = "Lager"
MANAGEMENT_ROLE = "Management"
ADMIN_ROLE = "Admin"


def is_logged_in():
    return bool(session.get("USERNAME") and session.get("ROLE"))


def current_username():
    return session.get("USERNAME")


def current_role():
    return session.get("ROLE")


def current_security_level():
    return int(session.get("SECURITYLEVEL", 0))


def is_admin():
    return current_role() == ADMIN_ROLE


def _next_url():
    if request.query_string:
        return request.full_path

    return request.path


def login_required(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash("Bitte melden Sie sich zuerst an.", "error")
            return redirect(url_for("auth.login", next=_next_url()))

        return view_function(*args, **kwargs)

    return decorated_function


def require_security_level(level):
    """
    Securitylevel-Decorator aus dem Systemkonzept fuer geschuetzte Flask-Routen.
    """

    def decorator(view_function):
        @wraps(view_function)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_security_level() < level:
                flash("Keine Berechtigung für diese Funktion.", "error")
                return redirect(url_for("dashboard.dashboard"))

            return view_function(*args, **kwargs)

        return decorated_function

    return decorator


def require_roles(*roles):
    def decorator(view_function):
        @wraps(view_function)
        @login_required
        def decorated_function(*args, **kwargs):
            if not is_admin() and current_role() not in roles:
                flash("Keine Berechtigung für diese Funktion.", "error")
                return redirect(url_for("dashboard.dashboard"))

            return view_function(*args, **kwargs)

        return decorated_function

    return decorator


def can_view_goods_receipts():
    return current_role() in {LAGER_ROLE, MANAGEMENT_ROLE, ADMIN_ROLE}


def can_create_goods_receipt():
    return current_role() in {LAGER_ROLE, ADMIN_ROLE}


def can_edit_goods_receipt_items():
    return current_role() in {LAGER_ROLE, ADMIN_ROLE}


def can_make_management_decision():
    return current_role() in {MANAGEMENT_ROLE, ADMIN_ROLE}


def can_view_admin_pages():
    return is_admin()


def can_change_goods_receipt_status(current_status, target_status):
    try:
        current_status = int(current_status)
        target_status = int(target_status)
    except (TypeError, ValueError):
        return False

    if is_admin():
        return True

    lager_transitions = {
        (200, 201),
        (201, 202),
        (201, 203),
        (203, 204),
    }
    management_transitions = {
        (204, 202),
        (204, 205),
    }

    if current_role() == LAGER_ROLE:
        return (current_status, target_status) in lager_transitions

    if current_role() == MANAGEMENT_ROLE:
        return (current_status, target_status) in management_transitions

    return False


def auth_template_context():
    return {
        "current_username": current_username(),
        "current_role": current_role(),
        "current_security_level": current_security_level(),
        "can_view_goods_receipts": can_view_goods_receipts(),
        "can_create_goods_receipt": can_create_goods_receipt(),
        "can_edit_goods_receipt_items": can_edit_goods_receipt_items(),
        "can_make_management_decision": can_make_management_decision(),
        "can_view_admin_pages": can_view_admin_pages(),
    }
