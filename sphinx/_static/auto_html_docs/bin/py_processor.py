#!/usr/bin/env python3

'''Convert any bits of document to HTML files.'''

import collections
import logging
import jinja2
import os
import re
import sys

logging.basicConfig()
logger = logging.getLogger(__name__)

tpldir = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                '../templates'
            ));

# Setup jinja2
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(tpldir, encoding='utf-8')
)

bits2slides_tpl = 'reveal_bits2slides.tpl'
bits2html_tpl = 'marked_bits2html.tpl'


class SlideDef(object):

    def __init__(self, stype, sargs):
        self.type = stype
        self.args = sargs
        self.content = ''


class ContentParser(object):

    _RE_HEAD_IGNORE = re.compile(r'(\s*#.*|\s*)$')
    _RE_HEAD_ENTRY = re.compile(r'\s*(?P<key>[\w_-]+)=(?P<value>.*)$')
    _RE_SLIDEDEF = re.compile(r'--\s*(?P<type>ht|md)\s+(?P<sub>(?:sub))?slide\s*(?P<args>.*)$')
    _RE_MDCLEAN = re.compile(r'Notes?:\s*$')
    _HEAD_ENTRIES = ['head_{:s}'.format(s) for s in ('title', 'description', 'author')]

    def __init__(self, mdclean=False):
        self._headers = dict()
        self._slides = list()
        self._mdclean=mdclean

    @property
    def headers(self):
        return self._headers

    @property
    def slides(self):
        return self._slides

    def _flush(self, cur_slide, sep_match):
        newl1 = sep_match and not sep_match.group('sub')
        if (not self._slides) and (not newl1):
            msg = 'The first slide cannot be a sub-slide'
            logger.critical(msg)
            raise RuntimeError(msg)
        if cur_slide:
            cur_slide.content = cur_slide.content.lstrip('\n')
            if cur_slide.content:
                logger.debug('+Slide: type="%s", length=%d, args="%s".',
                    cur_slide.type, len(cur_slide.content), cur_slide.args)
                self._slides[-1].append(cur_slide)
        if newl1:
            logger.debug('Level1: created')
            self._slides.append(list())
        return (SlideDef(sep_match.group('type'), sep_match.group('args'))
                if sep_match else None)

    def __call__(self, ifile):
        logger.debug('< %s > opened: starting file processing.', ifile)
        local_jinja = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(ifile), encoding='utf-8')
        )
        ifile_template = local_jinja.get_template(os.path.basename(ifile))
        ifile_rendered = ifile_template.render()
        header = True
        cur_slide = None
        for iline in ifile_rendered.split('\n'):
            m_sdef = self._RE_SLIDEDEF.match(iline)
            if m_sdef:
                header = False
                cur_slide = self._flush(cur_slide, m_sdef)
                continue
            if header:
                if self._RE_HEAD_IGNORE.match(iline):
                    logger.debug('Ignore: %s', iline)
                else:
                    m_entry = self._RE_HEAD_ENTRY.match(iline)
                    if m_entry:
                        if m_entry.group('key') in self._HEAD_ENTRIES:
                            logger.debug('Header : %s -> %s',
                                         m_entry.group('key'), m_entry.group('value'))
                            self._headers[m_entry.group('key')] = m_entry.group('value')
                        else:
                            logger.error('The %s key is not recognised...', m_entry.group('key'))
                    else:
                        logger.error('Invalid header entry: %s', iline)
            else:
                if cur_slide.type=='md' and self._mdclean and self._RE_MDCLEAN.match(iline):
                    continue
                cur_slide.content += ('\n' + iline)
        if cur_slide:
            self._flush(cur_slide, None)

        logger.info('%d first level slides found.', len(self.slides))
        for i, s in enumerate(self.slides, start=1):
            if len(s) > 1:
                logger.info('Entry #%d has %d subslides.', i, len(s))


def do_content2tpl(tplname, ifile, ofile, reveal, cdn, lang, style,
                   mdclean=False):
    cparser = ContentParser(mdclean=mdclean)
    cparser(ifile)
    template = jinja_env.get_template(tplname)
    rendered = template.render(slides=cparser.slides,
                               revealjs=reveal, cdn=cdn,
                               hljlang=lang, hljstyle=style,
                               **cparser.headers)
    with open(ofile, 'w', encoding='utf-8') as fho:
        fho.write(rendered)


if __name__ == '__main__':

    def _spacelist(line):
        if not line:
            return []
        else:
            return re.split(r'\s+', line)

    from argparse import ArgumentParser
    from argparse import RawDescriptionHelpFormatter

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup the argument parser
    parser = ArgumentParser(description=program_desc,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s].")
    parser.add_argument("--reveal", dest="reveal", action="store",
                        default='reveal.js',
                        help="set reveal.js code location [default: %(default)s].")
    parser.add_argument("--cdn", dest="cdn", action="store",
                        default='cdn',
                        help="subdirectory with the CDN local copy [default: %(default)s].")
    parser.add_argument("--lang", dest="lang", action="store", default=[],
                        type=_spacelist,
                        help="extra languages for highlight [default: %(default)s].")
    parser.add_argument("--style", dest="style", action="store", default='github',
                        help="style for highlight [default: %(default)s].")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--content2slides", dest="content2slides", action="store_true",
                       help="Generates a slideshow starting form generic content.")
    group.add_argument("--content2html", dest="content2html", action="store_true",
                       help="Generates a HTML document starting form generic content.")
    parser.add_argument("input_file", action="store",
                        help="The path to the input file.")
    parser.add_argument("output_file", action="store",
                        help="The path to the output file.")
    args = parser.parse_args()

    # Setup logger verbosity
    logger.setLevel('WARNING')
    if args.verbose:
        if args.verbose >= 2:
            logger.setLevel('DEBUG')
        elif args.verbose >= 1:
            logger.setLevel('INFO')

    # Check the input file
    if not os.path.exists(args.input_file):
        raise OSError('The {:s} does not exists.'.format(args.input_file))

    if args.content2slides:
        do_content2tpl(bits2slides_tpl, args.input_file, args.output_file,
                args.reveal, args.cdn, args.lang, args.style)

    if args.content2html:
        do_content2tpl(bits2html_tpl, args.input_file, args.output_file,
                args.reveal, args.cdn, args.lang, args.style, mdclean=True)

