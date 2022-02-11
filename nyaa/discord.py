from werkzeug.urls import url_encode
import requests


class DiscordOAuth2(object):
    def __init__(self, *, client_id=None, client_secret=None, redirect_uri=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None

    def _require(self, *values):
        for v in values:
            if getattr(self, v) is None:
                raise ValueError("Missing required value: {}".format(v))

    def get_authorize_url(self, *, scope="identify guilds guilds.members.read"):
        self._require("client_id", "redirect_uri")

        base = "https://discord.com/api/oauth2/authorize"
        query = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": scope,
            "redirect_uri": self.redirect_uri,
        }

        return f"{base}?{url_encode(query)}"

    def get_access_token(self, *, code):
        self._require("client_id", "client_secret", "redirect_uri")

        base = "https://discord.com/api/oauth2/token"
        query = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        r = requests.post(base, data=query)
        json = r.json()
        if r.status_code == 200:
            self.access_token = json["access_token"]

        return json, r.status_code

    def get_user_data(self, *, access_token=None):
        if access_token is None:
            access_token = self.access_token

        if access_token is None:
            raise ValueError("Missing access token")

        base = "https://discord.com/api/users/@me"
        headers = {"Authorization": f"Bearer {access_token}"}

        r = requests.get(base, headers=headers)
        return r.json(), r.status_code

    def get_user_guilds(self, *, access_token=None):
        if access_token is None:
            access_token = self.access_token

        if access_token is None:
            raise ValueError("Missing access token")

        base = "https://discord.com/api/users/@me/guilds"
        headers = {"Authorization": f"Bearer {access_token}"}

        r = requests.get(base, headers=headers)
        return r.json(), r.status_code

    def get_user_guild_member(self, *, guild_id, access_token=None):
        if access_token is None:
            access_token = self.access_token

        if access_token is None:
            raise ValueError("Missing access token")

        base = f"https://discord.com/api/users/@me/guilds/{guild_id}/member"
        headers = {"Authorization": f"Bearer {access_token}"}

        r = requests.get(base, headers=headers)
        return r.json(), r.status_code
