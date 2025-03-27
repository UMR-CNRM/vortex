"""
Configuration management through ini and template files.

The :func:`load_template` function is the entry-point when looking for template files.
It returns an object compliant with the interface defined in
:class:`AbstractTemplatingAdapter`.
"""

import abc
from configparser import NoOptionError, NoSectionError, InterpolationDepthError
from configparser import ConfigParser
import itertools
from pathlib import Path
import re
import string

import footprints
from bronx.fancies import loggers
from bronx.stdtypes import date as bdate
from bronx.syntax.parsing import StringDecoder, StringDecoderSyntaxError
from vortex import sessions

__all__ = []

logger = loggers.getLogger(__name__)

_RE_AUTO_TPL = re.compile(r"^@(([^/].*)\.tpl)$")

_RE_ENCODING = re.compile(r"^\s*#.*?coding[=:]\s*([-\w.]+)")

_RE_TEMPLATING = re.compile(r"^\s*#\s*vortex-templating\s*[=:]\s*([-\w.]+)$")

_DEFAULT_CONFIG_PARSER = ConfigParser


class AbstractTemplatingAdapter(metaclass=abc.ABCMeta):
    """Interface to any templating system.

    To render the template, just call the object with a list of named arguments
    that should be used during template rendering.
    """

    def __init__(self, tpl_str, tpl_file, tpl_encoding):
        """
        :param tpl_str: The template (as a string)
        :param tpl_file: The template filename (path object)
        :param tpl_encoding: The template encoding (when read from disk)
        """
        self._tpl_file = tpl_file
        self._tpl_encoding = tpl_encoding
        self._tpl_obj = self._rendering_tool_init(tpl_str)

    @property
    def srcfile(self):
        """The template filename (when read from disk)."""
        return str(self._tpl_file)

    @abc.abstractmethod
    def _rendering_tool_init(self, tpl_str):
        pass

    def substitute(self, *kargs, **kwargs):
        """Render the template using the kargs and kwargs dictionaries."""
        todo = dict()
        for m in kargs:
            todo.update(m)
        todo.update(kwargs)
        return self(**todo)

    safe_substitute = substitute

    @abc.abstractmethod
    def __call__(self, **kwargs):
        """Render the template using the kwargs dictionary."""
        pass


class LegacyTemplatingAdapter(AbstractTemplatingAdapter):
    """Just use :class:`string.Template` for the rendering.

    See :class:`AbstractTemplatingAdapter` for more details on this class usage.
    """

    def _rendering_tool_init(self, tpl_str):
        return string.Template(tpl_str)

    def safe_substitute(self, *kargs, **kwargs):
        """Render the template using the kargs and kwargs dictionaries."""
        return self._tpl_obj.safe_substitute(*kargs, **kwargs)

    def __call__(self, **kwargs):
        """Render the template using the kwargs dictionary."""
        return self._tpl_obj.substitute(kwargs)


class TwoPassLegacyTemplatingAdapter(AbstractTemplatingAdapter):
    """Just use :class:`string.Template`, but render the template two times.

    (it allows for two level of nesting in the variable to be rendered).

    See :class:`AbstractTemplatingAdapter` for more details on this class usage.
    """

    def _rendering_tool_init(self, tpl_str):
        return string.Template(tpl_str)

    def safe_substitute(self, *kargs, **kwargs):
        """Render the template using the kargs and kwargs dictionaries."""
        return string.Template(
            self._tpl_obj.safe_substitute(*kargs, **kwargs)
        ).safe_substitute(*kargs, **kwargs)

    def __call__(self, **kwargs):
        """Render the template using the kwargs dictionary."""
        return string.Template(self._tpl_obj.substitute(kwargs)).substitute(
            kwargs
        )


_TEMPLATE_RENDERING_CLASSES = {
    "legacy": LegacyTemplatingAdapter,
    "twopasslegacy": TwoPassLegacyTemplatingAdapter,
}


def register_template_renderer(key, cls):
    _TEMPLATE_RENDERING_CLASSES[key] = cls


