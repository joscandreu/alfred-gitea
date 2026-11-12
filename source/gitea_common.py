# encoding: utf-8
"""Shared helpers: settings, URL validation, TLS (client certificates) and Keychain."""
import os
import ssl
import stat
import subprocess
import urllib.parse

# Keychain account names (service is the workflow's bundle ID)
API_KEY_ACCOUNT = 'gitea_api_key'
CERT_PASS_ACCOUNT = 'gitea_client_key_passphrase'
ALL_ACCOUNTS = (API_KEY_ACCOUNT, CERT_PASS_ACCOUNT)

# Both the script filter and the background updater must use the same
# serializer, otherwise they read/write different cache files.
CACHE_SERIALIZER = 'json'
CACHE_KEY = 'projects_gitea'
ERROR_CACHE_KEY = 'projects_gitea_error'
CACHE_MAX_AGE = 3600  # seconds

API_SEARCH_PATH = '/api/v1/repos/search'


class ConfigError(Exception):
    """Raised for invalid user configuration (shown to the user)."""


# ---------------------------------------------------------------------------
# URL handling
# ---------------------------------------------------------------------------

def normalize_base_url(url):
    """Validate a Gitea base URL and return it without trailing slash.

    Only ``https`` is accepted: the access token (and client certificate
    handshake) must never go over a plaintext connection.
    """
    if not url:
        raise ConfigError('No URL given')
    url = url.strip()
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != 'https':
        raise ConfigError('URL must start with https://')
    if not parsed.hostname:
        raise ConfigError('URL has no host name')
    if parsed.username or parsed.password:
        raise ConfigError('URL must not contain credentials')
    if parsed.query or parsed.fragment:
        raise ConfigError('URL must not contain a query string or fragment')
    path = parsed.path.rstrip('/')
    # Accept URLs pasted with the API path (as older docs suggested)
    if path.endswith(API_SEARCH_PATH):
        path = path[:-len(API_SEARCH_PATH)]
    return urllib.parse.urlunsplit(('https', parsed.netloc, path, '', ''))


def get_base_url(wf):
    """Return the configured, validated base URL or ``None``."""
    url = wf.settings.get('base_url')
    if not url:
        return None
    try:
        return normalize_base_url(url)
    except ConfigError:
        return None


def is_url_on_instance(url, base_url):
    """True if ``url`` points to the configured Gitea instance.

    Used to make sure we only hand URLs to the browser that belong to the
    configured server (no ``javascript:``, ``file:`` or foreign hosts).
    """
    if not isinstance(url, str):
        return False
    return url == base_url or url.startswith(base_url + '/')


# ---------------------------------------------------------------------------
# TLS
# ---------------------------------------------------------------------------

def _env_path(name):
    value = os.getenv(name, '').strip()
    if not value:
        return None
    path = os.path.abspath(os.path.expanduser(value))
    if not os.path.isfile(path):
        raise ConfigError('{} not found: {}'.format(name, path))
    return path


def build_ssl_context(wf, log=None):
    """Build the TLS context used for all API calls.

    Configured through Alfred workflow variables:

    - ``client_cert``: PEM file with the client certificate (may also contain
      the private key and intermediate certificates)
    - ``client_key``: PEM file with the private key, if not in ``client_cert``
    - ``ca_bundle``: PEM file with extra CA certificate(s) to trust, e.g. a
      company-internal CA (added to the system defaults)

    The passphrase of an encrypted private key is read from the Keychain
    (set with ``tea set certpass``).
    """
    ctx = ssl.create_default_context()  # verifies certificates and host name
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2

    ca_bundle = _env_path('ca_bundle')
    if ca_bundle:
        try:
            ctx.load_verify_locations(cafile=ca_bundle)
        except ssl.SSLError as e:
            raise ConfigError('Cannot load ca_bundle: {}'.format(e))

    cert = _env_path('client_cert')
    key = _env_path('client_key')
    if key and not cert:
        raise ConfigError('client_key is set but client_cert is not')
    if cert:
        if log:
            _warn_if_key_readable_by_others(key or cert, log)
        passphrase = get_secret(wf, CERT_PASS_ACCOUNT) or ''
        try:
            # A callable prevents OpenSSL from prompting on a (missing) TTY
            ctx.load_cert_chain(cert, key, password=lambda: passphrase)
        except ssl.SSLError as e:
            raise ConfigError(
                'Cannot load client certificate/key ({}). If the key is '
                'encrypted, set its passphrase with `tea set certpass`.'.format(e.reason or e))
    return ctx


def _warn_if_key_readable_by_others(path, log):
    mode = os.stat(path).st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        log.warning('Private key %s is accessible by other users; '
                    'consider `chmod 600 %s`', path, path)


def api_headers(token):
    headers = {'Accept': 'application/json'}
    if token:
        # Send the token in a header, not as ?token=... in the URL, so it
        # does not end up in server/proxy access logs.
        headers['Authorization'] = 'token ' + token
    return headers


# ---------------------------------------------------------------------------
# Keychain
# ---------------------------------------------------------------------------

def get_secret(wf, account):
    """Return a secret from the Keychain or ``None``."""
    from workflow import PasswordNotFound
    try:
        return wf.get_password(account)
    except PasswordNotFound:
        return None


def save_secret(wf, account, secret):
    """Save a secret to the Keychain without exposing it on a command line.

    ``Workflow.save_password`` passes the secret as an argument to
    ``security``, which makes it visible to other processes via ``ps``.
    Here the command is fed to ``security -i`` via stdin, hex-encoded.
    """
    cmd = 'add-generic-password -U -s {} -a {} -X {}\n'.format(
        _quote(wf.bundleid), _quote(account), secret.encode('utf-8').hex())
    p = subprocess.run(['security', '-i'], input=cmd.encode('utf-8'),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError('Could not save secret to Keychain (security exit {})'.format(p.returncode))


def delete_secret(wf, account):
    from workflow import PasswordNotFound
    try:
        wf.delete_password(account)
    except PasswordNotFound:
        pass


def _quote(value):
    # Values are the bundle id / fixed account names; reject anything that
    # could break out of the interactive command.
    if not value or any(c in value for c in ' \t\r\n"\'\\'):
        raise ValueError('unsafe keychain identifier: {!r}'.format(value))
    return value


def prompt_hidden(prompt):
    """Ask for a secret in a macOS dialog with hidden input.

    Avoids typing secrets in clear text into Alfred's search bar.
    Returns ``None`` if the user cancels.
    """
    script = ('on run argv\n'
              'display dialog (item 1 of argv) default answer "" with hidden answer '
              'with title "Gitea" with icon caution\n'
              'return text returned of result\n'
              'end run')
    p = subprocess.run(['osascript', '-e', script, prompt],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        return None
    return p.stdout.decode('utf-8').rstrip('\n')
