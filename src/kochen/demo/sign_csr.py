#!/usr/bin/env python3
"""Interface with 'guardian' Vault via REST API.

Mainly for signing an existing CSR with the Vault's intermediate certificate.
Aligns with guardian specs.

Changelog:
    2024-05-02, Justin: Init

References:
    [1]:
"""

import pathlib
import re
import sys

import cryptography.hazmat.primitives.asymmetric.ec as ec
import cryptography.hazmat.primitives.serialization as serialization
import requests
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes

import kochen.scriptutil
import kochen.logging

logger = kochen.logging.get_logger(__name__)

def generate_key(password=None):
    """Generates an EC key using NIST P-384.

    To return the public key as well, use:

        pubkey = key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    """
    key = ec.generate_private_key(curve=ec.SECP384R1)
    encryption = serialization.NoEncryption()
    if password is not None:
        encryption = serialization.BestAvailableEncryption(
            password.encode()
        )
    privkey = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        encryption,
    )
    return key, privkey.decode()

def load_key(keypath):
    # No key found at path, generate a new one
    if not pathlib.Path(keypath).exists():
        print("Generating EC key...")
        password = prompt_password()
        key, privkey = generate_key(password)
        with open(keypath, "w") as f:
            f.write(privkey)

    # Key found at path, read it
    else:
        print("Loading private EC key...")
        with open(keypath, "r") as f:
            privkey = f.read()
        # Try to load, assuming no encryption
        try:
            key = serialization.load_pem_private_key(
                privkey.encode(),
                password=None,
            )
        except TypeError:
            password = None
            while (password := prompt_password()) is None:
                pass
            try:
                key = serialization.load_pem_private_key(
                    privkey.encode(),
                    password=password.encode(),
                )
            except ValueError:
                logger.error("Decryption failed - bad password?")
                sys.exit(1)
    return key

def load_csr(csrpath, key=None):
    if not pathlib.Path(csrpath).exists() and key is not None:
        csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            # Provide various details about who we are.
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Company"),
            x509.NameAttribute(NameOID.COMMON_NAME, "mysite.com"),
        ])).add_extension(
            x509.SubjectAlternativeName([
                # Describe what sites we want this certificate for.
                x509.DNSName("mysite.com"),
                x509.DNSName("www.mysite.com"),
                x509.DNSName("subdomain.mysite.com"),
            ]),
            critical=False,
        # Sign the CSR with our private key.
        ).sign(key, hashes.SHA256())
        # Write our CSR out to disk.
        with open("path/to/csr.pem", "wb") as f:
            f.write(csr.public_bytes(serialization.Encoding.PEM))
        plaintext = csr.public_bytes(serialization.Encoding.PEM).decode().strip()
        return plaintext

    else:
        with open(csrpath, "rb") as f:
            data = f.read()
        csr = x509.load_pem_x509_csr(data)
        return data

def prompt_password(prompt="Password (4-64 chars): "):
    password = sanitize_string(input(prompt))
    if not (4 <= len(password) <= 64):
        if len(password) == 0:
            logger.warning("No password provided - assuming no encryption.")
        elif len(password) < 4:
            logger.warning("Provided password too short (<4 chars) - assuming no encryption.")
        else:
            logger.warning("Provided password too long (>64 chars) - assuming no encryption.")
        password = None

    return password

def sanitize_string(s):
    """Sanitization of user input string.

    References:
        [1]: <https://stackoverflow.com/a/56820149>
    """
    s = s.replace("\t", "    ")
    return re.sub(r"[^ -~]", "", s).strip()


def main():
    parser = kochen.scriptutil.generate_default_parser(__doc__)

    # Boilerplate
    pgroup_config = parser.add_argument_group("display/configuration")
    pgroup_config.add_argument(
        "-h", "--help", action="store_true",
        help="Show this help message and exit")
    pgroup_config.add_argument(
        "-v", "--verbosity", action="count", default=0,
        help="Specify debug verbosity, e.g. -vv for more verbosity")
    pgroup_config.add_argument(
        "-L", "--logging", metavar="",
        help="Log to file, if specified. Log level follows verbosity.")
    pgroup_config.add_argument(
        "--quiet", action="store_true",
        help="Suppress errors, but will not block logging")
    pgroup_config.add_argument(
        "--config", metavar="", is_config_file_arg=True,
        help="Path to configuration file")
    pgroup_config.add_argument(
        "--save", metavar="", is_write_out_config_file_arg=True,
        help="Path to configuration file for saving, then immediately exit")

    pgroup_signing = parser.add_argument_group("signing")
    pgroup_signing.add_argument(
        "--domain",
        help="Domain and port number of vault server on KME")
    pgroup_signing.add_argument(
        "--endpoint", default="/v1/pki_int/sign/role_int_ca_cert_issuer",
        help="Signing endpoint")
    pgroup_signing.add_argument(
        "--csr",
        help="Path to CSR to be signed")
    pgroup_signing.add_argument(
        "--sae",
        help="Name of SAE to be assigned to certificate")

    pgroup_auth = parser.add_argument_group("authentication")
    pgroup_auth.add_argument(
        "--token",
        help="Access token for vault server (recommended to pass via config file)")
    pgroup_auth.add_argument(
        "--client-cert",
        help="Path to client certificate for vault server")
    pgroup_auth.add_argument(
        "--client-key",
        help="Path to client key for corresponding certificate")
    pgroup_auth.add_argument(
        "--server-cert",
        help="Path to server certificate chain for vault server")

    # Parse arguments and configure logging
    args = kochen.scriptutil.parse_args_or_help(parser)
    kochen.logging.set_logging_level(logger, args.verbosity)
    logger.debug("%s", args)

    # Assert existence of supplied files
    assert args.csr is not None, "CSR must be provided"
    assert args.client_cert is not None, "Client cert must be provided"
    assert args.client_key is not None, "Client key must be provided"
    assert args.server_cert is not None, "Server CA chain must be provided"
    kochen.scriptutil.guarantee_path(args.csr)
    kochen.scriptutil.guarantee_path(args.client_cert)
    kochen.scriptutil.guarantee_path(args.client_key)
    kochen.scriptutil.guarantee_path(args.server_cert)
    assert args.sae is not None, "SAE name must be provided"
    assert args.token is not None, "Access token must be provided"
    assert args.domain is not None, "Vault domain:port must be provided"
    assert args.endpoint is not None, "Vault signing endpoint must be provided"

    # Prepare for signing
    csr = load_csr(args.csr)
    sae = sanitize_string(args.sae)
    token = sanitize_string(args.token)
    domain = sanitize_string(args.domain)
    endpoint = f"https://{domain}{args.endpoint}"
    body = {
        "common_name": f"{sae}",
        "uri_sans": f"sae-id:{sae}",
        "key_type": "ec",
        "csr": csr,
    }
    headers = {
       "X-Vault-Token": token,
       "X-Vault-Request": "true",
    }
    cert = (args.client_cert, args.client_key)
    chain = args.server_cert

    # Perform signing
    r = requests.post(endpoint, headers=headers, data=body, cert=cert, verify=chain)
    if r.status_code != 200:
        print(r.json())
        sys.exit(1)

    # Read and store certificates to disk
    json_response = r.json()["data"]
    with open(f"{sae}.cert", "w") as f:
        f.write(json_response["certificate"])
    with open(f"{sae}.ca-chain.cert", "w") as f:
        f.write("\n".join(json_response["ca_chain"]))


if __name__ == "__main__":
    main()