def load_template(tplpath, encoding=None, default_templating="legacy"):
    """Load a template according to *tplfile*.

    :param str tplpath: path-like object for the template file
    :param str encoding: The characters encoding of the template file
    :param int version: Find a template file with version >= to version
    :param str default_templating: The default templating engine that will
      be used. The content of the template file is always searched in
      order to detect a "# vortex-templating:" comment that will overrid
      this default.
    :return: A :class:`AbstractTemplatingAdapter` object

    The characters encoding of the template file may be specified. If
    *encoding* equals ``script``, a line looking like ``#
    encoding:special-encoding`` will be searched for in the first ten
    lines of the template file. If it exists, the ``special-encoding``
    will be used as an encoding and the ``#
    encoding:special-encoding`` line will be stripped from the
    template.

    Different templating engine may be used to render the template
    file. It defaults to ``legacy`` that is compatible with Python's
    :class:`string.Template` class. However, another default may be
    provided using the *default_templating* argument. In any case, a
    line looking like ``# vortex-templating:kind`` will be searched
    for in the first ten lines of the template file. If it exists, the
    ``kind`` templating engine will be used and the ``#
    vortex-templating:kind`` line will be stripped.

    Currently, only few templating engines are supported:

    * ``legacy``: see :class:`LegacyTemplatingAdapter`
    * ``twopasslegacy``: see :class:`TwoPassLegacyTemplatingAdapter`
    * ``jinja2``: see :class:`Jinja2TemplatingAdapter`
    """
    tplpath = Path(tplpath).absolute()
    if not tplpath.exists():
        msg = f"Template file {tplpath} not found"
        raise FileNotFoundError(msg)
    ignored_lines = set()
    actual_encoding = None if encoding == "script" else encoding
    actual_templating = default_templating
    # To determine the encoding & templating open the file with the default
    # encoding (ignoring decoding errors) and look for comments
    with open(tplpath, errors="replace") as tpfld_tmp:
        if encoding is None:
            actual_encoding = tpfld_tmp.encoding
        # Only inspect the first 10 lines
        for iline, line in enumerate(itertools.islice(tpfld_tmp, 10)):
            # Encoding
            if encoding == "script":
                encoding_match = _RE_ENCODING.match(line)
                if encoding_match:
                    ignored_lines.add(iline)
                    actual_encoding = encoding_match.group(1)
            # Templating
            templating_match = _RE_TEMPLATING.match(line)
            if templating_match:
                ignored_lines.add(iline)
                actual_templating = templating_match.group(1)
    # Read the template and delete the encoding line if present
    logger.debug("Opening %s with encoding %s", tplpath, str(actual_encoding))
    with open(tplpath, encoding=actual_encoding) as tpfld:
        tpl_txt = "".join(
            [l for (i, l) in enumerate(tpfld) if i not in ignored_lines]
        )

    try:
        template_rendering_cls = _TEMPLATE_RENDERING_CLASSES[actual_templating]
    except KeyError:
        msg = (
            f"Unknown templating systes < {actual_templating} >"
            f"when trying to load template {tplpath}"
        )
        logger.error(msg)

    return template_rendering_cls(
        tpl_txt,
        tplpath,
        actual_encoding,
    )


