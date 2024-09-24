## VORTEX

Versatile Objects Rounded-Up in a Toolbox for Environmental eXperiments

### Documentation

Documentation is available at

http://intra.cnrm.meteo.fr/algopy/sphinx/vortex/current/

currently unreachable from outside of Météo-France's internal network.

### Installation

VORTEX is available on most machines you'll come to use at
Météo-France.  Unless you want to contribute to the project, there is
probably no reason for you to install VORTEX manually.

- belenos/taranis: `/home/mf/dp/marp/verolive/vortex/vortex-olive`
- CNRM laptops: `/home/common/sync/vortex/vortex-olive`
- CNRM team servers: `/d0/verolive/vortex/vortex-olive`
- DSI dev servers (`soprano`): `/home/marp/marp999/vortex/vortex-olive`

To use VORTEX, the installation path must be added to PYTHONPATH, for instance

```
VORTEX_BASE_DIR=/home/mf/dp/marp/verolive/vortex/vortex-olive
export PYTHONPATH=$PYTHONPATH:$VORTEX_BASE_DIR/src:$VORTEX_BASE_DIR/site
```

To use VORTEX comand line tools, the PATH variable should also be adjusted:

```
export PATH=$PATH:VORTEX_BASE_DIR/bin
```

You could execute the above lines each time you want to use VORTEX, or
add them to your `.bashrc` bash configuration file.

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).







