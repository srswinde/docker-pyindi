# docker-pyindi
Docker recipes for the pyindi

## indiserver
The [indiserver](indiserver) image behavior is managed by these ENV variables:

 - INDI_VERBOSE (verbosity -v -vv or -vvv)
 - INDI_RESTART_COUNT (Number of times INDI will restart a crashed drivr)
 - INDI_DRIVERS (White space separated list of path to drivers to be run at startup)
 - INDI_FIFO_PATH (path to FIFO for runtime starting/stoping of drivers)
 
These are mostly arguments to the indiserver. For details see the [indiserver documntation](https://docs.indilib.org/indiserver/).
