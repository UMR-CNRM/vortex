{% extends "jobs_rd/job-ecmwfsequana1-mtool-base.tpl" %}
# vortex-templating: jinja2
# encoding: utf-8

{% block mtool_steps_setup %}
#MTOOL set fetch=[this:frontend]
#MTOOL set compute=[this:cpunodes]
#MTOOL set backup=[this:frontend]
{%- endblock %}

{% block mtool_last_id %}backup{% endblock %}

{% block mtool_steps_create %}
#MTOOL step id=fetch target=[this:fetch]
#MTOOL step id=compute target=[this:compute]
#MTOOL step id=backup target=[this:backup]
{%- endblock %}