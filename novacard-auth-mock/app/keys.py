from jose import jwk
from jose.constants import Algorithms
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import uuid

def generate_rsa_keypair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    kid = str(uuid.uuid4())

    jwk_public = jwk.construct(public_pem, Algorithms.RS256)
    jwk_public_dict = jwk_public.to_dict()
    jwk_public_dict["kid"] = kid
    jwk_public_dict["use"] = "sig"

    return {
        "kid": kid,
        "private_pem": private_pem,
        "public_jwk": jwk_public_dict
    }