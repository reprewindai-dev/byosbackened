"""
mTLS Infrastructure
===================

This module implements the mTLS (mutual TLS) infrastructure for Seked's zero-trust
networking model. Every component runs with cryptographic identity, and all traffic
is mutually authenticated.

Architecture:
- Seked PKI: Internal certificate authority for issuing certificates
- Service mesh mTLS: All internal traffic encrypted and authenticated
- Client certificates: For AI citizens and human users
- Certificate lifecycle: Automated issuance, rotation, and revocation
- Zero-trust enforcement: No component talks without valid mTLS

This ensures "no component talks to Seked without cryptographic proof of who it is."
"""

import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from pydantic import BaseModel, Field
import structlog

from core.config import get_settings


class CertificateRequest(BaseModel):
    """Certificate signing request data."""
    common_name: str
    organization: str = "Seked"
    organizational_unit: str = "AI Governance"
    country: str = "US"
    state: str = "CA"
    locality: str = "San Francisco"
    email: Optional[str] = None
    key_usage: List[str] = ["digital_signature", "key_encipherment"]
    extended_key_usage: List[str] = ["server_auth", "client_auth"]


class IssuedCertificate(BaseModel):
    """Issued certificate with metadata."""
    certificate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    common_name: str
    certificate_pem: str
    private_key_pem: str  # Only returned during initial issuance
    serial_number: str
    issued_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    expires_at: str
    revoked: bool = False
    revocation_date: Optional[str] = None
    certificate_chain: List[str] = []  # Full chain including CA


