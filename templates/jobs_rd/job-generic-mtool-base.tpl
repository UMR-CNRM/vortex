{% extends "jobs_rd/job-generic-base.tpl" %}

{%- block job_header -%}
#MTOOL set jobname={{name}}
#MTOOL set jobtag=[this:jobname]
{%- block mtool_prof -%}
{%- endblock %}
#MTOOL set host={{target}}
#MTOOL setconf files=targets.[this:host]
#MTOOL set logtarget=[this:frontend]
{%- block mtool_steps_setup -%}
{%- endblock %}

#MTOOL set bangline={{python}}_{{pyopts}}
#MTOOL configure submitcmd={{submitcmd}}
{%- endblock %}

{% block job_core -%}
#MTOOL common not=autolog

{{super()}}
{% endblock %}

{% block ja_extra_plugins -%}
ja.add_plugin('mtool',
              step='[this:number]',
              stepid='[this:id]',
              lastid='{% block mtool_last_id %}{% endblock %}',
              mtoolid='[this:count]')
{%- if j2_ecflow is defined and j2_ecflow %}
ja.add_plugin('flow', backend='ecflow', jobidlabels=True, mtoolmeters=True)
{%- endif %}
{% endblock -%}

{% block ja_setup_extra_args -%}
{% if j2_ecflow is defined and j2_ecflow -%}dict(
        flowscheduler={{ecflow_config_dict() | indent(8)}},
    )
{%- else -%}
dict()
{%- endif -%}
{% endblock %}

{% block driver_opts -%}
    opts = dict(jobassistant=ja,
                steps={% block ja_mtool_steps %}ja.mtool_steps{% endblock %},
                mstep_job_last=ja.is_last)
{% endblock -%}

{% block job_post_rescue -%}
    if ja.subjob_tag is None:
        #MTOOL include files=epilog.step
        #MTOOL include files=submit.last
        pass
{% endblock -%}

{%- block job_footer -%}
{%- block mtool_steps_create -%}
{%- endblock %}

#MTOOL autoclean
#MTOOL autolog
{%- endblock %}
