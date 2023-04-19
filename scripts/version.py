"""Work with versions in pyatv."""
import argparse
import re
import subprocess
import sys

# These are read and replace by the exec command
__version__ = None
PATCH_VERSION = None

# Read version from const.py without importing pyatv to not require it to be installed
with open("pyatv/const.py", "rb") as _const:
    exec(compile(_const.read(), "pyatv/const.py", "exec"))  # pylint: disable=exec-used


def call(cmd, *args, show_output=False):
    """Call a shell command."""
    result = subprocess.run(
        cmd.format(*args),
        shell=True,
        check=True,
        stdout=subprocess.PIPE if not show_output else None,
    )
    return None if show_output else result.stdout.decode("utf-8")


def get_version() -> str:
    """Return full version string, e.g. 0.8.2."""
    return __version__


def get_patch_version() -> str:
    """Return only patch version, e.g. 2."""
    return PATCH_VERSION


def set_patch_version(version: str) -> None:
    """Change patch version to something else."""
    output = ""
    with open("pyatv/const.py", "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("PATCH_VERSION"):
                output += f'PATCH_VERSION = "{version}"\n'
            else:
                output += line

    with open("pyatv/const.py", "w", encoding="utf-8") as handle:
        handle.write(output)


def update_sha1() -> None:
    """Add SHA1 of current commit to patch version."""
    current_sha1 = call("git rev-parse --short HEAD").replace("\n", "")
    patch_ver = re.match(r"(\d+).*", get_patch_version())
    if not patch_ver:
        raise RuntimeError(f"Invalid patch version found: {get_patch_version()}")

    set_patch_version(f"{patch_ver.group(1)}g{current_sha1}")


def is_release() -> bool:
    """Return if current branch is a release branch."""
    tag_name = call("git describe --tags").replace("\n", "")
    return re.match(r"^v\d+\.\d+\.\d+$", tag_name) is not None


def is_master() -> bool:
    """Return if current branch is master."""
    branch_name = call("git rev-parse --abbrev-ref HEAD").replace("\n", "")
    return branch_name == "master"


def main() -> None:
    """Script starts here."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="sub-commands", dest="command")

    subparsers.add_parser("get", help="Get version")

    setter = subparsers.add_parser("patch", help="Patch version")
    setter.add_argument("version", help="Change patch versiont")

    subparsers.add_parser("sha1", help="Insert SHA1 into patch version")

    subparsers.add_parser("is_release", help="Return if branch is release tag")
    subparsers.add_parser("is_master", help="Return if branch is master")

    args = parser.parse_args()
    if not args.command:
        parser.error("No command specified")
        return 1

    if args.command == "get":
        print(get_version())
    elif args.command == "patch":
        set_patch_version(args.version)
    elif args.command == "sha1":
        update_sha1()
    elif args.command == "is_release":
        return "true" if is_release() else "false"
    elif args.command == "is_master":
        return "true" if is_master() else "false"
    else:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
