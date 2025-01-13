"""
Usage of the TNT package.
"""

import codecs
import io

from bronx.fancies import loggers
from bronx.syntax.externalcode import ExternalCodeImportChecker

from vortex import sessions
from vortex.data.stores import FunctionStoreCallbackError
from vortex.util.roles import setrole

logger = loggers.getLogger(__name__)

tnt_checker = ExternalCodeImportChecker("thenamelisttool")
with tnt_checker as tnt_register:
    import thenamelisttool

__all__ = []


@tnt_checker.disabled_if_unavailable
def compose_nam(options):
    """Use a TNT recipe in order to build a namelist file.

    This function is designed to be executed by a
    :obj:`vortex.data.stores.FunctionStore` object.

    In order to "execute" the TNT recipe, this function requires a namelist
    pack to be available in the inputs sequence. By default, this namelist
    pack should have the "MainNamelistPack" role. This default value can
    be overriden using the `nampack` attribute of the URI query.

    The recipe file should be named `[source].yaml` where `[source]` stands
    for the `source` attribute of the obj:`~nwp.data.namelists.Namelist`
    resource object.

    By defaut, the recipe file is looked for in the namelist pack mentioned
    above. The role of an alternative pack can be designated using the
    `dirpack` attribute of the URI.

    :param dict options: All the options passed to the store plus anything from
                         the query part of the URI.

    :return: Content of a :obj:`nwp.data.namelists.Namelist` resource

    :rtype: A file like object
    """
    rhdict = options.get("rhandler", None)
    source = rhdict["resource"].get("source", None)
    if source is None:
        logger.error("Inapropriate type of resource. Got:\n%s", rhdict)
        raise FunctionStoreCallbackError("Inapropriate type of resources.")

    t = sessions.current()

    def _get_pack_adress(role):
        role = setrole(role)
        packlist = [
            sec.rh for sec in t.context.sequence.filtered_inputs(role=role)
        ]
        if len(packlist) != 1:
            logger.error("The number of namelist packs with role=%s is not 1.")
            raise FunctionStoreCallbackError(
                "Incorrect number of namelist packs."
            )
        packrh = packlist[0]
        if packrh.resource.realkind != "namelistpack":
            logger.error(
                "Incorrect resource type for role %s. Resource handler:\n%s",
                role,
                packrh.icdard(),
            )
            raise FunctionStoreCallbackError("Incorrect resource type.")
        if not packrh.container.filled:
            logger.error(
                "The resource handler's container is not filled for role %s",
                role,
            )
            raise FunctionStoreCallbackError("RH container is not filled.")
        return packrh.container.abspath

    nampack_path = _get_pack_adress(
        options.get("nampack", "Main Namelist Pack")
    )
    dirpack_role = options.get("dirpack", None)
    dirpack_path = (
        _get_pack_adress(dirpack_role) if dirpack_role else nampack_path
    )

    out_io = io.BytesIO()
    thenamelisttool.util.compose_namelist(
        t.sh.path.join(dirpack_path, source + ".yaml"),
        sourcenam_directory=nampack_path,
        sorting=thenamelisttool.namadapter.FIRST_ORDER_SORTING,
        squeeze=False,
        fhoutput=codecs.getwriter("utf-8")(out_io),
    )
    return out_io
