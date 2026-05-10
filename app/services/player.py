import httpx
import json
from google.protobuf import json_format
from app.proto import main_pb2, AccountPersonalShow_pb2
from app.core.config import MAIN_KEY, MAIN_IV, USERAGENT, RELEASE_VERSION
from app.core.security import encrypt_aes
from app.services.auth import get_token

async def get_player(uid, region):
    req = main_pb2.GetPlayerPersonalShow()
    req.a = int(uid)
    req.b = 7

    payload = encrypt_aes(MAIN_KEY, MAIN_IV, req.SerializeToString())

    token, server = await get_token(region)

    headers = {
        "User-Agent": USERAGENT,
        "Authorization": token,
        "Content-Type": "application/octet-stream",
        "ReleaseVersion": RELEASE_VERSION
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(server + "/GetPlayerPersonalShow", data=payload, headers=headers)

        msg = AccountPersonalShow_pb2.AccountPersonalShowInfo()
        msg.ParseFromString(res.content)

        return json.loads(json_format.MessageToJson(msg))