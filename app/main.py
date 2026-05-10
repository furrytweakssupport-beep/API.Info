import asyncio
import time
import httpx
import json
from collections import defaultdict
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from cachetools import TTLCache
from typing import Tuple

from app.proto import FreeFire_pb2, main_pb2, AccountPersonalShow_pb2
from google.protobuf import json_format
from google.protobuf.message import Message
from Crypto.Cipher import AES
import base64

# ================= CONFIG =================

MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')

# 🔥 Updated version (important)
RELEASEVERSION = "OB53"

USERAGENT = "Dalvik/2.1.0 (Linux; Android 13)"

# Keep small for Vercel
SUPPORTED_REGIONS = {"IND"}

# ================= APP =================

app = Flask(__name__)
CORS(app)

cache = TTLCache(maxsize=100, ttl=300)
cached_tokens = defaultdict(dict)

# ================= HELPERS =================

def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    return text + bytes([padding_length] * padding_length)

def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(plaintext))

def decode_protobuf(data: bytes, message_type):
    try:
        msg = message_type()
        msg.ParseFromString(data)
        return msg
    except Exception as e:
        print("PROTO DECODE ERROR:", e)
        return None

async def json_to_proto(json_data: str, proto_message: Message) -> bytes:
    json_format.ParseDict(json.loads(json_data), proto_message)
    return proto_message.SerializeToString()

# ================= ACCOUNT =================

def get_account_credentials(region: str) -> str:
    return "uid=4044218743&password=96A37E2B8D306360A481BBE9552FCD395F2EFDAAD04792D1F0F38AD7ED1706B6"

# ================= TOKEN =================

async def get_access_token(account: str):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"

    payload = account + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"

    headers = {
        "User-Agent": USERAGENT,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data=payload, headers=headers)
            data = resp.json()
            return data.get("access_token"), data.get("open_id")
    except Exception as e:
        print("TOKEN ERROR:", e)
        return None, None

async def create_jwt(region: str):
    account = get_account_credentials(region)

    token_val, open_id = await get_access_token(account)

    if not token_val:
        raise Exception("Failed to get access token")

    body = json.dumps({
        "open_id": open_id,
        "open_id_type": "4",
        "login_token": token_val,
        "orign_platform_type": "4"
    })

    proto_bytes = await json_to_proto(body, FreeFire_pb2.LoginReq())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, proto_bytes)

    url = "https://loginbp.ggblueshark.com/MajorLogin"

    headers = {
        "User-Agent": USERAGENT,
        "Content-Type": "application/octet-stream",
        "X-Unity-Version": "2018.4.11f1",
        "ReleaseVersion": RELEASEVERSION
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, data=payload, headers=headers)

        decoded = decode_protobuf(resp.content, FreeFire_pb2.LoginRes)

        if not decoded:
            raise Exception("Login protobuf decode failed")

        msg = json.loads(json_format.MessageToJson(decoded))

        cached_tokens[region] = {
            "token": f"Bearer {msg.get('token','')}",
            "server_url": msg.get("serverUrl",""),
            "expires_at": time.time() + 25000
        }

async def get_token(region: str):
    info = cached_tokens.get(region)

    if info and time.time() < info["expires_at"]:
        return info["token"], info["server_url"]

    await create_jwt(region)
    info = cached_tokens[region]
    return info["token"], info["server_url"]

# ================= PLAYER =================

async def GetAccountInformation(uid, region):

    payload = await json_to_proto(
        json.dumps({"a": uid, "b": 7}),
        main_pb2.GetPlayerPersonalShow()
    )

    encrypted = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, payload)

    token, server = await get_token(region)

    headers = {
        "User-Agent": USERAGENT,
        "Content-Type": "application/octet-stream",
        "Authorization": token,
        "X-Unity-Version": "2018.4.11f1",
        "ReleaseVersion": RELEASEVERSION
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(server + "/GetPlayerPersonalShow", data=encrypted, headers=headers)

        decoded = decode_protobuf(resp.content, AccountPersonalShow_pb2.AccountPersonalShowInfo)

        if not decoded:
            return None

        return json.loads(json_format.MessageToJson(decoded))

# ================= ROUTES =================

@app.route("/")
def home():
    return "API running ✅"

@app.route("/player-info")
def player_info():

    uid = request.args.get("uid")
    region = request.args.get("region", "IND").upper()

    if not uid:
        return jsonify({"error": "UID required"}), 400

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        data = loop.run_until_complete(GetAccountInformation(uid, region))

        loop.close()

        if not data:
            return jsonify({"error": "No data returned from server"}), 500

        # SAFE ACCESS (no crash)
        basic = data.get("basicInfo", {})

        result = {
            "name": basic.get("nickname", "Unknown"),
            "uid": basic.get("accountId", uid),
            "level": basic.get("level", 0),
            "likes": basic.get("liked", 0),
            "region": region,
            "raw": data
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": "Failed",
            "details": str(e)
        }), 500import asyncio
