#!/bin/bash
#PBS -N vtxsync
#PBS -S /bin/bash
#PBS -q ns
#PBS -l walltime=00:02:00
#PBS -l EC_memory_per_task=128mb
#PBS -j oe
#PBS -m a

echo "Hostname: $(hostname)"
echo

PYTHON_27=%{python27}
LD_LIBS_27=%{ldlibs27}
PYTHON_3=%{python3}
LD_LIBS_3=%{ldlibs3}

STAGEDIR=%{stagedir}
HEADDIR=%{headdir}
LOCAL=%{local}

TGZSOURCEFILE=%{tmplocation}
TGZSOURCEHOST=%{tmphost}
TGZLOCALNAME=$(basename $TGZSOURCEFILE)
VTXNAME=$(basename $LOCAL | sed -r 's/\.(tgz|tar|tar\.gz)$//')

# Always Fail on error
set -e
set -x

# Temporary directory
cd $HOME
mkdir -p $STAGEDIR
TMPWKDIR=$(mktemp -d --tmpdir=$STAGEDIR)

PREVTB=
cleanup()
{
    cd $HOME
    echo "Removing $TMPWKDIR"
    rm -rf $TMPWKDIR
    if [ -n "$PREVTB" ] ; then
        echo "Removing $PREVTB"
        rm -rf $PREVTB
    fi
    echo "Removing $TGZSOURCEHOST:$TGZSOURCEFILE (ssh)"
    ssh $TGZSOURCEHOST "rm -f $TGZSOURCEFILE"
}
trap 'cleanup' 0

cd $TMPWKDIR

# Get the input tar file
echo "Getting Vortex from $TGZSOURCEHOST:$TGZSOURCEFILE (scp)"
scp $TGZSOURCEHOST:$TGZSOURCEFILE $TGZLOCALNAME

# Unpack
echo "Untar..."
tar xf $TGZLOCALNAME

# Launch tests
echo "Testing..."
cd $VTXNAME
export LANG='en_US.UTF-8'
export PYTHONPATH=$(pwd)/src:$(pwd)/site:$(pwd)/project:$PYTHONPATH
if [ -n "$PYTHON_27" ] ; then
  if [ -n "$LD_LIBS_27" ] ; then
    export LD_LIBRARY_PATH=$LD_LIBS_27:$LD_LIBRARY_PATH
  fi
  $PYTHON_27 tests/do_working_tests-2.7.py
fi
if [ -n "$PYTHON_3" ] ; then
  if [ -n "$LD_LIBS_3" ] ; then
    export LD_LIBRARY_PATH=$LD_LIBS_3:$LD_LIBRARY_PATH
  fi
  $PYTHON_3 tests/do_working_tests-3.py
fi

# Ok, install the toolbox
echo "Install..."
cd $TMPWKDIR
mkdir -p $HEADDIR
if [ -d $HEADDIR/$VTXNAME ] ; then
    PREVTB=$HEADDIR/$VTXNAME.todelete
    echo "Putting away the previous install ($PREVTB)..."
    mv $HEADDIR/$VTXNAME $PREVTB
fi
mv $VTXNAME $HEADDIR/$VTXNAME