class GenericReadOnlyConfigParser:
    """A Basic ReadOnly configuration file parser.

    It relies on a :class:`ConfigParser.ConfigParser` parser (or another class
    that satisfies the interface) to access the configuration data.

    :param str inifile: Path to a configuration file or a configuration file name
        (see the :meth:`setfile` method for more details)
    :param ConfigParser.ConfigParser parser: an existing configuration parser
        object the will be used to access the configuration
    :param bool mkforce: If the configuration file doesn't exists. Create an empty
        one in ``~/.vortexrc``
    :param type clsparser: The class that will be used to create a parser object
        (if needed)
    :param str encoding: The configuration file encoding
    :param str defaultinifile: The name of a default ini file (read before,
         and possibly overwritten by **inifile**)

    :note: Some of the parser's methods are directly accessible because ``__getattr__``
        is implemented. For this ReadOnly class, only methods ``defaults``,
        ``sections``, ``options``, ``items``, ``has_section`` and ``has_option``
        are accessible. The user will refer to the Python's ConfigParser module
        documentation for more details.
    """

    _RE_AUTO_SETFILE = re.compile(r"^@([^/]+\.ini)$")

    def __init__(
        self,
        inifile=None,
        parser=None,
        mkforce=False,
        clsparser=_DEFAULT_CONFIG_PARSER,
        encoding=None,
        defaultinifile=None,
    ):
        self.parser = parser
        self.mkforce = mkforce
        self.clsparser = clsparser
        self.defaultencoding = encoding
        self.defaultinifile = defaultinifile
        if inifile:
            self.setfile(inifile, encoding=None)
        else:
            self.file = None

    def __deepcopy__(self, memo):
        """Warning: deepcopy of any item of the class is... itself!"""
        memo[id(self)] = self
        return self

    def as_dump(self):
        """Return a nicely formated class name for dump in footprint."""
        return "file={!s}".format(self.file)

    def setfile(self, inifile, encoding=None):
        """Read the specified **inifile** as new configuration.

        **inifile** may be:

        * A File like object
        * A path to a file
        * A file name preceded by '@'

        In the latter case, the configuration file is looked for both in
        ``~/.vortexrc`` and in the ``conf`` directory of the vortex installation.
        If a section/option is  defined in ``~/.vortexrc`` it takes precedence
        over the one defined in ``conf``.

        :example:

        Let's consider the following declaration in ``conf``::

            [mysection]
            var1=Toto
            var2=Titi

        Let's consider the following declaration in ``~/.vortexrc``::

            [mysection]
            var1=Personalised

        A call to ``get('mysection', 'var1')`` will return ``Personalised`` and a
        call to ``get('mysection', 'var2')`` will return ``Titi``.
        """
        if self.parser is None:
            self.parser = self.clsparser()
        if encoding is None:
            encoding = self.defaultencoding
        self.file = None
        filestack = list()
        local = sessions.system()
        glove = sessions.current().glove
        if not isinstance(inifile, str):
            if self.defaultinifile:
                sitedefaultinifile = glove.siteconf + "/" + self.defaultinifile
                if local.path.exists(sitedefaultinifile):
                    with open(sitedefaultinifile, encoding=encoding) as a_fh:
                        self.parser.read_file(a_fh)
                else:
                    raise ValueError(
                        "Configuration file "
                        + sitedefaultinifile
                        + " not found"
                    )
            # Assume it's an IO descriptor
            inifile.seek(0)
            self.parser.read_file(inifile)
            self.file = repr(inifile)
            if self.defaultinifile:
                self.file = sitedefaultinifile + "," + self.file
        else:
            # Let's continue as usual
            autofile = self._RE_AUTO_SETFILE.match(inifile)
            if not autofile:
                if local.path.exists(inifile):
                    filestack.append(local.path.abspath(inifile))
                else:
                    raise ValueError(
                        "Configuration file " + inifile + " not found"
                    )
            else:
                autofile = autofile.group(1)
                sitefile = glove.siteconf + "/" + autofile
                persofile = glove.configrc + "/" + autofile
                if local.path.exists(sitefile):
                    filestack.append(sitefile)
                if local.path.exists(persofile):
                    filestack.append(persofile)
                if not filestack:
                    if self.mkforce:
                        filestack.append(persofile)
                        local.filecocoon(persofile)
                        local.touch(persofile)
                    else:
                        raise ValueError(
                            "Configuration file " + inifile + " not found"
                        )
            if self.defaultinifile:
                sitedefaultinifile = glove.siteconf + "/" + self.defaultinifile
                if local.path.exists(sitedefaultinifile):
                    # Insert at the beginning (i.e. smallest priority)
                    filestack.insert(0, local.path.abspath(sitedefaultinifile))
                else:
                    raise ValueError(
                        "Configuration file "
                        + sitedefaultinifile
                        + " not found"
                    )
            self.file = ",".join(filestack)
            for a_file in filestack:
                with open(a_file, encoding=encoding) as a_fh:
                    self.parser.read_file(a_fh)

    def as_dict(self, merged=True):
        """Export the configuration file as a dictionary."""
        if merged:
            dico = dict()
        else:
            dico = dict(defaults=dict(self.defaults()))
        for section in self.sections():
            if merged:
                dico[section] = dict(self.items(section))
            else:
                dico[section] = {
                    k: v
                    for k, v in self.items(section)
                    if k in self.parser._sections[section]
                }
        return dico

    def __getattr__(self, attr):
        # Give access to a very limited set of methods
        if attr.startswith("get") or attr in (
            "defaults",
            "sections",
            "options",
            "items",
            "has_section",
            "has_option",
        ):
            return getattr(self.parser, attr)
        else:
            raise AttributeError(
                self.__class__.__name__
                + " instance has no attribute '"
                + str(attr)
                + "'"
            )

    def footprint_export(self):
        return self.file


