{% extends "job-generic-tmpdir-base.tpl" %}
# vortex-templating: jinja2
# encoding: utf-8

{%- block job_header -%}
{{ super() }}
#SBATCH --cpus-per-task={{openmp}}
#SBATCH --export=NONE
#SBATCH --job-name={{name}}
#SBATCH --mem={{mem}}
#SBATCH --nodes={{nnodes}}
#SBATCH --ntasks-per-node={{ntasks}}
#SBATCH --partition={{partition}}
#SBATCH --time={{time}}
{% if exclusive is defined and exclusive -%}
#SBATCH --{{exclusive}}
{% endif -%}
#SBATCH --{{verbose}}
#SBATCH --output={{pwd}}/../logs/{{file}}.%j
{% if billing_account is defined and billing_account -%}
#SBATCH --account={{billing_account}}
{% endif -%}
{%- endblock job_header %}
