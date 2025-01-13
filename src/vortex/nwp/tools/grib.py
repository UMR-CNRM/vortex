"""
TODO: Module documentation.
"""

import json

import footprints
from bronx.fancies import loggers
from vortex import sessions
from vortex.algo.components import AlgoComponentError
from vortex.layout.contexts import Context

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class _GenericFilter:
    """This class could be the start of filtering classes for different formats."""

    def __init__(self):
        """

        No parameters.
        """
        self._filters = list()
        self._sh = sessions.system()

    def add_filters(self, *filters):
        """Add one or more filters to the filters list.

        :param filters: a list of filters

        Filters are described using dictionaries. Here is an example of such a
        dictionary::

            {
              "fields_include": [
                {
                  "indicatorOfTypeOfLevel": 100,
                  "shortName": "t",
                  "level": [
                    850,
                    500,
                    300
                  ]
                }
              ],
              "fid_format": "GRIB1",
              "filter_name": "toto"
            }

        **fields_include** or **fields_exclude** lists depends on the data
        format specified with the **fid_format** key.

        The filters argument of this function accepts dictionaries but also
        strings or Context objects :

            * If a string is provided, it will be converted to a dictionary
              using json.loads
            * If a Context object is provided, the Context's sequence will be
              used to find available resources of filtering_request kind. The
              content of such resources will be used as a filter.

        """

        for a_filter in filters:
            if isinstance(a_filter, dict):
                self._filters.append(a_filter)
            elif isinstance(a_filter, str):
                self._filters.append(json.loads(a_filter))
            elif isinstance(a_filter, Context):
                for a_request in a_filter.sequence.effective_inputs(
                    kind="filtering_request"
                ):
                    self._filters.append(a_request.rh.contents.data)

    def __len__(self):
        """Returns the number of active filters."""
        return len(self._filters)

    @staticmethod
    def _is_dict_superset(full, subset):
        """Finds out if the full dictionary contains and matches subset."""
        superset_ok = True
        for k, v in subset.items():
            # Ignore the comments...
            if k.startswith("comment"):
                continue
            # Check for the key inside the full dictionary
            try:
                fullvalue = full[str(k)]
            except KeyError:
                superset_ok = False
                break
            # Does the key match ?
            if isinstance(v, (list, tuple)):
                if fullvalue not in v:
                    superset_ok = False
                    break
            else:
                if fullvalue != v:
                    superset_ok = False
                    break
        return superset_ok

    def _filter_process(self, fid, a_filter):
        """Check if the data's fid complies with the filter."""
        includes = a_filter.get("fields_include", [])
        excludes = a_filter.get("fields_exclude", [])
        try:
            fid = fid[a_filter["fid_format"]]
        except KeyboardInterrupt:
            raise ValueError(
                "Please specify a valid fid_format in the filter description"
            )
        # First process includes
        includes_ok = True
        for include in includes:
            includes_ok = self._is_dict_superset(fid, include)
            if includes_ok:
                break
        # Process the excludes if necessary
        if includes_ok:
            for exclude in excludes:
                includes_ok = not self._is_dict_superset(fid, exclude)
                if not includes_ok:
                    break
        return includes_ok

    def __call__(self, inputfile, outfile_fmt):
        """Apply the various filters on *inputfile*. Should be implemented..."""
        raise NotImplementedError("This method have to be overwritten.")