class ExtendedReadOnlyConfigParser(GenericReadOnlyConfigParser):
    """A ReadOnly configuration file parser with a nice inheritance feature.

    Using this readonly configuration parser, a section can inherit from one or
    several other sections. The basic interpolation (with the usual ``%(varname)s``
    syntax) is available.

    It relies on a :class:`ConfigParser.ConfigParser` parser (or another class
    that satisfies the interface) to access the configuration data.

    :param str inifile: Path to a configuration file or a configuration file name
    :param ConfigParser.ConfigParser parser: an existing configuration parser
        object the will be used to access the configuration
    :param bool mkforce: If the configuration file doesn't exists. Create an empty
        one in ``~/.vortexrc``
    :param type clsparser: The class that will be used to create a parser object
        (if needed)

    :example: Here is an example using the inheritance mechanism. Let's consider
        the following section declaration::

            [newsection:base1:base2]
            var1=...

        ``newsection`` will inherit the variables contained in sections ``base1``
        and ``base2``. In case of a conflict, ``base1`` takes precedence over ``base2``.
    """

    _RE_VALIDATE = re.compile(r"([\w-]+)[ \t]*:?")
    _RE_KEYC = re.compile(r"%\(([^)]+)\)s")

    _max_interpolation_depth = 20

    def _get_section_list(self, zend_section):
        """
        Return the stack of sections that will be used to look for a given
        variable. Somehow, it is close to python's MRO.
        """
        found_sections = []
        if self.parser.has_section(zend_section):
            found_sections.append(zend_section)
        for section in self.parser.sections():
            pieces = re.split(r"[ \t]*:[ \t]*", section)
            if len(pieces) >= 2 and pieces[0] == zend_section:
                found_sections.append(section)
                for inherited in pieces[1:]:
                    found_sections.extend(self._get_section_list(inherited))
                break
        return found_sections

    def _interpolate(self, section, rawval):
        """Performs the basic interpolation."""
        value = rawval
        depth = self._max_interpolation_depth

        def _interpolation_replace(match):
            s = match.group(1)
            return self.get(section, self.parser.optionxform(s), raw=False)

        while depth:  # Loop through this until it's done
            depth -= 1
            if value and self._RE_KEYC.match(value):
                value = self._RE_KEYC.sub(_interpolation_replace, value)
            else:
                break
        if value and self._RE_KEYC.match(value):
            raise InterpolationDepthError(
                self.options(section), section, rawval
            )
        return value

    def get(self, section, option, raw=False, myvars=None):
        """Behaves like the GenericConfigParser's ``get`` method."""
        expanded = [
            s for s in self._get_section_list(section) if s is not None
        ]
        if not expanded:
            raise NoSectionError(section)
        expanded.reverse()
        acc_result = None
        acc_except = None
        mydefault = self.defaults().get(option, None)
        for isection in expanded:
            try:
                tmp_result = self.parser.get(
                    isection, option, raw=True, vars=myvars
                )
                if tmp_result is not mydefault:
                    acc_result = tmp_result
            except NoOptionError as err:
                acc_except = err
        if acc_result is None and mydefault is not None:
            acc_result = mydefault
        if acc_result is not None:
            if not raw:
                acc_result = self._interpolate(section, acc_result)
            return acc_result
        else:
            raise acc_except

    def sections(self):
        """Behaves like the Python ConfigParser's ``section`` method."""
        seen = set()
        for section_m in [
            self._RE_VALIDATE.match(s) for s in self.parser.sections()
        ]:
            if section_m is not None:
                seen.add(section_m.group(1))
        return list(seen)

    def has_section(self, section):
        """Return whether a section exists or not."""
        return section in self.sections()

    def options(self, section):
        """Behaves like the Python ConfigParser's ``options`` method."""
        expanded = self._get_section_list(section)
        if not expanded:
            return self.parser.options(
                section
            )  # A realistic exception will be thrown !
        options = set()
        for isection in [s for s in expanded]:
            options.update(set(self.parser.options(isection)))
        return list(options)

    def has_option(self, section, option):
        """Return whether an option exists or not."""
        return option in self.options(section)

    def items(self, section, raw=False, myvars=None):
        """Behaves like the Python ConfigParser's ``items`` method."""
        return [
            (o, self.get(section, o, raw, myvars))
            for o in self.options(section)
        ]

    def __getattr__(self, attr):
        # Give access to a very limited set of methods
        if attr in ("defaults",):
            return getattr(self.parser, attr)
        else:
            raise AttributeError(
                self.__class__.__name__
                + " instance has no attribute '"
                + str(attr)
                + "'"
            )

    def as_dict(self, merged=True):
        """Export the configuration file as a dictionary."""
        if not merged:
            raise ValueError(
                "merged=False is not allowed with ExtendedReadOnlyConfigParser."
            )
        return super().as_dict(merged=True)