import time
import httpx
import json
from collections import defaultdict
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from cachetools import TTLCache
from typing import Tuple

from app.proto import FreeFire_pb2, main_pb2, AccountPersonalShow_pb2
from google.protobuf import json_format
from google.protobuf.message import Message
from Crypto.Cipher import AES
import base64

# ================= CONFIG =================

MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')

# 🔥 Updated version (important)
RELEASEVERSION = "OB53"

USERAGENT = "Dalvik/2.1.0 (Linux; Android 13)"

# Keep small for Vercel
SUPPORTED_REGIONS = {"IND"}

# ================= APP =================

app = Flask(__name__)
CORS(app)

cache = TTLCache(maxsize=100, ttl=300)
cached_tokens = defaultdict(dict)

# ================= HELPERS =================

def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    return text + bytes([padding_length] * padding_length)

def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(plaintext))

def decode_protobuf(data: bytes, message_type):
    try:
        msg = message_type()
        msg.ParseFromString(data)
        return msg
    except Exception as e:
        print("PROTO DECODE ERROR:", e)
        return None

async def json_to_proto(json_data: str, proto_message: Message) -> bytes:
    json_format.ParseDict(json.loads(json_data), proto_message)
    return proto_message.SerializeToString()

# ================= ACCOUNT =================

def get_account_credentials(region: str) -> str:
    return "uid=4044218743&password=96A37E2B8D306360A481BBE9552FCD395F2EFDAAD04792D1F0F38AD7ED1706B6"

# ================= TOKEN =================

async def get_access_token(account: str):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"

    payload = account + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"

    headers = {
        "User-Agent": USERAGENT,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data=payload, headers=headers)
            data = resp.json()
            return data.get("access_token"), data.get("open_id")
    except Exception as e:
        print("TOKEN ERROR:", e)
        return None, None

async def create_jwt(region: str):
    account = get_account_credentials(region)

    token_val, open_id = await get_access_token(account)

    if not token_val:
        raise Exception("Failed to get access token")

    body = json.dumps({
        "open_id": open_id,
        "open_id_type": "4",
        "login_token": token_val,
        "orign_platform_type": "4"
    })

    proto_bytes = await json_to_proto(body, FreeFire_pb2.LoginReq())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, proto_bytes)

    url = "https://loginbp.ggblueshark.com/MajorLogin"

    headers = {
        "User-Agent": USERAGENT,
        "Content-Type": "application/octet-stream",
        "X-Unity-Version": "2018.4.11f1",
        "ReleaseVersion": RELEASEVERSION
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, data=payload, headers=headers)

        decoded = decode_protobuf(resp.content, FreeFire_pb2.LoginRes)

        if not decoded:
            raise Exception("Login protobuf decode failed")

        msg = json.loads(json_format.MessageToJson(decoded))

        cached_tokens[region] = {
            "token": f"Bearer {msg.get('token','')}",
            "server_url": msg.get("serverUrl",""),
            "expires_at": time.time() + 25000
        }

async def get_token(region: str):
    info = cached_tokens.get(region)

    if info and time.time() < info["expires_at"]:
        return info["token"], info["server_url"]

    await create_jwt(region)
    info = cached_tokens[region]
    return info["token"], info["server_url"]

# ================= PLAYER =================

async def GetAccountInformation(uid, region):

    payload = await json_to_proto(
        json.dumps({"a": uid, "b": 7}),
        main_pb2.GetPlayerPersonalShow()
    )

    encrypted = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, payload)

    token, server = await get_token(region)

    headers = {
        "User-Agent": USERAGENT,
        "Content-Type": "application/octet-stream",
        "Authorization": token,
        "X-Unity-Version": "2018.4.11f1",
        "ReleaseVersion": RELEASEVERSION
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(server + "/GetPlayerPersonalShow", data=encrypted, headers=headers)

        decoded = decode_protobuf(resp.content, AccountPersonalShow_pb2.AccountPersonalShowInfo)

        if not decoded:
            return None

        return json.loads(json_format.MessageToJson(decoded))

# ================= ROUTES =================

@app.route("/")
def home():
    return "API running ✅"

@app.route("/player-info")
def player_info():

    uid = request.args.get("uid")
    region = request.args.get("region", "IND").upper()

    if not uid:
        return jsonify({"error": "UID required"}), 400

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        data = loop.run_until_complete(GetAccountInformation(uid, region))

        loop.close()

        if not data:
            return jsonify({"error": "No data returned from server"}), 500

        # SAFE ACCESS (no crash)
        basic = data.get("basicInfo", {})

        result = {
            "name": basic.get("nickname", "Unknown"),
            "uid": basic.get("accountId", uid),
            "level": basic.get("level", 0),
            "likes": basic.get("liked", 0),
            "region": region,
            "raw": data
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": "Failed",
            "details": str(e)
        }), 500
