import ipaddress
from typing import Tuple
from urllib.parse import urlparse

from .nostr.key import PrivateKey


def parse_nostr_private_key(key: str) -> PrivateKey:
    if key.startswith("nsec"):
        return PrivateKey.from_nsec(key)
    else:
        return PrivateKey(bytes.fromhex(key))


def is_localhost_or_internal_url(url: str) -> Tuple[bool, str]:
    """
    Check if a URL is localhost, internal IP, or non-HTTPS.
    Returns (is_unsafe, warning_message)
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        scheme = parsed.scheme.lower()
        
        # Tor onion addresses are allowed with HTTP
        if host.endswith(".onion"):
            return False, ""
        
        # Check if it's not HTTPS
        if scheme != "https":
            # Check for localhost variations
            if host in ["localhost", "127.0.0.1", "::1"]:
                return True, "Localhost addresses are only accessible from the same machine and may not work with all wallets"
            
            # Check for internal/private IP addresses
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private:
                    return True, f"Internal IP address {host} is only accessible within your local network and may not work with external wallets"
            except ValueError:
                # Not an IP address, could be a domain
                pass
            
            # Check for .local domains (common in internal networks)
            if host.endswith(".local"):
                return True, f"{host} appears to be a local network address and may not work with external wallets"
            
            # General HTTP warning
            return True, "HTTP addresses are not secure and may not work with most wallets. HTTPS or Tor onion addresses are recommended"
            
        return False, ""
    except Exception:
        return False, ""