class GRIBFilter(_GenericFilter):
    """Class in charge of filtering GRIB files."""

    CONCATENATE_FILTER = "concatenate"

    def __init__(self, concatenate=False):
        """

        :param bool concatenate: Wether to generate a concatenated GRIB file
        """
        super().__init__()
        self.concatenate = concatenate
        self._xgrib_support = "grib" in self._sh.loaded_addons()

    def __len__(self):
        """Returns the number of active filters (concatenate included)."""
        return super().__len__() + (1 if self.concatenate else 0)

    def _simple_cat(self, gribfile, outfile_fmt, intent):
        """Just concatenate a multipart GRIB."""
        if self._xgrib_support and self._sh.is_xgrib(gribfile):
            self._sh.xgrib_pack(
                gribfile,
                outfile_fmt.format(filtername=self.CONCATENATE_FILTER),
                intent=intent,
            )
        else:
            # Just make a copy with the appropriate name...
            self._sh.cp(
                gribfile,
                outfile_fmt.format(filtername=self.CONCATENATE_FILTER),
                intent=intent,
                fmt="grib",
            )

    def __call__(self, gribfile, outfile_fmt, intent="in"):
        """Apply the various filters on *gribfile*.

        :param gribfile: The path to the input GRIB file
        :param outfile_fmt: The path of output files

        The *outfile_fmt* must be a format string such as
        **GRIBOUTPUT_{filtername:s}.grib** where **filtername** will be replaced
        by the name of the filter.
        """

        if not self._sh.path.exists(gribfile):
            raise OSError("{!s} doesn't exist".format(gribfile))

        # We just want to concatenate files...
        if not self._filters:
            if self.concatenate:
                self._simple_cat(gribfile, outfile_fmt, intent=intent)
                return [
                    outfile_fmt.format(filtername=self.CONCATENATE_FILTER),
                ]
            else:
                raise ValueError("Set concatenate=True or provide a filter.")

        # Open the input file using Epygram
        from ..util import usepygram

        if not usepygram.epygram_checker.is_available(version="1.0.0"):
            raise AlgoComponentError("Epygram (v1.0.0) needs to be available")

        if self._xgrib_support and self._sh.is_xgrib(gribfile):
            idx = self._sh.xgrib_index_get(gribfile)
            in_data = [
                footprints.proxy.dataformat(
                    filename=self._sh.path.realpath(a_gribfile),
                    openmode="r",
                    format="GRIB",
                )
                for a_gribfile in idx
            ]
        else:
            in_data = [
                footprints.proxy.dataformat(
                    filename=self._sh.path.realpath(gribfile),
                    openmode="r",
                    format="GRIB",
                ),
            ]

        # Open output files
        out_data = list()
        out_filelist = list()
        for a_filter in self._filters:
            f_name = outfile_fmt.format(filtername=a_filter["filter_name"])
            out_filelist.append(f_name)
            # It would be a lot better to use io.open but grib_api is very annoying !
            out_data.append(open(f_name, "wb"))
        if self.concatenate:
            f_name = outfile_fmt.format(filtername=self.CONCATENATE_FILTER)
            out_filelist.append(f_name)
            # It would be a lot better to use io.open but grib_api is very annoying !
            out_cat = open(f_name, "wb")

        with usepygram.epy_env_prepare(sessions.current()):
            for a_in_data in in_data:
                msg = a_in_data.iter_messages(headers_only=False)
                while msg is not None:
                    for a_out_data, a_filter in zip(out_data, self._filters):
                        thefid = msg.genfid()
                        if self._filter_process(thefid, a_filter):
                            logger.debug(
                                "Select succeed for filter %s: %s",
                                a_filter["filter_name"],
                                thefid,
                            )
                            msg.write_to_file(a_out_data)
                    if self.concatenate:
                        msg.write_to_file(out_cat)
                    msg = a_in_data.iter_messages(headers_only=False)

        # Close outpout files
        for a_in_data in in_data:
            a_in_data.close()
        for a_out_data in out_data:
            a_out_data.close()
        if self.concatenate:
            out_cat.close()

        return out_filelist


def grib_inplace_cat(t, rh):
    """Ensure that a GRIB file is a usual single file (if not, concatenate it).

    This function is designed to be used as a hook function.

    :param t: A :class:`vortex.sessions.Ticket` object
    :param rh: A :class:`vortex.data.handlers.Handler` object
    """
    xgrib_support = "grib" in t.sh.loaded_addons()
    if xgrib_support:
        if t.sh.is_xgrib(rh.container.localpath()):
            # Some cleanup...
            rh.reset_contents()
            rh.container.close()
            # Move the index file prior to the concatenation
            tmpfile = (
                rh.container.localpath() + "_concat" + t.sh.safe_filesuffix()
            )
            t.sh.move(rh.container.localpath(), tmpfile)
            # Concatenate
            t.sh.xgrib_pack(tmpfile, rh.container.localpath())
            # Remove the multipart file
            t.sh.grib_remove(tmpfile)
            logger.info("The multipart GRIB has been concatenated.")
        else:
            logger.info(
                "The localpath is not a multipart GRIB: nothing to do."
            )
    else:
        logger.info(
            "Multipart GRIB support is not activated: nothing can be done."
        )
