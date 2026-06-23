from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.auth import login_required
from app.services.user_service import authenticate_user, get_login_roles


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("USERNAME"):
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        user = authenticate_user(
            username=username,
            password=password,
            role=role
        )

        if user is None:
            flash("Benutzername, Passwort und Rolle passen nicht zusammen.", "error")
            return render_template(
                "login.html",
                roles=get_login_roles(),
                selected_role=role,
                username=username
            )

        session.clear()
        session["USERNAME"] = user["username"]
        session["ROLE"] = user["role"]
        session["SECURITYLEVEL"] = user["security_level"]

        flash("Anmeldung erfolgreich.", "success")

        next_url = request.args.get("next")
        if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
            next_url = url_for("dashboard.dashboard")

        return redirect(next_url)

    return render_template(
        "login.html",
        roles=get_login_roles(),
        selected_role="Lager"
    )


@auth_bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Sie wurden abgemeldet.", "success")
    return redirect(url_for("auth.login"))
