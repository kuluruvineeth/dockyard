import os
import subprocess


def clone_git_repository(
    repository_url: str, branch_name: str, destination: str
) -> str:
    result = subprocess.run(
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
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[-1000:] or "git clone failed")

    head = subprocess.run(
        ["git", "-C", destination, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return head.stdout.strip()


def build_docker_image(
    context_dir: str,
    dockerfile_path: str,
    image_tag: str,
    build_args: dict[str, str] | None = None,
) -> str:
    dockerfile = os.path.normpath(os.path.join(context_dir, dockerfile_path))
    command = ["docker", "build", "-f", dockerfile, "-t", image_tag]
    for key, value in (build_args or {}).items():
        command += ["--build-arg", f"{key}={value}"]
    command.append(context_dir)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[-1000:] or "docker build failed")
    return image_tag
