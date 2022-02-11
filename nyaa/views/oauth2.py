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

app = flask.current_app
bp = flask.Blueprint("oauth2", __name__)


@bp.route("/discord/oauth2/callback")
def discord_callback():
    """
    Discord OAuth2 callback.
    """
    if "error" in flask.request.args:
        return flask.jsonify({"error": flask.request.args["error"]})

    discord_code = flask.request.args["code"]

    # Get the access token.
    data = {
        "client_id": app.config["DISCORD_CLIENT_ID"],
        "client_secret": app.config["DISCORD_CLIENT_SECRET"],
        "grant_type": "authorization_code",
        "code": discord_code,
        "redirect_uri": flask.url_for("oauth2.discord_callback", _external=True),
    }

    response = requests.post("https://discordapp.com/api/oauth2/token", data=data)

    if response.status_code != 200:
        return flask.jsonify({"error": "Failed to get access token."})

    access_token = response.json()["access_token"]

    # Get the user's data.
    response = requests.get(
        "https://discordapp.com/api/users/@me",
        headers={"Authorization": "Bearer " + access_token},
    )

    if response.status_code != 200:
        return flask.jsonify({"error": "Failed to get user data."})

    user_id = response.json()["id"]

    # Get the user's guilds.
    response = requests.get(
        "https://discordapp.com/api/users/@me/guilds",
        headers={"Authorization": "Bearer " + access_token},
    )

    if response.status_code != 200:
        return flask.jsonify({"error": "Failed to get user guilds."})

    response_data = response.json()
    guilds = [guild["id"] for guild in response_data]

    # return json for debugging
    return flask.jsonify(
        discord_code=discord_code,
        access_token=access_token,
        user_id=user_id,
        guilds=guilds,
    )
