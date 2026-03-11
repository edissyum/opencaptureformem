import os
import json
import time
import subprocess
from urllib.parse import urlparse
from datetime import datetime, timezone

import requests
from OpenSSL import crypto


def sign_csr(config, url_endpoint):
    try:
        parsed = urlparse(url_endpoint)
        url = f"{parsed.scheme}://{parsed.netloc}/mtls/sign-csr"
        username = config["sender_remote_login"]
        password = config["sender_remote_password"]
        cert_path = config["cert_path"]
        
        client_cert = os.path.join(cert_path, "client.crt")
        client_key = os.path.join(cert_path, "client.key")
        ca_cert = os.path.join(cert_path, "ca.crt")

        if not all(os.path.isfile(p) for p in (client_cert, client_key, ca_cert)):
            return False, "La clé de chiffrement est absente."

        with open(client_cert, "rb") as f:
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())

        expires_at = int(
            datetime.strptime(
                cert.get_notAfter().decode("ascii"),
                "%Y%m%d%H%M%SZ",
            ).replace(tzinfo=timezone.utc).timestamp()
        )

        remaining_seconds = expires_at - int(time.time())
        remaining_days = remaining_seconds // 86400
        renew_threshold = 10 * 24 * 60 * 60 # 10 jours

        if remaining_seconds >= renew_threshold:
            return True, "Le certificat client est toujours valide."

        tmp_key = os.path.join(cert_path, "client.key.tmp")
        tmp_csr = os.path.join(cert_path, "client.csr.tmp")
        tmp_crt = os.path.join(cert_path, "client.crt.tmp")

        for path in (tmp_key, tmp_csr, tmp_crt):
            if os.path.exists(path):
                os.unlink(path)

        subprocess.run(
            [
                "openssl",
                "req",
                "-newkey", "rsa:4096",
                "-nodes",
                "-keyout", tmp_key,
                "-out", tmp_csr,
                "-subj", "/CN=client",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        with open(tmp_csr, "r", encoding="utf-8") as f:
            payload = json.dumps({"csr_pem": f.read()})

        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            data=payload,
            timeout=30,
            auth=(username, password),
            cert=(client_cert, client_key),
            verify=ca_cert,
        )
        response.raise_for_status()

        client_crt = response.json()["client_crt"]

        with open(tmp_crt, "w", encoding="utf-8") as f:
            f.write(client_crt)

        os.replace(tmp_key, client_key)
        os.replace(tmp_crt, client_cert)

        if os.path.exists(tmp_csr):
            os.unlink(tmp_csr)

        os.chmod(client_key, 0o600)
        os.chmod(client_cert, 0o644)

        return True, "Le certificat client a été renouvelé"

    except Exception as e:
        return False, str(e)
