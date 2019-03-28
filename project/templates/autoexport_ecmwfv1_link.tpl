echo "Hostname: $(hostname)"
echo

HEADDIR=%{headdir}
FROM=%{from}
TO=%{to}

# Always Fail on error
set -e
set -x

cd $HEADDIR
rm -f $TO
ln -sf $FROM $TO

if [ ! -e $FROM ] ; then
    echo "WARNING: Source is missing: $FROM"
fi 
