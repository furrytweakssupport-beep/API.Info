from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection

class LoginReq(_message.Message):
    __slots__ = ["open_id", "open_id_type", "login_token", "orign_platform_type"]

class BlacklistInfoRes(_message.Message):
    __slots__ = ["ban_reason", "expire_duration", "ban_time"]

class LoginQueueInfo(_message.Message):
    __slots__ = ["allow", "queue_position", "need_wait_secs", "queue_is_full"]

class LoginRes(_message.Message):
    __slots__ = [
        "account_id","lock_region","noti_region","ip_region",
        "agora_environment","new_active_region","recommend_regions",
        "token","ttl","server_url","emulator_score",
        "blacklist","queue_info","tp_url","app_server_id",
        "ano_url","ip_city","ip_subdivision"
    ]