import os
import json
import time
import base64
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives.serialization import load_pem_private_key

CONNECT_TIMEOUT = 5
REQUEST_TIMEOUT = 60
JWT_CACHE_FILE = "serenia_jwt_cache.json"
JWT_EXPIRY_SAFETY_MARGIN = 30


def get_base_url_or_fail(config):
    base_url = config.get("sender_remote_url")
    if not base_url or not isinstance(base_url, str):
        raise RuntimeError("sender_remote_url missing or invalid")
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError("sender_remote_url missing or invalid")
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def get_secrets_path(config, ai_type):
    cert_path = config.get(ai_type+"_cert_path")
    if not cert_path or not isinstance(cert_path, str):
        raise RuntimeError("cert_path missing or invalid")
    if not cert_path.endswith(os.sep):
        cert_path += os.sep
    return cert_path


def get_client_private_pem_path(config, ai_type):
    return os.path.join(get_secrets_path(config, ai_type), "client_private.pem")


def get_ca_crt_path(config, ai_type):
    return os.path.join(get_secrets_path(config, ai_type), "ca.crt")


def get_jwt_cache_path(config, ai_type):
    return os.path.join(get_secrets_path(config, ai_type), JWT_CACHE_FILE)


def get_runtime_files_state(config, ai_type):
    private_key_path = get_client_private_pem_path(config, ai_type)
    ca_crt_path = get_ca_crt_path(config, ai_type)

    if not os.path.isfile(private_key_path) or not os.access(private_key_path, os.R_OK):
        return False, "client_private.pem introuvable ou illisible"

    if not os.path.isfile(ca_crt_path) or not os.access(ca_crt_path, os.R_OK):
        return False, "ca.crt introuvable ou illisible"

    return True, "client_private.pem et ca.crt disponibles"


def build_url(base_url, path):
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def read_jwt_cache(config, ai_type):
    path = get_jwt_cache_path(config, ai_type)
    if not os.path.isfile(path) or not os.access(path, os.R_OK):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return None
        decoded = json.loads(content)
        return decoded if isinstance(decoded, dict) else None
    except Exception:
        return None


def write_jwt_cache(config, token_data, ai_type):
    path = get_jwt_cache_path(config, ai_type)
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o700, exist_ok=True)

    tmp_path = f"{path}.tmp.{os.urandom(4).hex()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)
    os.chmod(path, 0o600)


def clear_jwt_cache(config, ai_type):
    path = get_jwt_cache_path(config, ai_type)
    if os.path.isfile(path):
        try:
            os.unlink(path)
        except OSError:
            pass


def is_jwt_cache_valid(cached):
    token = cached.get("access_token")
    expires_at = cached.get("expires_at")

    if not isinstance(token, str) or not token.strip():
        return False

    if not isinstance(expires_at, int):
        return False

    return (expires_at - JWT_EXPIRY_SAFETY_MARGIN) > int(time.time())


def load_ed25519_private_key_from_pem(pem_path):
    if not os.path.isfile(pem_path) or not os.access(pem_path, os.R_OK):
        raise RuntimeError("client_private.pem introuvable ou illisible")

    with open(pem_path, "rb") as f:
        pem_data = f.read()

    private_key = load_pem_private_key(pem_data, password=None)

    # La clé doit être une Ed25519
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if not isinstance(private_key, Ed25519PrivateKey):
        raise RuntimeError("client_private.pem n'est pas une clé privée Ed25519")

    return private_key


def build_auth_message_to_sign(raw_body, timestamp, nonce):
    return f"{timestamp}\n{nonce}\n{raw_body}".encode("utf-8")


def build_auth_token_signed_headers(config, ai_type, raw_body):
    timestamp = str(int(time.time()))
    nonce = os.urandom(16).hex()

    private_key = load_ed25519_private_key_from_pem(get_client_private_pem_path(config, ai_type))
    message = build_auth_message_to_sign(raw_body, timestamp, nonce)
    signature_raw = private_key.sign(message)
    signature_b64 = base64.b64encode(signature_raw).decode("ascii")

    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature_b64,
    }


def request_new_jwt_token(config, ai_type):
    base_url = get_base_url_or_fail(config)
    username = config.get(ai_type+"_remote_login")
    if not username or not isinstance(username, str) or not username.strip():
        raise RuntimeError("remote_login missing or invalid")

    url = build_url(base_url, "/auth/token")
    payload = {"username": username}
    raw_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    headers = build_auth_token_signed_headers(config, ai_type, raw_body)
    ca_cert = get_ca_crt_path(config, ai_type)

    response = requests.post(
        url,
        headers=headers,
        data=raw_body.encode("utf-8"),
        timeout=(CONNECT_TIMEOUT, REQUEST_TIMEOUT),
        verify=ca_cert,
    )

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(
            f"JWT token request failed: HTTP {response.status_code}"
            + (f" - {response.text}" if response.text else "")
        )

    try:
        data = response.json()
    except Exception:
        raise RuntimeError("JWT token response is not valid JSON")

    access_token = data.get("access_token")
    expires_in = data.get("expires_in")

    if not isinstance(access_token, str) or not access_token.strip():
        raise RuntimeError("JWT token response missing access_token")

    if not isinstance(expires_in, int):
        raise RuntimeError("JWT token response missing expires_in")

    now = int(time.time())
    token_data = {
        "access_token": access_token,
        "expires_at": now + expires_in,
        "created_at": now,
    }

    write_jwt_cache(config, token_data, ai_type)
    return token_data


def get_valid_jwt_token(config, ai_type, force_refresh=False):
    if not force_refresh:
        cached = read_jwt_cache(config, ai_type)
        if cached and is_jwt_cache_valid(cached):
            return cached["access_token"]

    token_data = request_new_jwt_token(config, ai_type)
    return token_data["access_token"]


def build_jwt_headers(config, ai_type, content_type=None, force_refresh=False):
    jwt_token = get_valid_jwt_token(config, ai_type, force_refresh=force_refresh)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers
