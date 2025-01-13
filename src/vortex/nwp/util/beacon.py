"""
Functions to create and write a few information in a file using Vortex
(FunctionStore).
"""

import io
import json

#: No automatic export
__all__ = []


def beaconfunction(options):
    """Function to create a file and write information in it.

    - model
    - date
    - cutoff
    - vapp
    - vconf
    - member (optional)
    """
    rst = dict()

    # Find out if a resource handler is present and load the elements to be written
    rhdict = options.get("rhandler", None)
    if rhdict:
        rst["vapp"] = rhdict.get("provider", {}).get("vapp", "")
        rst["vconf"] = rhdict.get("provider", {}).get("vconf", "")
        rst["model"] = rhdict.get("resource", {}).get("model", "")
        rst["date"] = rhdict.get("resource", {}).get("date", "")
        rst["cutoff"] = rhdict.get("resource", {}).get("cutoff", "")
        member = rhdict.get("provider", {}).get("member", None)
        if member is not None:
            rst["member"] = member
    else:
        rst["error"] = "No resource handler here"
    outstr = json.dumps(rst)
    # Return the string, which has to be converted to a file like object
    return io.BytesIO(outstr.encode(encoding="utf_8"))
