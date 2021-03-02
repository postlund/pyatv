#!/usr/bin/env python3
"""Simple tool to generate API reference documentation."""
import sys
import os
import argparse
import warnings
from difflib import unified_diff
from pathlib import Path

import pdoc

warnings.filterwarnings("ignore")
pdoc.tpl_lookup.directories.insert(0, os.path.join("docs", "pdoc_templates"))


def _filter_func(doc):
    for exclude in [
        "airplay",
        "mrp",
        "dmap",
        "support",
        "scripts",
    ]:
        if doc.refname.startswith("pyatv." + exclude):
            return False
    return True


def _api_modules():
    def _recursive_htmls(mod):
        yield mod.name, mod.html()
        for submod in mod.submodules():
            yield from _recursive_htmls(submod)

    modules = ["pyatv"]
    context = pdoc.Context()

    modules = [
        pdoc.Module(mod, context=context, docfilter=_filter_func) for mod in modules
    ]
    pdoc.link_inheritance(context)

    for mod in modules:
        for module_name, html in _recursive_htmls(mod):
            split = module_name.split(".")
            split[-1] = split[-1] + ".html"
            output_file = os.path.join("docs", "api", *split)
            yield output_file, html


def generate():
    """Generate API reference."""
    for output_file, html in _api_modules():
        print("Generating", output_file)
        with open(output_file, "wb") as f:
            f.write(html.encode("utf-8"))

    return 0


def verify():
    """Verify that API reference is up-to-date."""
    return_value = 0
    for output_file, html in _api_modules():
        print("Verifying", output_file)
        expected_output = Path(output_file).read_text(encoding="utf-8")
        if html != expected_output:
            print(
                "File content mismatch - run: api.py generate. Diff is below:",
                file=sys.stderr,
            )
            print(
                "".join(
                    unified_diff(expected_output.splitlines(1), html.splitlines(1))
                ),
                file=sys.stderr,
            )
            return_value = 1
    return return_value


def main():
    """Script starts here."""
    if not os.path.exists(".git"):
        print("Run this script from repo root", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["generate", "verify"], help="command to run"
    )

    args = parser.parse_args()

    if args.command == "generate":
        return generate()
    if args.command == "verify":
        return verify()

    return 1


if __name__ == "__main__":
    sys.exit(main())
