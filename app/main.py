from flask import Flask, request, jsonify
import asyncio
from app.services.player import get_player
from app.utils.formatter import format_response

app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "API Running"}

@app.route("/player")
def player():
    uid = request.args.get("uid")
    region = request.args.get("region")

    if not uid or not region:
        return jsonify({"error": "uid & region required"}), 400

    data = asyncio.run(get_player(uid, region.upper()))
    return jsonify(format_response(data))