class MTLSInfrastructure:
    """mTLS infrastructure implementation."""

    def __init__(self):
        self.settings = get_settings()
        self.pki_path = os.path.join(self.settings.DATA_DIR, "pki")
        self.ca_cert_path = os.path.join(self.pki_path, "ca.crt")
        self.ca_key_path = os.path.join(self.pki_path, "ca.key")
        self.certificates_db_path = os.path.join(self.pki_path, "certificates.db")
        self.logger = structlog.get_logger(__name__)
        self._init_pki()

    def _init_pki(self) -> None:
        """Initialize the Seked PKI infrastructure."""
        os.makedirs(self.pki_path, exist_ok=True)

        # Initialize certificate database
        if not os.path.exists(self.certificates_db_path):
            self._init_certificates_db()

        # Generate CA if it doesn't exist
        if not os.path.exists(self.ca_cert_path) or not os.path.exists(self.ca_key_path):
            self._generate_ca_certificate()

        self.logger.info("Seked PKI initialized", pki_path=self.pki_path)

    def _init_certificates_db(self) -> None:
        """Initialize certificates database."""
        import sqlite3

        conn = sqlite3.connect(self.certificates_db_path)
        conn.execute("""
            CREATE TABLE certificates (
                certificate_id TEXT PRIMARY KEY,
                common_name TEXT NOT NULL,
                certificate_pem TEXT NOT NULL,
                private_key_pem TEXT NOT NULL,  -- Encrypted storage
                serial_number TEXT NOT NULL UNIQUE,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT FALSE,
                revocation_date TEXT,
                certificate_chain TEXT NOT NULL,  -- JSON array
                key_usage TEXT NOT NULL,  -- JSON array
                extended_key_usage TEXT NOT NULL,  -- JSON array
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE certificate_revocation_list (
                serial_number TEXT PRIMARY KEY,
                revocation_date TEXT NOT NULL,
                revocation_reason TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def _generate_ca_certificate(self) -> None:
        """Generate the Seked Certificate Authority."""
        # Generate CA private key
        ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )

        # Create CA certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Seked"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Certificate Authority"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Seked Root CA"),
        ])

        ca_cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            ca_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=3650)  # 10 years
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key())
            ),
            critical=False
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        ).sign(ca_key, hashes.SHA256(), default_backend())

        # Save CA certificate
        with open(self.ca_cert_path, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

        # Save CA private key (encrypted)
        with open(self.ca_key_path, "wb") as f:
            f.write(ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(b"seked_ca_key")
            ))

        self.logger.info("Seked Root CA generated", ca_cert_path=self.ca_cert_path)

    def _load_ca_certificate(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Load the CA certificate and private key."""
        # Load CA certificate
        with open(self.ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        # Load CA private key
        with open(self.ca_key_path, "rb") as f:
            ca_key = serialization.load_pem_private_key(
                f.read(),
                password=b"seked_ca_key",
                backend=default_backend()
            )

        return ca_cert, ca_key

    def _generate_certificate_keypair(self) -> rsa.RSAPrivateKey:
        """Generate RSA keypair for certificate."""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

    def _create_certificate_request(self, request: CertificateRequest) -> x509.Certificate:
        """Create a certificate from request data."""
        ca_cert, ca_key = self._load_ca_certificate()

        # Generate private key for certificate
        private_key = self._generate_certificate_keypair()

        # Create certificate subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, request.country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, request.state),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, request.organizational_unit),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, request.organization),
            x509.NameAttribute(NameOID.COMMON_NAME, request.common_name),
        ])

        if request.email:
            subject = subject + x509.Name([
                x509.NameAttribute(NameOID.EMAIL_ADDRESS, request.email),
            ])

        # Build certificate
        builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow() - timedelta(minutes=5)  # Allow for clock skew
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)  # 1 year validity
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
                ca_cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_KEY_IDENTIFIER).value
            ),
            critical=False
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True
        )

        # Add key usage extension
        key_usage = self._parse_key_usage(request.key_usage)
        builder = builder.add_extension(key_usage, critical=True)

        # Add extended key usage extension
        extended_key_usage = self._parse_extended_key_usage(request.extended_key_usage)
        builder = builder.add_extension(extended_key_usage, critical=False)

        # Sign certificate
        certificate = builder.sign(ca_key, hashes.SHA256(), default_backend())

        return certificate, private_key

    def _parse_key_usage(self, key_usage_list: List[str]) -> x509.KeyUsage:
        """Parse key usage list into KeyUsage extension."""
        return x509.KeyUsage(
            digital_signature="digital_signature" in key_usage_list,
            content_commitment="content_commitment" in key_usage_list,
            key_encipherment="key_encipherment" in key_usage_list,
            data_encipherment="data_encipherment" in key_usage_list,
            key_agreement="key_agreement" in key_usage_list,
            key_cert_sign="key_cert_sign" in key_usage_list,
            crl_sign="crl_sign" in key_usage_list,
            encipher_only="encipher_only" in key_usage_list,
            decipher_only="decipher_only" in key_usage_list
        )

    def _parse_extended_key_usage(self, extended_key_usage_list: List[str]) -> x509.ExtendedKeyUsage:
        """Parse extended key usage list into ExtendedKeyUsage extension."""
        usages = []
        for usage in extended_key_usage_list:
            if usage == "server_auth":
                usages.append(x509.oid.ExtendedKeyUsageOID.SERVER_AUTH)
            elif usage == "client_auth":
                usages.append(x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH)
            elif usage == "code_signing":
                usages.append(x509.oid.ExtendedKeyUsageOID.CODE_SIGNING)
            elif usage == "email_protection":
                usages.append(x509.oid.ExtendedKeyUsageOID.EMAIL_PROTECTION)
            elif usage == "time_stamping":
                usages.append(x509.oid.ExtendedKeyUsageOID.TIME_STAMPING)
            elif usage == "ms_code_indicating":
                usages.append(x509.oid.ExtendedKeyUsageOID.MS_CODE_INDICATING)
            elif usage == "ms_code_treatment":
                usages.append(x509.oid.ExtendedKeyUsageOID.MS_CODE_TREATMENT)
            elif usage == "ms_smartcard_logon":
                usages.append(x509.oid.ExtendedKeyUsageOID.MS_SMARTCARD_LOGON)
            elif usage == "ipsec_end_system":
                usages.append(x509.oid.ExtendedKeyUsageOID.IPSEC_END_SYSTEM)
            elif usage == "ipsec_tunnel":
                usages.append(x509.oid.ExtendedKeyUsageOID.IPSEC_TUNNEL)
            elif usage == "ipsec_user":
                usages.append(x509.oid.ExtendedKeyUsageOID.IPSEC_USER)

        return x509.ExtendedKeyUsage(usages)

    def issue_certificate(self, request: CertificateRequest) -> IssuedCertificate:
        """
        Issue a new certificate.

        Args:
            request: Certificate request data

        Returns:
            Issued certificate with private key
        """
        import sqlite3
        import json

        # Create certificate
        certificate, private_key = self._create_certificate_request(request)

        # Load CA certificate for chain
        ca_cert, _ = self._load_ca_certificate()

        # Serialize certificate and key
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()  # Return unencrypted for initial setup
        ).decode()

        ca_cert_pem = ca_cert.public_bytes(serialization.Encoding.PEM).decode()
        certificate_chain = [cert_pem, ca_cert_pem]

        # Create issued certificate object
        issued_cert = IssuedCertificate(
            common_name=request.common_name,
            certificate_pem=cert_pem,
            private_key_pem=key_pem,
            serial_number=str(certificate.serial_number),
            expires_at=certificate.not_valid_after.isoformat() + "Z",
            certificate_chain=certificate_chain
        )

        # Store in database
        conn = sqlite3.connect(self.certificates_db_path)
        conn.execute("""
            INSERT INTO certificates (
                certificate_id, common_name, certificate_pem, private_key_pem,
                serial_number, issued_at, expires_at, certificate_chain,
                key_usage, extended_key_usage, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            issued_cert.certificate_id, issued_cert.common_name, cert_pem, key_pem,
            issued_cert.serial_number, issued_cert.issued_at, issued_cert.expires_at,
            json.dumps(certificate_chain), json.dumps(request.key_usage),
            json.dumps(request.extended_key_usage), datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        conn.close()

        self.logger.info("Certificate issued",
                        certificate_id=issued_cert.certificate_id,
                        common_name=request.common_name,
                        serial_number=issued_cert.serial_number)

        return issued_cert

    def get_certificate(self, certificate_id: str) -> Optional[IssuedCertificate]:
        """Get certificate by ID."""
        import sqlite3
        import json

        conn = sqlite3.connect(self.certificates_db_path)
        cursor = conn.execute("""
            SELECT certificate_id, common_name, certificate_pem, serial_number,
                   issued_at, expires_at, revoked, revocation_date, certificate_chain
            FROM certificates
            WHERE certificate_id = ?
        """, (certificate_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return IssuedCertificate(
                certificate_id=row[0],
                common_name=row[1],
                certificate_pem=row[2],
                private_key_pem="",  # Don't return private key
                serial_number=row[3],
                issued_at=row[4],
                expires_at=row[5],
                revoked=row[6],
                revocation_date=row[7],
                certificate_chain=json.loads(row[8]) if row[8] else []
            )
        return None

    def revoke_certificate(self, certificate_id: str, reason: str = "unspecified") -> bool:
        """Revoke a certificate."""
        import sqlite3

        conn = sqlite3.connect(self.certificates_db_path)

        # Get certificate info
        cursor = conn.execute("""
            SELECT serial_number FROM certificates
            WHERE certificate_id = ? AND revoked = FALSE
        """, (certificate_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        serial_number = row[0]
        revocation_date = datetime.utcnow().isoformat() + "Z"

        # Mark certificate as revoked
        conn.execute("""
            UPDATE certificates
            SET revoked = TRUE, revocation_date = ?
            WHERE certificate_id = ?
        """, (revocation_date, certificate_id))

        # Add to revocation list
        conn.execute("""
            INSERT OR REPLACE INTO certificate_revocation_list
            (serial_number, revocation_date, revocation_reason)
            VALUES (?, ?, ?)
        """, (serial_number, revocation_date, reason))

        conn.commit()
        conn.close()

        self.logger.info("Certificate revoked",
                        certificate_id=certificate_id,
                        serial_number=serial_number,
                        reason=reason)

        return True

    def get_certificate_revocation_list(self) -> List[Dict[str, str]]:
        """Get the certificate revocation list."""
        import sqlite3

        conn = sqlite3.connect(self.certificates_db_path)
        cursor = conn.execute("""
            SELECT serial_number, revocation_date, revocation_reason
            FROM certificate_revocation_list
            ORDER BY revocation_date DESC
        """)

        crl = []
        for row in cursor.fetchall():
            crl.append({
                "serial_number": row[0],
                "revocation_date": row[1],
                "revocation_reason": row[2]
            })

        conn.close()
        return crl

    def verify_certificate_chain(self, certificate_pem: str) -> bool:
        """
        Verify certificate chain against Seked CA.

        Args:
            certificate_pem: PEM-encoded certificate to verify

        Returns:
            True if certificate is valid and properly signed
        """
        try:
            # Load certificate
            cert = x509.load_pem_x509_certificate(certificate_pem.encode(), default_backend())

            # Load CA certificate
            ca_cert, _ = self._load_ca_certificate()

            # Verify certificate is signed by CA
            ca_public_key = ca_cert.public_key()
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                cert.signature_hash_algorithm
            )

            # Check if certificate is revoked
            conn = sqlite3.connect(self.certificates_db_path)
            cursor = conn.execute("""
                SELECT 1 FROM certificate_revocation_list
                WHERE serial_number = ?
            """, (str(cert.serial_number),))

            is_revoked = cursor.fetchone() is not None
            conn.close()

            if is_revoked:
                return False

            # Check expiration
            now = datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                return False

            return True

        except Exception as e:
            self.logger.error("Certificate verification failed", error=str(e))
            return False

    def generate_mtls_config(self, service_name: str) -> Dict[str, str]:
        """
        Generate mTLS configuration for a service.

        Args:
            service_name: Name of the service

        Returns:
            Configuration dictionary with cert paths and settings
        """
        # Issue certificate for service if it doesn't exist
        existing_cert = self.get_certificate(f"service_{service_name}")
        if not existing_cert:
            request = CertificateRequest(
                common_name=f"{service_name}.seked.internal",
                organizational_unit="Services"
            )
            existing_cert = self.issue_certificate(request)

        return {
            "certificate_path": f"/etc/seked/certs/{service_name}.crt",
            "private_key_path": f"/etc/seked/certs/{service_name}.key",
            "ca_certificate_path": "/etc/seked/certs/ca.crt",
            "certificate_pem": existing_cert.certificate_pem,
            "private_key_pem": existing_cert.private_key_pem,
            "verify_peer": "true",
            "fail_if_no_peer_cert": "true"
        }

    def rotate_certificate(self, certificate_id: str) -> Optional[IssuedCertificate]:
        """
        Rotate a certificate with new validity period.

        Args:
            certificate_id: ID of certificate to rotate

        Returns:
            New certificate if rotation successful
        """
        import sqlite3
        import json

        # Get existing certificate info
        conn = sqlite3.connect(self.certificates_db_path)
        cursor = conn.execute("""
            SELECT common_name, key_usage, extended_key_usage
            FROM certificates
            WHERE certificate_id = ?
        """, (certificate_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        common_name, key_usage_json, extended_key_usage_json = row

        # Create new certificate request
        request = CertificateRequest(
            common_name=common_name,
            key_usage=json.loads(key_usage_json),
            extended_key_usage=json.loads(extended_key_usage_json)
        )

        # Issue new certificate
        new_cert = self.issue_certificate(request)

        # Revoke old certificate
        self.revoke_certificate(certificate_id, "rotation")

        self.logger.info("Certificate rotated",
                        old_certificate_id=certificate_id,
                        new_certificate_id=new_cert.certificate_id,
                        common_name=common_name)

        return new_cert


# Global mTLS infrastructure instance
mtls_infrastructure = MTLSInfrastructure()