class GenericConfigParser(GenericReadOnlyConfigParser):
    """A Basic Read/Write configuration file parser.

    It relies on a :class:`ConfigParser.ConfigParser` parser (or another class
    that satisfies the interface) to access the configuration data.

    :param str inifile: Path to a configuration file or a configuration file name
    :param ConfigParser.ConfigParser parser: an existing configuration parser
        object the will be used to access the configuration
    :param bool mkforce: If the configuration file doesn't exists. Create an empty
        one in ``~/.vortexrc``
    :param type clsparser: The class that will be used to create a parser object
        (if needed)
    :param str encoding: The configuration file encoding
    :param str defaultinifile: The name of a default ini file (read before,
         and possibly overwritten by **inifile**)

    :note: All of the parser's methods are directly accessible because ``__getattr__``
        is implemented. The user will refer to the Python's ConfigParser module
        documentation for more details.
    """

    def __init__(
        self,
        inifile=None,
        parser=None,
        mkforce=False,
        clsparser=_DEFAULT_CONFIG_PARSER,
        encoding=None,
        defaultinifile=None,
    ):
        super().__init__(
            inifile, parser, mkforce, clsparser, encoding, defaultinifile
        )
        self.updates = list()

    def setall(self, kw):
        """Define in all sections the couples of ( key, values ) given as dictionary argument."""
        self.updates.append(kw)
        for section in self.sections():
            for key, value in kw.items():
                self.set(section, key, str(value))

    def save(self):
        """Write the current state of the configuration in the inital file."""
        with open(self.file.split(",").pop(), "wb") as configfile:
            self.write(configfile)

    @property
    def updated(self):
        """Return if this configuration has been updated or not."""
        return bool(self.updates)

    def history(self):
        """Return a list of the description for each update performed."""
        return self.updates[:]

    def __getattr__(self, attr):
        # Give access to all of the parser's methods
        if attr.startswith("__"):
            raise AttributeError(
                self.__class__.__name__
                + " instance has no attribute '"
                + str(attr)
                + "'"
            )
        return getattr(self.parser, attr)


class DelayedConfigParser(GenericConfigParser):
    """Configuration file parser with possible delayed loading.

    :param str inifile: Path to a configuration file or a configuration file name

    :note: All of the parser's methods are directly accessible because ``__getattr__``
        is implemented. The user will refer to the Python's ConfigParser module
        documentation for more details.
    """

    def __init__(self, inifile=None):
        GenericConfigParser.__init__(self)
        self.delay = inifile

    def refresh(self):
        """Load the delayed inifile."""
        if self.delay:
            self.setfile(self.delay)
            self.delay = None

    def __getattribute__(self, attr):
        try:
            logger.debug("Getattr %s < %s >", attr, self)
            if attr in filter(
                lambda x: not x.startswith("_"),
                dir(_DEFAULT_CONFIG_PARSER) + ["setall", "save"],
            ):
                object.__getattribute__(self, "refresh")()
        except Exception:
            logger.critical("Trouble getattr %s < %s >", attr, self)
        return object.__getattribute__(self, attr)


