---
layout: template
title: Submit a PR
permalink: /internals/submit-pr
link_group: internals
---
# :star: Submit a PR

* Fork this repository
* Make changes and push to fork
  * Make sure that tests, linting, etc. pass by running `chickn` locally
  * New code shall have [type hints](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
  * Update documentation if needed
  * PR cannot be merged if any check in `chickn` fails
* Open a new PR
  * If you are fixing a bug, please reference it with "Fixes #xxx" (alternatively "Relates
    to #xxx") in commit message or pull request message to connect them
  * Prefix the commit message with a topic, see [topics](#topics)
* Await review comments
* Fix potential comments
* Wait for PR to be merged

## Topics

To make it easier to see where a commit makes changes, add a prefix topic to the commit message. Here are a few topics that are used (suggest new if necessary):

| Topic | What/where you have changed |
| ----- | --------------------------- |
| airplay | Something related to `AirPlay`, likely in {% include code file="airplay" %}.
| companion | Something related to `Companion`, likely in {% include code file="companion" %}.
| cq | Code Quality, e.g, clean ups, added documentation, refactoring.
| docs | Documentation in `docs`.
| gha | GitHub Actions (`.github/workflows`).
| dmap  | Something related to `DMAP`, likely in {% include code file="dmap" %}.
| if | Interface related changes (e.g. {% include code file="interface.py" %}).
| mrp   | Something related to `MRP`, likely in {% include code file="mrp" %}.
| raop | Something related to `RAOP`, likely in {% include code file="raop" %}.
| scan | Scanning related code, likely {% include code file="support/scan.py" %}.

Try so split changes over multiple commits if possible, to keep them small (e.g. one for adding interface, one for implementing `MRP`, one for `DMAP` and one for documentation).

Some examples of first lines in commit messages:

```raw
cq: Add typing hints to public interface
if: Add interface for device information
raop: Send feedback if supported by receiver
test: Migrate from asynctest to pytest-asyncio
```

# Known Issues

There are currently two known issues with GitHub Actions:

* pytest sometimes fails with an "internal error". Reason is still unknown, restart jobs until it succeeds.
* pip sometimes fails due to files being broken (bad CRC or BadGzipFile), not sure how to fix that