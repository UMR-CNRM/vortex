{% extends "job-generic-base.tpl" %}

{%- block job_header -%}
#!${python} $pyopts
{%- endblock job_header %}

{% block ja_extra_plugins -%}
ja.add_plugin('tmpdir')
{%- endblock %}