class JacketConfigParser(GenericConfigParser):
    """Configuration parser for Jacket files.

    :param str inifile: Path to a configuration file or a configuration file name
    :param ConfigParser.ConfigParser parser: an existing configuration parser
        object the will be used to access the configuration
    :param bool mkforce: If the configuration file doesn't exists. Create an empty
        one in ``~/.vortexrc``
    :param type clsparser: The class that will be used to create a parser object
        (if needed)

    :note: All of the parser's methods are directly accessible because ``__getattr__``
        is implemented. The user will refer to the Python's ConfigParser module
        documentation for more details.
    """

    def get(self, section, option):
        """
        Return for the specified ``option`` in the ``section`` a sequence of values
        build on the basis of a comma separated list.
        """
        s = _DEFAULT_CONFIG_PARSER.get(self, section, option)
        tmplist = s.replace(" ", "").split(",")
        if len(tmplist) > 1:
            return tmplist
        else:
            return tmplist[0]


class AppConfigStringDecoder(StringDecoder):
    """Convert a string from a configuration file into a proper Python's object.

    See the :class:`StringDecoder` class documentation for a complete description
    the configuration string's syntax.

    This class extends the :class:`StringDecoder` as follow:

    * It's possible to convert (i.e. remap) configuration lines to Vortex's
      geometries: ``geometry(geo_tagname)``
    * The :func:`footprints.util.rangex` can be called to generate a list:
      ``dict(production:rangex(0-6-1) assim:rangex(0-3-1))`` will generate
      the following object ``{u'assim': [0, 1, 2, 3], u'production': [0, 1, 2, 3, 4, 5, 6]}``
    * It is possible to create an object using the *iniconf* footprint's collector:
      ``'iniconf(family:pollutants kind:elements version:std)'`` will generate
      the following object ``<intairpol.data.elements.PollutantsElementsTable at 0x...>``
      (provided that the :mod:`intairpol` package has been imported).
    * It is possible to create an object using the *conftools* footprint's collector
      (following the previous example's syntax).

    """

    BUILDERS = StringDecoder.BUILDERS + [
        "geometry",
        "date",
        "time",
        "rangex",
        "daterangex",
        "iniconf",
        "conftool",
    ]

    def remap_geometry(self, value):
        """Convert all values to Geometry objects."""
        from vortex.data import geometries

        try:
            value = geometries.get(tag=value)
        except ValueError:
            pass
        return value

    def remap_date(self, value):
        """Convert all values to bronx' Date objects."""
        try:
            value = bdate.Date(value)
        except (ValueError, TypeError):
            pass
        return value

    def remap_time(self, value):
        """Convert all values to bronx' Time objects."""
        try:
            value = bdate.Time(value)
        except (ValueError, TypeError):
            pass
        return value

    def _build_geometry(self, value, remap, subs):
        val = self._value_expand(value, remap, subs)
        from vortex.data import geometries

        return geometries.get(tag=val)

    def _build_date(self, value, remap, subs):
        val = self._value_expand(value, remap, subs)
        return bdate.Date(val)

    def _build_time(self, value, remap, subs):
        val = self._value_expand(value, remap, subs)
        return bdate.Time(val)

    def _build_generic_rangex(self, cb, value, remap, subs):
        """Build a rangex or daterangex from the **value** string."""
        # Try to read names arguments
        try:
            values = self._sparser(value, itemsep=" ", keysep=":")
            if all(
                [
                    k in ("start", "end", "step", "shift", "fmt", "prefix")
                    for k in values.keys()
                ]
            ):
                return cb(
                    **{
                        k: self._value_expand(v, remap, subs)
                        for k, v in values.items()
                    }
                )
        except StringDecoderSyntaxError:
            pass
        # The usual case...
        return cb(
            [
                self._value_expand(v, remap, subs)
                for v in self._sparser(value, itemsep=",")
            ]
        )

    def _build_rangex(self, value, remap, subs):
        """Build a rangex from the **value** string."""
        return self._build_generic_rangex(
            bdate.timeintrangex, value, remap, subs
        )

    def _build_daterangex(self, value, remap, subs):
        """Build a daterangex from the **value** string."""
        return self._build_generic_rangex(bdate.daterangex, value, remap, subs)

    def _build_fpgeneric(self, value, remap, subs, collector):
        fp = {
            k: self._value_expand(v, remap, subs)
            for k, v in self._sparser(value, itemsep=" ", keysep=":").items()
        }
        obj = footprints.collectors.get(tag=collector).load(**fp)
        if obj is None:
            raise StringDecoderSyntaxError(
                value,
                "No object could be created from the {} collector".format(
                    collector
                ),
            )
        return obj

    def _build_iniconf(self, value, remap, subs):
        return self._build_fpgeneric(value, remap, subs, "iniconf")

    def _build_conftool(self, value, remap, subs):
        return self._build_fpgeneric(value, remap, subs, "conftool")


