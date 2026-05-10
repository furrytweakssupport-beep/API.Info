import asyncio
import time
import httpx
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import defaultdict
from google.protobuf import json_format

from proto import FreeFire_pb2, main_pb2, AccountPersonalShow_pb2
from Crypto.Cipher import AES
import base64

app = Flask(__name__)
CORS(app)

# ===== CONFIG =====
MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')

USERAGENT = "Dalvik/2.1.0 (Linux; Android 13)"
RELEASEVERSION = "OB49"

cached_tokens = defaultdict(dict)

# ===== AES =====
def pad(data):
    pad_len = 16 - len(data) % 16
    return data + bytes([pad_len]) * pad_len

def encrypt(data):
    cipher = AES.new(MAIN_KEY, AES.MODE_CBC, MAIN_IV)
    return cipher.encrypt(pad(data))

# ===== TOKEN =====
async def get_token():
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = "uid=4044218743&password=96A37E2B8D306360A481BBE9552FCD395F2EFDAAD04792D1F0F38AD7ED1706B6&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"

    async with httpx.AsyncClient() as client:
        r = await client.post(url, data=payload)
        j = r.json()
        return j.get("access_token"), j.get("open_id")

# ===== LOGIN =====
async def login():
    token, open_id = await get_token()

    body = {
        "open_id": open_id,
        "open_id_type": "4",
        "login_token": token,
        "orign_platform_type": "4"
    }

    proto = FreeFire_pb2.LoginReq()
    json_format.ParseDict(body, proto)

    encrypted = encrypt(proto.SerializeToString())

    headers = {
        "User-Agent": USERAGENT,
        "Content-Type": "application/octet-stream",
        "ReleaseVersion": RELEASEVERSION
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://loginbp.ggblueshark.com/MajorLogin",
            data=encrypted,
            headers=headers
        )

        res = FreeFire_pb2.LoginRes()
        res.ParseFromString(r.content)

        return {
            "token": f"Bearer {res.token}",
            "server": res.server_url
        }

# ===== PLAYER INFO =====
async def fetch_player(uid):
    login_data = await login()

    proto = main_pb2.GetPlayerPersonalShow()
    proto.a = int(uid)
    proto.b = 7

    encrypted = encrypt(proto.SerializeToString())

    headers = {
        "Authorization": login_data["token"],
        "User-Agent": USERAGENT,
        "Content-Type": "application/octet-stream",
        "ReleaseVersion": RELEASEVERSION
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            login_data["server"] + "/GetPlayerPersonalShow",
            data=encrypted,
            headers=headers
        )

        msg = AccountPersonalShow_pb2.AccountPersonalShowInfo()
        msg.ParseFromString(r.content)

        return json_format.MessageToDict(msg, preserving_proto_field_name=True)

# ===== SAFE PARSER =====
def safe_get(d, path, default="N/A"):
    try:
        for p in path:
            d = d[p]
        return d
    except:
        return default

# ===== ROUTE =====
@app.route("/")
def home():
    return "API RUNNING"

@app.route("/player-info")
def player():
    uid = request.args.get("uid")

    if not uid:
        return jsonify({"error": "UID required"}), 400

    try:
        data = asyncio.run(fetch_player(uid))

        # ===== SAFE DATA EXTRACTION =====
        result = {
            "name": safe_get(data, ["basic_info", "nickname"]),
            "uid": uid,
            "level": safe_get(data, ["basic_info", "level"]),
            "likes": safe_get(data, ["basic_info", "liked"]),
            "exp": safe_get(data, ["basic_info", "exp"]),
            "bio": safe_get(data, ["basic_info", "signature"]),
            "region": safe_get(data, ["basic_info", "region"]),
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": "Failed to fetch player info",
            "details": str(e)
        }), 500
