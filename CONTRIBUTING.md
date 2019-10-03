# Contributing

First off, thank you for showing an interest in pyatv and perhaps also contributing!
Every contribution matters and it's people like you that make pyatv great! :heart:

## Getting Started

### Resources to read

Make sure to read these awesome documents:

[Code of Conduct](CODE_OF_CONDUCT.md)

[FAQ](https://pyatv.readthedocs.io/en/master/faq.html)

### Reporting a bug

If you think you have found a bug, please consider writing an issue about it. Use the "Bug" template
and be as precise as you can.

[Click here to open a new bug report](https://github.com/postlund/pyatv/issues/new?assignees=&labels=bug&template=bug_report.md&title=)

### Requesting a new feature

New features are always cool, maybe you have some ideas or wishes? There is a template for feature
requests as well. Just create an issue and fill it out.

[Click here to request a new feature](https://github.com/postlund/pyatv/issues/new?assignees=&labels=feature&template=feature_request.md&title=)

### Questions or ideas

If you have any questions (e.g. "how do I do this with pyatv"), you can write an issue as well. You can also
leave ideas for other kinds of improvements, like gaps in the documentation or better development tools.

[Click here to ask a general question](https://github.com/postlund/pyatv/issues/new?assignees=&labels=question&template=question-or-idea.md&title=)

## Development

### Getting code and setting up development environment

Getting started with development is quite simple:

```
1. Fork this project on GitHub
2. git clone https://github.com/<username>/pyatv.git
3. cd pyatv
4. ./setup_dev_env.sh
```

This will set everything up. To run tests, linting, etc. just run activate the virtual environment and run tox:

```shell
$ source bin/activate
(pyatv)$ tox
```

### Pull Requests (PR)

When submitting changes, create a PR and make sure:

* You add tests for new functionality and/or bug fixes
* All tests must pass
* Do not decrease code coverage
* Add pydoc documentation and update `docs/`
* Linting passes (just run tox)

PRs will not be merged unless all criterias are met. If you are unsure about anything, just push a PR and ask
for help in the PR itself :smile:

### License

The MIT license is used by pyatv and by contributing, you agree that your content will be covered by that license.
