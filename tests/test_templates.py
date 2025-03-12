from pathlib import Path

import pytest

from vortex.util.config import load_template

TEST_TPL_DIR = Path(__file__).parent.absolute() / "test_templates"


def test_load_template():
    with pytest.raises(FileNotFoundError):
        tpl = load_template(tplpath=Path("/a/b/c/d"))

    tplpath = TEST_TPL_DIR / "test.tpl"
    tpl = load_template(
        tplpath=tplpath,
        encoding=None,
        default_templating="legacy",
    )
    assert tpl.srcfile == str(tplpath)


def test_load_template_encoding():
    tplpath = TEST_TPL_DIR / "test_with_encoding.tpl"
    tpl = load_template(
        tplpath=tplpath,
        encoding="script",
        default_templating="legacy",
    )
    assert tpl.srcfile == str(tplpath)


def test_load_jinja2_template():
    tplpath = TEST_TPL_DIR / "test_jinja2.tpl"
    tpl = load_template(
        tplpath=tplpath,
        encoding=None,
        default_templating="jinja2",
    )
    assert tpl.srcfile == str(tplpath)
