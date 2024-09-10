from .nostr.key import PrivateKey


def parse_nostr_private_key(key: str) -> PrivateKey:
    if key.startswith("nsec"):
        return PrivateKey.from_nsec(key)
    else:
        return PrivateKey(bytes.fromhex(key))
