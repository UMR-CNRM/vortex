## tests

With the exception of `test_config.py`, all the test modules listed
in this directory have been included as-is from vortex 1.  They are
not expected to pass, mostly due to breaking changes in some modules'
interface.

Porting this test suite for vortex 2 is ongoing work.  If you'd like
to help, just pick a test module and try to repait the tests it
contains.  It is also possible that some tests do not make sense
anymore.

### Running the tests

The test suite can be run with
[`pytest`](https://docs.pytest.org/en/stable/).  If your installation
of *vortex* included the `dev` optional set of dependencies, then
`pytest` should already be installed in your environnement.  If not,
you can install it with 

```
pip install pytest
```

To run the tests:

```
pytest
```
