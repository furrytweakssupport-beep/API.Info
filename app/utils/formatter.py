def format_response(data):
    basic = data.get("basicInfo", {})
    pet = data.get("petInfo", {})
    clan = data.get("clanBasicInfo", {})

    return {
        "name": basic.get("nickname"),
        "uid": basic.get("accountId"),
        "level": basic.get("level"),
        "likes": basic.get("liked"),
        "region": basic.get("region"),

        "pet": {
            "name": pet.get("name"),
            "level": pet.get("level")
        },

        "guild": {
            "name": clan.get("clanName"),
            "members": clan.get("memberNum")
        }
    }