## vortex

A Python library to write individual tasks in Numerical Weather
Prediction pipelines.

![A blue coloured vortex pointing downwards on a lighter blue background](vortex.png)

Experiments in Numerical Weather Prediction (NWP) and related fields
consist in a series of computational tasks that can depend on each
other's output data. Each task is typically made of three successive
steps:

1. Fetch required input data.
2. Execute a program.
3. Make the program's output data available to subsequent tasks in the
   pipeline.

Tasks have historically been written in some variant of the UNIX
shell, which was convenient to interact with the file system, manage
environment variables and execute programs.  As NWP pipelines and
tasks grow more and more complex, however, there is a need for a
language providing more abstraction and code reuse mechanisms.

On top of the popular Python language, *vortex* provides abstractions
that encapsulate running -- potentially distributed -- programs as
well as fetching and storing the data they consume and generate.

### Documentation

The documentation is available at [vortex-nwp.readthedocs.io](https://vortex-nwp.readthedocs.io).

### Installation

Vortex can be installed using `pip` like most Python packages:

```bash
pip install vortex-nwp
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
