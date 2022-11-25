{% extends "jobs_rd/job-ecmwfsequana1-mtool-base.tpl" %}
# vortex-templating: jinja2
# encoding: utf-8

{% block mtool_steps_setup %}
#MTOOL set transfer=[this:frontend]
{%- endblock %}

{% block mtool_last_id %}transfer{% endblock %}

{% block ja_mtool_steps %}ja.mtool_steps if not (rd_warmstart or rd_refill) else (){% endblock %}

{% block mtool_steps_create %}
#MTOOL step id=transfer target=[this:transfer]
{%- endblock %}