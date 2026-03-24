# encoding: utf-8
import os
import ssl
import subprocess
import tempfile


def build_ssl_context(settings, get_password_fn):
    """Return a configured ssl.SSLContext for mTLS, or None to use the default.

    Reads two optional settings keys:
      client_p12_path  - path to a password-protected PKCS12 (.p12) identity file
      ca_bundle_path   - path to a custom CA certificate bundle (PEM)

    The PKCS12 passphrase is retrieved from the macOS Keychain under the key
    'gitea_p12_passphrase' via get_password_fn (wf.get_password).

    When a .p12 is configured the cert and key are extracted to a private temp
    directory (mode 0700) using /usr/bin/openssl, loaded into the ssl context,
    and the temp files are deleted immediately — the private key is never left
    as a plaintext file on disk.
    """
    p12_path = settings.get('client_p12_path')
    ca_path = settings.get('ca_bundle_path')

    if not (p12_path or ca_path):
        return None

    ctx = ssl.create_default_context()

    if ca_path:
        ctx.load_verify_locations(cafile=ca_path)

    if p12_path:
        passphrase = get_password_fn('gitea_p12_passphrase')
        passphrase_bytes = (passphrase + '\n').encode('utf-8')
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_tmp = os.path.join(tmpdir, 'cert.pem')
            key_tmp = os.path.join(tmpdir, 'key.pem')
            subprocess.run(
                ['/usr/bin/openssl', 'pkcs12',
                 '-in', p12_path,
                 '-passin', 'stdin',
                 '-nokeys', '-out', cert_tmp],
                input=passphrase_bytes,
                check=True, capture_output=True)
            subprocess.run(
                ['/usr/bin/openssl', 'pkcs12',
                 '-in', p12_path,
                 '-passin', 'stdin',
                 '-nocerts', '-nodes', '-out', key_tmp],
                input=passphrase_bytes,
                check=True, capture_output=True)
            ctx.load_cert_chain(cert_tmp, key_tmp)

    return ctx
