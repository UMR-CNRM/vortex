# Contributing to bronx

Contributions are always welcome.

## Pull Request Process

Pull requests are the best way to propose changes to the codebase (we use Github
Flow). We actively welcome your pull requests:

1. Fork the repo and create your branch from master.
2. If you've added code that should be tested, add tests.
3. If you add a new sub-package, update the documentation.
4. Make sure your code lints (see below).
5. Ensure the test suite passes (see below).
6. Ensure the documentation builds (see below).
7. Issue the pull request!

## Code style and basic checks

* `pyflakes` should run without any error.
* The code needs to be PEP8 compliant (the line length should not exceed  120
* characters). This can be checked using `pycodestyle`.
* `pydocstyle` should run without error.

Here is a typical way to run all these tests (from the repository root)::

    $ pyflakes src tests
    $ pycodestyle --max-line-length=120 --ignore=W504 src
    $ pycodestyle --max-line-length=120 --ignore=W504 tests
    $ pydocstyle

If no warning pops up, that(s) ok!

## Test suite

Launching the `pytest` command at the repository root will run all the unit
tests. 

## Documentation builds

The `docs` subdirectory is equipped with a Makefile::

    $ cd docs
    $ make
    ...
