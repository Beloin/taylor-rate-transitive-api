from __future__ import annotations

import datetime
import ipaddress
import os
import ssl
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.config import get_settings

CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"


def cert_paths() -> tuple[Path, Path]:
    cert_dir = Path(get_settings().cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)
    return cert_dir / CERT_FILE, cert_dir / KEY_FILE


def generate_self_signed_cert(force: bool = False) -> tuple[Path, Path]:
    """Generate a self-signed certificate and private key if missing."""
    cert_path, key_path = cert_paths()
    if not force and cert_path.exists() and key_path.exists():
        return cert_path, key_path

    settings = get_settings()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    cn = settings.cert_cn
    san_entries = [x509.DNSName(cn)]
    try:
        san_entries.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))
    except ValueError:
        pass

    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Taylor Music Rating"),
        ]
    )

    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .sign(key, hashes.SHA256())
    )

    cert_path.write_bytes(
        cert.public_bytes(serialization.Encoding.PEM)
    )
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    os.chmod(key_path, 0o600)
    return cert_path, key_path


def ssl_context() -> ssl.SSLContext | None:
    """Build an SSL context for the HTTPS server, or None if cert missing."""
    cert_path, key_path = cert_paths()
    if not cert_path.exists() or not key_path.exists():
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    return ctx