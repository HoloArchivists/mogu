import json
from ipaddress import ip_address
from urllib.parse import quote

import flask
import requests
from werkzeug.datastructures import CombinedMultiDict

from sqlalchemy.orm import joinedload

from nyaa import backend, forms, models, torrents
from nyaa.extensions import db
from nyaa.utils import cached_function
from nyaa.discord import DiscordOAuth2

app = flask.current_app
bp = flask.Blueprint("oauth2", __name__)


@bp.route("/discord/oauth2/callback")
def discord_callback():
    """
    Discord OAuth2 callback.
    """
    if "error" in flask.request.args:
        return flask.render_template("error.html", message=flask.request.args["error"])

    discord = DiscordOAuth2(
        client_id=app.config["DISCORD_CLIENT_ID"],
        client_secret=app.config["DISCORD_CLIENT_SECRET"],
        redirect_uri=app.config["DISCORD_REDIRECT_URI"],
    )

    discord_code = flask.request.args["code"]

    # Get the access token.
    response, status = discord.get_access_token(code=discord_code)
    if status != 200:
        return flask.render_template(
            "error.html",
            message="Failed to get access token from Discord",
            trace=response,
        )

    # Get the user's data.
    response, status = discord.get_user_data()
    if status != 200:
        return flask.render_template(
            "error.html", message="Failed to get user data", trace=response
        )

    user_id = response["id"]

    # Get the user's guilds.
    response, status = discord.get_user_guilds()
    if status != 200:
        return flask.render_template(
            "error.html", message="Failed to get user guilds", trace=response
        )

    user_guilds = [guild["id"] for guild in response]
    allowed_guild = app.config["DISCORD_GUILD"]

    # Check if the user is in the allowed guilds.
    if not allowed_guild in user_guilds:
        return flask.render_template(
            "error.html",
            message="Please join the discord server in the Help page and try again.",
        )

    # Get the user's roles.
    response, status = discord.get_user_guild_member(guild_id=allowed_guild)
    if status != 200:
        return flask.render_template(
            "error.html",
            message="Failed to get user roles",
            trace=response,
        )

    user_roles = response["roles"]
    role_admin = app.config["DISCORD_ROLE_ADMIN"]
    role_trusted = app.config["DISCORD_ROLE_TRUSTED"]

    # return json for debugging
    return flask.jsonify(
        discord_code=discord_code,
        user_id=user_id,
        guilds=user_guilds,
        roles=user_roles,
    )
