import re
from urllib.parse import urlparse


class ValidationError(ValueError):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code


_HOSTNAME_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)
_COMMON_PASSWORDS = {
    "password",
    "123456",
    "12345678",
    "qwerty",
    "abc123",
    "password1",
    "111111",
    "iloveyou",
    "admin",
}


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValidationError("Invalid URL")
    if not _HOSTNAME_RE.match(parsed.netloc):
        raise ValidationError("Invalid URL")


def validate_new_password(value: str, user=None) -> str:
    if len(value) < 8:
        raise ValidationError(
            "This password is too short. It must contain at least 8 characters.",
            code="password_too_short",
        )
    if value.isdigit():
        raise ValidationError(
            "This password is entirely numeric.",
            code="password_entirely_numeric",
        )
    if value.lower() in _COMMON_PASSWORDS:
        raise ValidationError(
            "This password is too common.", code="password_too_common"
        )

    char_types = 0
    for regex in (r"[a-z]", r"[A-Z]", r"[0-9]", r"[^a-zA-Z0-9]"):
        if re.search(regex, value):
            char_types += 1
    if char_types < 2:
        raise ValidationError(
            "Password must contain at least 2 different types of characters "
            "(uppercase letters, lowercase letters, numbers, or symbols).",
            code="password_too_weak",
        )
    return value


def validate_url_domain(value: str) -> None:
    wildcard = "*."
    try:
        if value.startswith(wildcard):
            prefix, domain = value.split(wildcard)
            if len(prefix) != 0:
                raise ValidationError("Invalid domain")
            value = domain

        _validate_url("https://" + value)
        parsed = urlparse("https://" + value)
        if parsed.netloc != value:
            raise ValidationError("Invalid domain")
    except ValidationError:
        raise ValidationError(
            "Should be a domain without the scheme, pathname or querystring."
        )
    except Exception:
        raise ValidationError("Invalid domain")


def validate_url_path(value: str) -> None:
    try:
        _validate_url("https://dky.com" + value)
        parsed = urlparse("https://dky.com" + value)
        if parsed.path != value or ".." in value or "*" in value:
            raise ValidationError("Invalid Path")
    except ValidationError:
        raise ValidationError(
            "should be a valid pathname starting with `/` and not containing "
            "query parameters, `..` or `*`"
        )


def validate_env_name(value: str) -> None:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
        raise ValidationError(
            "Environment variable names shoud starts with an underscore (_) or a "
            "letter followed by letters, number or underscores(_)"
        )


def validate_git_commit_sha(value: str) -> None:
    if not re.compile(r"^(HEAD|[0-9a-f]{7,40})$", re.IGNORECASE).fullmatch(value):
        raise ValidationError(f"'{value}' is not a valid Git commit SHA.")
