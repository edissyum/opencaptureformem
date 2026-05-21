import os
import json
import time
from urllib.parse import urlparse

import requests

CONNECT_TIMEOUT = 5
REQUEST_TIMEOUT = 60
JWT_CACHE_FILE = "serenia_jwt_cache.json"
JWT_EXPIRY_SAFETY_MARGIN = 30


# =========================
# Config helpers
# =========================

def get_config_value(config, key):
    try:
        return config.get(key)
    except Exception:
        return None


def get_base_url_or_fail(config, ai_type):
    base_url = get_config_value(config, f"{ai_type}_remote_url")

    if not base_url or not isinstance(base_url, str):
        raise RuntimeError(f"{ai_type}_remote_url missing or invalid")

    base_url = base_url.strip()
    parsed = urlparse(base_url)

    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(f"{ai_type}_remote_url missing or invalid")

    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def get_remote_login_or_fail(config, ai_type):
    username = get_config_value(config, ai_type + "_remote_login")

    if not username or not isinstance(username, str) or not username.strip():
        raise RuntimeError(f"{ai_type}_remote_login missing or invalid")

    return username.strip()


def get_remote_client_secret_or_fail(config, ai_type):
    value = get_config_value(config, ai_type + "_remote_password")

    if isinstance(value, str) and value.strip():
        client_secret = value.strip()

        if len(client_secret) < 16:
            raise RuntimeError(f"{key} invalid: minimum length is 16")

        return client_secret

    raise RuntimeError(
        f"{ai_type}_remote_password missing or invalid"
    )


def get_secrets_path(config, ai_type):
    cert_path = get_config_value(config, ai_type + "_cert_path")

    if not cert_path or not isinstance(cert_path, str):
        raise RuntimeError(f"{ai_type}_cert_path missing or invalid")

    cert_path = cert_path.strip()

    if not cert_path:
        raise RuntimeError(f"{ai_type}_cert_path missing or invalid")

    if not cert_path.endswith(os.sep):
        cert_path += os.sep

    return cert_path


def get_ca_crt_path(config, ai_type):
    return os.path.join(get_secrets_path(config, ai_type), "ca.crt")


def get_jwt_cache_path(config, ai_type):
    return os.path.join(get_secrets_path(config, ai_type), JWT_CACHE_FILE)


def get_tls_verify_value(config, ai_type):
    tls_verify = get_config_value(config, ai_type + "_tls_verify")

    if isinstance(tls_verify, str) and tls_verify.strip().lower() in ("0", "false", "no", "off"):
        return False

    try:
        ca_crt_path = get_ca_crt_path(config, ai_type)
    except RuntimeError:
        return True

    if os.path.isfile(ca_crt_path) and os.access(ca_crt_path, os.R_OK):
        return ca_crt_path

    return True


# =========================
# Runtime checks
# =========================

def get_runtime_files_state(config, ai_type):
    try:
        get_base_url_or_fail(config, ai_type)
        get_remote_login_or_fail(config, ai_type)
        get_remote_client_secret_or_fail(config, ai_type)
    except Exception as exc:
        return False, str(exc)

    try:
        ca_crt_path = get_ca_crt_path(config, ai_type)
    except Exception:
        return True, "configuration JWT disponible, ca.crt non configuré"

    if os.path.isfile(ca_crt_path) and os.access(ca_crt_path, os.R_OK):
        return True, "configuration JWT disponible, ca.crt disponible"

    return True, "configuration JWT disponible, ca.crt absent: utilisation du magasin CA système"


# =========================
# URL helpers
# =========================

def build_url(base_url, path):
    return base_url.rstrip("/") + "/" + path.lstrip("/")


# =========================
# JWT cache
# =========================

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
    if not isinstance(cached, dict):
        return False

    token = cached.get("access_token")
    expires_at = cached.get("expires_at")

    if not isinstance(token, str) or not token.strip():
        return False

    if not isinstance(expires_at, int):
        return False

    return (expires_at - JWT_EXPIRY_SAFETY_MARGIN) > int(time.time())


# =========================
# JWT request
# =========================

def request_new_jwt_token(config, ai_type):
    base_url = get_base_url_or_fail(config, ai_type)
    username = get_remote_login_or_fail(config, ai_type)
    client_secret = get_remote_client_secret_or_fail(config, ai_type)

    url = build_url(base_url, "/auth/token")

    payload = {
        "username": username,
        "client_secret": client_secret,
    }

    response = requests.post(
        url,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=(CONNECT_TIMEOUT, REQUEST_TIMEOUT),
        verify=get_tls_verify_value(config, ai_type),
    )

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(
            f"JWT token request failed: HTTP {response.status_code}"
            + (f" - {response.text}" if response.text else "")
        )

    try:
        data = response.json()
    except Exception as exc:
        raise RuntimeError("JWT token response is not valid JSON") from exc

    access_token = data.get("access_token")
    token_type = data.get("token_type", "bearer")
    expires_in = data.get("expires_in")

    if not isinstance(access_token, str) or not access_token.strip():
        raise RuntimeError("JWT token response missing access_token")

    if not isinstance(token_type, str) or token_type.lower() != "bearer":
        raise RuntimeError("JWT token response invalid token_type")

    if not isinstance(expires_in, int):
        raise RuntimeError("JWT token response missing expires_in")

    now = int(time.time())

    token_data = {
        "access_token": access_token.strip(),
        "token_type": token_type.lower(),
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


# =========================
# Headers for protected endpoints
# =========================

def build_jwt_headers(config, ai_type, content_type=None, force_refresh=False):
    jwt_token = get_valid_jwt_token(
        config,
        ai_type,
        force_refresh=force_refresh,
    )

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }

    if content_type:
        headers["Content-Type"] = content_type

    return headers
