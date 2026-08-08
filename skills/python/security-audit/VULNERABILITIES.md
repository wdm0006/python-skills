# Vulnerability Catalog

Each class below targets a finding the security-audit tooling flags. The vulnerable→fixed pairs are the patterns bandit, pip-audit, semgrep, and detect-secrets are configured to catch.

## Contents

- [SQL Injection](#sql-injection)
- [Command Injection](#command-injection)
- [Path Traversal](#path-traversal)
- [Hardcoded Credentials](#hardcoded-credentials)
- [Weak Cryptography](#weak-cryptography)
- [Insecure Deserialization](#insecure-deserialization)
- [SSRF](#ssrf)
- [XXE](#xxe)
- [Tool Coverage Summary](#tool-coverage-summary)

## SQL Injection

Caught by: bandit (B608), semgrep.

```python
# Vulnerable — user_id interpolated into the query string
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
cursor.execute("SELECT * FROM users WHERE name = '%s'" % name)
```

```python
# Fixed — parameters bound by the driver, never string-formatted
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
cursor.execute("SELECT * FROM users WHERE name = %s", (name,))
```

Identifiers (table/column names) cannot be parameterized. Validate them against an allowlist rather than interpolating request data.

## Command Injection

Caught by: bandit (B602/B605), semgrep.

```python
# Vulnerable — shell parses the string, so filename can inject `; rm -rf /`
subprocess.run(f"cat {filename}", shell=True)
os.system("ping " + host)
```

```python
# Fixed — argument vector, no shell, no word-splitting
subprocess.run(["cat", filename], check=True)
subprocess.run(["ping", "-c", "1", host], check=True)
```

Never build a shell string from external input. If a shell feature is truly required, `shlex.quote()` each argument, but prefer the argument-list form.

## Path Traversal

Caught by: bandit (B108 for temp paths), semgrep; also enforce at runtime.

```python
# Vulnerable — filename of "../../etc/passwd" escapes the base directory
path = os.path.join(base_dir, filename)
open(path).read()
```

```python
# Fixed — resolve and confirm the result stays under the base
base = Path(base_dir).resolve()
target = (base / filename).resolve()
if not target.is_relative_to(base):
    raise ValueError("Path escapes base directory")
target.read_text()
```

`is_relative_to` requires resolving both paths first so symlinks and `..` segments are collapsed before the check.

## Hardcoded Credentials

Caught by: detect-secrets, bandit (B105/B106).

```python
# Vulnerable — secret committed to source control
API_KEY = "sk-live-9f8a7b6c5d4e3f2a1b0c"
db = connect(password="hunter2")
```

```python
# Fixed — read from the environment; fail loudly if unset
API_KEY = os.environ["API_KEY"]
db = connect(password=os.environ["DB_PASSWORD"])
```

Rotate any secret that reached version control; removing the line does not undo the exposure. See CI_SECURITY.md for the detect-secrets baseline that keeps this out of future commits.

## Weak Cryptography

Caught by: bandit (B303 for md5/sha1, B311 for `random`).

```python
# Vulnerable — MD5/SHA1 are broken for integrity; `random` is predictable
digest = hashlib.md5(data).hexdigest()
token = str(random.random())
password_hash = hashlib.sha256(password.encode()).hexdigest()
```

```python
# Fixed — SHA-256+ for integrity, secrets for tokens, a KDF for passwords
digest = hashlib.sha256(data).hexdigest()
token = secrets.token_urlsafe(32)
import bcrypt
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

`random` is a PRNG seeded predictably — never use it for tokens, salts, or session IDs; use `secrets`. Plain SHA-256 is wrong for passwords because it is fast; use bcrypt, scrypt, or argon2.

## Insecure Deserialization

Caught by: bandit (B301 pickle, B506 yaml.load).

```python
# Vulnerable — both execute arbitrary code from crafted input
obj = pickle.loads(untrusted_bytes)
config = yaml.load(untrusted_text)
```

```python
# Fixed — a data-only format, or yaml's safe loader
obj = json.loads(untrusted_text)
config = yaml.safe_load(untrusted_text)
```

`pickle`, `marshal`, and `yaml.load` (without `SafeLoader`) instantiate arbitrary objects and are equivalent to remote code execution on attacker-controlled data. Reserve pickle for trusted, in-process data only.

## SSRF

Caught by: semgrep; also enforce at runtime.

```python
# Vulnerable — attacker points url at internal metadata / localhost services
url = request.args["url"]
resp = requests.get(url)
```

```python
# Still vulnerable — validation and connection perform separate DNS lookups
parsed = urllib.parse.urlparse(url)
addresses = socket.getaddrinfo(parsed.hostname, 443)
if any(ipaddress.ip_address(item[4][0]).is_private for item in addresses):
    raise ValueError("Disallowed URL")
resp = requests.get(url, timeout=5)  # resolves the hostname again
```

That check has two holes. An attacker-controlled hostname can resolve to a public
address during validation and an internal address when the HTTP client resolves it
again (DNS rebinding). Redirects create the same gap at every hop.

The safe invariant is **connect only to an address returned by validation**:

```python
CGNAT = ipaddress.ip_network("100.64.0.0/10")

def address_is_blocked(text: str) -> bool:
    address = ipaddress.ip_address(text)
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or address in CGNAT
    )

# Pseudocode: the transport API differs by HTTP client.
target = validate_url_and_resolve(url)  # returns original host + approved IPs
response = transport.request(
    connect_ip=choose(target.approved_ips),
    authority=target.hostname,           # HTTP Host / HTTP/2 :authority
    tls_server_name=target.hostname,     # certificate verification and SNI
)
```

Do not substitute `ip_address(...).is_private` for an explicit deny policy:
Python does not classify carrier-grade NAT (`100.64.0.0/10`) as private, even
though it is not a safe public destination for an SSRF fetcher. Include IPv4 and
IPv6 results, and reject the hostname if **any** resolved address is forbidden;
otherwise an attacker can influence which answer the client selects.

If redirects are enabled, handle them manually with a small hop limit. Parse,
allowlist, resolve, validate, and pin the connection again for every `Location`.
Preserve the redirected URL's original authority and TLS server name while the
socket connects to the approved IP. Disabling redirects is simpler and preferred
when the product does not require them.

Tests must prove the validation-to-connection binding, not merely mock the
validator: simulate DNS returning public-then-loopback answers and assert that the
transport either uses the retained public IP or rejects the request without a
second unconstrained lookup. Repeat the test for a redirect target and include
CGNAT, IPv6 loopback, link-local, and mixed public/private answer sets.

## XXE

Caught by: bandit (B314/B320 for xml.etree/lxml), semgrep.

```python
# Vulnerable — default parsers resolve external entities and DTDs
import xml.etree.ElementTree as ET
tree = ET.fromstring(untrusted_xml)
```

```python
# Fixed — defusedxml hardens the parser against entity expansion and XXE
import defusedxml.ElementTree as ET
tree = ET.fromstring(untrusted_xml)
```

Add `defusedxml` as a dependency and swap it in for the stdlib `xml.*` and `lxml` imports on any path that parses untrusted XML. It blocks external-entity resolution, billion-laughs expansion, and external DTD loads.

## Tool Coverage Summary

| Vulnerability | Primary tool | Signal |
|---------------|--------------|--------|
| SQL injection | bandit / semgrep | B608, string-formatted query |
| Command injection | bandit / semgrep | B602, B605, shell=True |
| Path traversal | bandit / semgrep | B108, unvalidated join |
| Hardcoded credentials | detect-secrets / bandit | entropy match, B105/B106 |
| Weak crypto | bandit | B303, B311 |
| Insecure deserialization | bandit | B301, B506 |
| SSRF | semgrep | request to unvalidated URL |
| XXE | bandit / semgrep | B314, B320 |

Run all four tools together through `scripts/security_scan.py`; see CI_SECURITY.md for wiring it into CI.
