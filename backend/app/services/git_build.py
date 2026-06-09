import subprocess


def clone_git_repository(
    repository_url: str, branch_name: str, destination: str
) -> str:
    subprocess.run(
        [
            "git",
            "clone",
            "--branch",
            branch_name,
            "--depth",
            "1",
            repository_url,
            destination,
        ],
        check=True,
        capture_output=True,
        timeout=300,
    )
    result = subprocess.run(
        ["git", "-C", destination, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def build_docker_image(
    context_dir: str,
    dockerfile_path: str,
    image_tag: str,
    build_args: dict[str, str] | None = None,
) -> str:
    command = ["docker", "build", "-f", dockerfile_path, "-t", image_tag]
    for key, value in (build_args or {}).items():
        command += ["--build-arg", f"{key}={value}"]
    command.append(context_dir)
    subprocess.run(
        command,
        check=True,
        capture_output=True,
        timeout=1800,
    )
    return image_tag
