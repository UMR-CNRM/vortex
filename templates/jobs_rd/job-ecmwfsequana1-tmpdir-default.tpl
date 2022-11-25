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
#SBATCH --qos={{qos}}
#SBATCH --time={{time}}
#SBATCH --{{verbose}}
#SBATCH --output={{pwd}}/../logs/{{file}}.%j
{%- endblock job_header %}
