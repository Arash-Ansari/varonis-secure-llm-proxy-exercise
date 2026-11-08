"""Create a local CA and a localhost server certificate for the NGINX demo."""
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CERTS = Path(__file__).resolve().parent.parent / "certs"
CA_KEY = CERTS / "local-ca.key"
CA_CERT = CERTS / "local-ca.crt"
SERVER_KEY = CERTS / "localhost.key"
SERVER_CERT = CERTS / "localhost.crt"
MITMPROXY_KEY = CERTS / "mitmproxy.key"
MITMPROXY_CERT = CERTS / "mitmproxy.crt"
MITMPROXY_PEM = CERTS / "mitmproxy.pem"


def write_private_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))


def write_certificate(path: Path, certificate: x509.Certificate) -> None:
    path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))


def issue_server_certificate(
    common_name: str,
    names: list[x509.GeneralName],
    ca_key: rsa.RSAPrivateKey,
    ca_cert: x509.Certificate,
    now: datetime,
) -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    """Create a server certificate signed by this demo's local CA."""
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .issuer_name(ca_cert.subject).public_key(server_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False
        )
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=True,
            data_encipherment=False, key_agreement=False, key_cert_sign=False,
            crl_sign=False, encipher_only=False, decipher_only=False,
        ), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName(names), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return server_key, server_cert


def main() -> None:
    files = (
        CA_KEY, CA_CERT, SERVER_KEY, SERVER_CERT,
        MITMPROXY_KEY, MITMPROXY_CERT, MITMPROXY_PEM,
    )
    if any(path.exists() for path in files):
        raise SystemExit("Certificates already exist. Refusing to overwrite them.")

    CERTS.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Secure LLM Proxy Local CA")])
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    ca_cert = (
        x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False
        )
        .add_extension(x509.KeyUsage(
            digital_signature=False, content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=True,
            crl_sign=True, encipher_only=False, decipher_only=False,
        ), critical=True).sign(ca_key, hashes.SHA256())
    )

    server_key, server_cert = issue_server_certificate(
        "localhost",
        [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))],
        ca_key, ca_cert, now,
    )
    mitmproxy_key, mitmproxy_cert = issue_server_certificate(
        "mitmproxy", [x509.DNSName("mitmproxy")], ca_key, ca_cert, now,
    )

    write_private_key(CA_KEY, ca_key)
    write_certificate(CA_CERT, ca_cert)
    write_private_key(SERVER_KEY, server_key)
    write_certificate(SERVER_CERT, server_cert)
    write_private_key(MITMPROXY_KEY, mitmproxy_key)
    write_certificate(MITMPROXY_CERT, mitmproxy_cert)
    MITMPROXY_PEM.write_bytes(MITMPROXY_KEY.read_bytes() + MITMPROXY_CERT.read_bytes())
    print("Created a local CA plus certificates for localhost and mitmproxy in certs/.")
    print("Keep certs/local-ca.key private; it is ignored by Git.")


if __name__ == "__main__":
    main()
