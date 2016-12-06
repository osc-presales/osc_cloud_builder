# OSC Cloud Builder

The **OCB** project provides tools as snippets and modules.

************
Introduction
************

**OCB** is a set of boto connectors, generic tools and samples scripts to be used to ease the build of platforms.

******
Setup
******

# Cloud account setup
First of all, in order to run scripts you have to setup your Cloud account via environment variables.
Setup of the following variables:
* export AWS_ACCESS_KEY_ID=XXXX424242XXXX
* export AWS_SECRET_ACCESS_KEY=YYYYY4242YYYYY

Then you have to setup the region
* export FCU_ENDPOINT=fcu.<REGION_NAME>.outscale.com
* export LBU_ENDPOINT=lbu.<REGION_NAME>.outscale.com
* export EIM_ENDPOINT=eim.<REGION_NAME>.outscale.com
* export OSU_ENDPOINT=osu.<REGION_NAME>.outscale.com

# Configure PYTHONPATH
Go to root of this project, then run:

> $>export PYTHONPATH=$PYTHONPATH:$PWD/osc_cloud_builder


# Quick start
> >>>from OCBase import OCBase
> >>>ocb = OCBase()
> >>>print ocb.fcu.get_only_instances()
> >>>print ocb.eim.get_user()
> >>>print ocb.lbu.get_all_load_balancers()

# console.py
This script aim to be used in a python intepreter (ptpython or bpython for instance) after setting up your environment variables or your settings.ini
> $>ptpythn -i console.py
> >>> ocb.fcu.get_only_instances()
> [Instance:i-c90defd4, Instance:i-d74aaf02]

# Directories
## ./osc_cloud_builder/
## OCBase.py
This file contains the OCBase class with boto connectors to:
- FCU
- EIM
- LBU
- OSU

### ./osc_cloud_builder/tools/
This directory contains common tools.

### ./samples/
This directory contain useful samples.