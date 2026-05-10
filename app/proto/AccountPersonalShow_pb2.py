from google.protobuf import message as _message

class BasicInfo(_message.Message):
    __slots__ = [
        "accountId","nickname","level","exp",
        "liked","createAt","lastLoginAt","region"
    ]

class ProfileInfo(_message.Message):
    __slots__ = ["signature"]

class PetInfo(_message.Message):
    __slots__ = ["name","level","exp"]

class ClanBasicInfo(_message.Message):
    __slots__ = ["clanName","clanId","clanLevel","memberNum","capacity"]

class AccountPersonalShowInfo(_message.Message):
    __slots__ = ["basicInfo","profileInfo","petInfo","clanBasicInfo"]