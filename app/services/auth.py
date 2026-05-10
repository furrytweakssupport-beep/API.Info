import httpx
import time
import json
from collections import defaultdict
from google.protobuf import json_format
from app.proto import FreeFire_pb2
from app.core.config import MAIN_KEY, MAIN_IV, USERAGENT, RELEASE_VERSION
from app.core.security import encrypt_aes

cached_tokens = defaultdict(dict)

async def get_guest_token(account):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"

    payload = account + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"

    headers = {
        "User-Agent": USERAGENT,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, data=payload, headers=headers)
        data = res.json()
        return data.get("access_token"), data.get("open_id")


async def create_session(region):
    account = "uid=xxxx&password=xxxx"  # replace if needed

    token, open_id = await get_guest_token(account)

    body = json.dumps({
        "open_id": open_id,
        "open_id_type": "4",
        "login_token": token,
        "orign_platform_type": "4"
    })

    proto = FreeFire_pb2.LoginReq()
    json_format.ParseDict(json.loads(body), proto)

    encrypted = encrypt_aes(MAIN_KEY, MAIN_IV, proto.SerializeToString())

    headers = {
        "User-Agent": USERAGENT,
        "Content-Type": "application/octet-stream",
        "ReleaseVersion": RELEASE_VERSION
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://loginbp.ggblueshark.com/MajorLogin",
            data=encrypted,
            headers=headers
        )

        msg = FreeFire_pb2.LoginRes()
        msg.ParseFromString(res.content)

        cached_tokens[region] = {
            "token": "Bearer " + msg.token,
            "server": msg.server_url,
            "expires": time.time() + 25000
        }


async def get_token(region):
    data = cached_tokens.get(region)

    if data and time.time() < data["expires"]:
        return data["token"], data["server"]

    await create_session(region)
    data = cached_tokens[region]

    return data["token"], data["server"]