class IniConf(footprints.FootprintBase):
    """
    Generic Python configuration file.
    """

    _collector = ("iniconf",)
    _abstract = True
    _footprint = dict(
        info="Abstract Python Inifile",
        attr=dict(
            kind=dict(
                info="The configuration object kind.",
                values=[
                    "generic",
                ],
            ),
            clsconfig=dict(
                type=GenericReadOnlyConfigParser,
                isclass=True,
                optional=True,
                default=GenericReadOnlyConfigParser,
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
            inifile=dict(
                kind="The configuration file to look for.",
                optional=True,
                default="@[kind].ini",
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug("Ini Conf %s", self.__class__)
        super().__init__(*args, **kw)
        self._config = self.clsconfig(inifile=self.inifile)

    @property
    def config(self):
        return self._config


class ConfigurationTable(IniConf):
    """
    A specialised version of :class:`IniConf` that automatically create a list of
    items (instantiated from the tableitem footprint's collector) from a given
    configuration file.
    """

    _abstract = True
    _footprint = dict(
        info="Abstract configuration tables",
        attr=dict(
            kind=dict(
                info="The configuration's table kind.",
            ),
            family=dict(
                info="The configuration's table family.",
            ),
            version=dict(
                info="The configuration's table version.",
                optional=True,
                default="std",
            ),
            searchkeys=dict(
                info="Item's attributes used to perform the lookup in the find method.",
                type=footprints.FPTuple,
                optional=True,
                default=footprints.FPTuple(),
            ),
            groupname=dict(
                info="The class attribute matching the configuration file groupname",
                optional=True,
                default="family",
            ),
            inifile=dict(
                optional=True,
                default="@[family]-[kind]-[version].ini",
            ),
            clsconfig=dict(
                default=ExtendedReadOnlyConfigParser,
            ),
            language=dict(
                info="The default language for the translator property.",
                optional=True,
                default="en",
            ),
        ),
    )

    @property
    def realkind(self):
        return "configuration-table"

    def groups(self):
        """Actual list of items groups described in the current iniconf."""
        return [
            x
            for x in self.config.parser.sections()
            if ":" not in x and not x.startswith("lang_")
        ]

    def keys(self):
        """Actual list of different items in the current iniconf."""
        return [
            x
            for x in self.config.sections()
            if x not in self.groups() and not x.startswith("lang_")
        ]

    @property
    def translator(self):
        """The special section of the iniconf dedicated to translation, as a dict."""
        if not hasattr(self, "_translator"):
            if self.config.has_section("lang_" + self.language):
                self._translator = self.config.as_dict()[
                    "lang_" + self.language
                ]
            else:
                self._translator = None
        return self._translator

    @property
    def tablelist(self):
        """List of unique instances of items described in the current iniconf."""
        if not hasattr(self, "_tablelist"):
            self._tablelist = list()
            d = self.config.as_dict()
            for item, group in [
                x.split(":") for x in self.config.parser.sections() if ":" in x
            ]:
                try:
                    for k, v in d[item].items():
                        # Can occur in case of a redundant entry in the config file
                        if isinstance(v, str) and v:
                            if re.match("none$", v, re.IGNORECASE):
                                d[item][k] = None
                            if re.search("[a-z]_[a-z]", v, re.IGNORECASE):
                                d[item][k] = v.replace("_", "'")
                    d[item][self.searchkeys[0]] = item
                    d[item][self.groupname] = group
                    d[item]["translator"] = self.translator
                    itemobj = footprints.proxy.tableitem(**d[item])
                    if itemobj is not None:
                        self._tablelist.append(itemobj)
                    else:
                        logger.error(
                            "Unable to create the %s item object. Check the footprint !",
                            item,
                        )
                except (KeyError, IndexError):
                    logger.warning("Some item description could not match")
        return self._tablelist

    def get(self, item):
        """Return the item with main key exactly matching the given argument."""
        candidates = [
            x
            for x in self.tablelist
            if x.footprint_getattr(self.searchkeys[0]) == item
        ]
        if candidates:
            return candidates[0]
        else:
            return None

    def match(self, item):
        """Return the item with main key matching the given argument without case consideration."""
        candidates = [
            x
            for x in self.tablelist
            if x.footprint_getattr(self.searchkeys[0])
            .lower()
            .startswith(item.lower())
        ]
        if candidates:
            return candidates[0]
        else:
            return None

    def grep(self, item):
        """Return a list of items with main key loosely matching the given argument."""
        return [
            x
            for x in self.tablelist
            if re.search(
                item, x.footprint_getattr(self.searchkeys[0]), re.IGNORECASE
            )
        ]

    def find(self, item):
        """Return a list of items with main key or name loosely matching the given argument."""
        return [
            x
            for x in self.tablelist
            if any(
                [
                    re.search(
                        item, x.footprint_getattr(thiskey), re.IGNORECASE
                    )
                    for thiskey in self.searchkeys
                ]
            )
        ]


class TableItem(footprints.FootprintBase):
    """
    Abstract configuration table's item.
    """

    #: Attribute describing the item's name during RST exports
    _RST_NAME = ""
    #: Attributes that will appear on the top line of RST exports
    _RST_HOTKEYS = []

    _abstract = True
    _collector = ("tableitem",)
    _footprint = dict(
        info="Abstract configuration table's item.",
        attr=dict(
            # Define your own...
            translator=dict(
                optional=True,
                type=footprints.FPDict,
                default=None,
            ),
        ),
    )

    @property
    def realkind(self):
        return "tableitem"

    def _translated_items(self, mkshort=True):
        """Returns a list of 3-elements tuples describing the item attributes.

        [(translated_key, value, original_key), ...]
        """
        output_stack = list()
        if self.translator:
            for k in self.translator.get("ordered_dump", "").split(","):
                if not mkshort or self.footprint_getattr(k) is not None:
                    output_stack.append(
                        (
                            self.translator.get(
                                k, k.replace("_", " ").title()
                            ),
                            str(self.footprint_getattr(k)),
                            k,
                        )
                    )
        else:
            for k in self.footprint_attributes:
                if (
                    not mkshort or self.footprint_getattr(k) is not None
                ) and k != "translator":
                    output_stack.append((k, str(self.footprint_getattr(k)), k))
        return output_stack

    def nice_str(self, mkshort=True):
        """Produces a nice ordered representation of the item attributes."""
        output_stack = self._translated_items(mkshort=mkshort)
        output_list = []
        if output_stack:
            max_keylen = max([len(i[0]) for i in output_stack])
            print_fmt = "{0:" + str(max_keylen) + "s} : {1:s}"
            for item in output_stack:
                output_list.append(print_fmt.format(*item))
        return "\n".join(output_list)

    def __str__(self):
        return self.nice_str()

    def nice_print(self, mkshort=True):
        """Print a nice ordered output of the item attributes."""
        print(self.nice_str(mkshort=mkshort))

    def nice_rst(self, mkshort=True):
        """Produces a nice ordered RST output of the item attributes."""
        assert self._RST_NAME, "Please override _RST_NAME"
        output_stack = self._translated_items(mkshort=mkshort)
        i_name = "????"
        i_hot = []
        i_other = []
        for item in output_stack:
            if item[2] == self._RST_NAME:
                i_name = item
            elif item[2] in self._RST_HOTKEYS:
                i_hot.append(item)
            else:
                i_other.append(item)
        return "**{}** : `{}`\n\n{}\n\n".format(
            i_name[1],
            ", ".join(["{:s}={:s}".format(*i) for i in i_hot]),
            "\n".join(["    * {:s}: {:s}".format(*i) for i in i_other]),
        )
