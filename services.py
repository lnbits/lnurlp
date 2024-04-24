import re


async def check_lnaddress_format(username: str) -> bool:
    # check username complies with lnaddress specification
    if not re.match("^[a-z0-9-_.]{1,210}$", username):
        assert False, "Only letters a-z0-9-_. allowed, min 1 and max 210 characters!"
        return
    return True
