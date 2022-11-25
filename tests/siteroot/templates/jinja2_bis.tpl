# vortex-templating:jinja2
# encoding:utf-8
{% extends "jinja2_base.tpl" %}
{% block linedisp %}{{ "%02d" | format(ivar) }}{% endblock %}
{% block vardisp %}{{ var | lower }}{% endblock %}