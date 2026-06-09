import subprocess

NON_EXISTENT_REPOSITORY = "https://github.com/kuluruvineeth/donotexist.git"


def check_if_git_repository_exists(
    repository_url: str, branch_name: str | None = None
) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-remote", repository_url],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:  # noqa: BLE001
        return False

    if result.returncode != 0:
        return False
    if branch_name:
        return (
            f"refs/heads/{branch_name}" in result.stdout
            or f"refs/tags/{branch_name}" in result.stdout
        )
    return True
