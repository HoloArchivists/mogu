import binascii
import time
from datetime import datetime, timedelta
from ipaddress import ip_address

import flask

from nyaa import email, forms, models
from nyaa.extensions import db, limiter
from nyaa.utils import sha1_hash
from nyaa.views.users import (
    get_activation_link,
    get_password_reset_link,
    get_serializer,
)

app = flask.current_app
bp = flask.Blueprint("account", __name__)


@bp.route("/logout")
def logout():
    flask.g.user = None
    flask.session.permanent = False
    flask.session.modified = False

    response = flask.make_response(flask.redirect(redirect_url()))
    response.set_cookie(app.session_cookie_name, expires=0)
    return response


def _check_for_multi_account(ip, cooldown):
    if not cooldown:
        return False
    cooldown_timestamp = datetime.utcnow() - timedelta(seconds=cooldown)
    q = models.User.query.filter(
        ip == models.User.registration_ip, models.User.created_time > cooldown_timestamp
    )
    return db.session.query(q.exists()).scalar()


@bp.route("/profile", methods=["GET", "POST"])
def profile():
    if not flask.g.user:
        # so we don't get stuck in infinite loop when signing out
        return flask.redirect(flask.url_for("main.home"))

    form = forms.ProfileForm(flask.request.form)

    if flask.request.method == "POST":
        if form.authorized_submit and form.validate():
            # Disable email and password change
            flask.flash(
                flask.Markup("<strong>Updating email or password is disabled</strong>"),
                "danger",
            )
            return flask.redirect("/profile")

            user = flask.g.user
            new_email = form.email.data.strip()
            new_password = form.new_password.data

            if new_email:
                if form.current_password.data != user.password_hash:
                    flask.flash(
                        flask.Markup(
                            "<strong>Email change failed!</strong> Incorrect password."
                        ),
                        "danger",
                    )
                    return flask.redirect("/profile")
                user.email = form.email.data
                flask.flash(
                    flask.Markup("<strong>Email successfully changed!</strong>"),
                    "success",
                )

            if new_password:
                if form.current_password.data != user.password_hash:
                    flask.flash(
                        flask.Markup(
                            "<strong>Password change failed!</strong> Incorrect password."
                        ),
                        "danger",
                    )
                    return flask.redirect("/profile")
                user.password_hash = form.new_password.data
                flask.flash(
                    flask.Markup("<strong>Password successfully changed!</strong>"),
                    "success",
                )
            db.session.add(user)
            db.session.commit()
            flask.g.user = user
            return flask.redirect("/profile")

        elif form.submit_settings:
            user = flask.g.user
            if user.preferences is None:
                preferences = models.UserPreferences(user.id)
                db.session.add(preferences)
                db.session.commit()
            user.preferences.hide_comments = form.hide_comments.data
            flask.flash(
                flask.Markup("<strong>Preferences successfully changed!</strong>"),
                "success",
            )
            db.session.add(user)
            db.session.commit()
            flask.g.user = user
            return flask.redirect("/profile")

    return flask.render_template("profile.html", form=form)


def redirect_url():
    next_url = flask.request.args.get("next", "")
    referrer = flask.request.referrer or ""

    target_url = (
        # Use ?next= param if it's a local (/foo/bar) path
        (next_url.startswith("/") and next_url)
        or
        # Use referrer if it's on our own host
        (referrer.startswith(flask.request.host_url) and referrer)
    )

    # Return the target, avoiding infinite loops
    if target_url and target_url != flask.request.url:
        return target_url

    # Default to index
    return flask.url_for("main.home")
