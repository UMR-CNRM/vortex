{% extends "jobs_rd/job-generic-mtool-base.tpl" %}

{% block mtool_prof %}
#MTOOL profile target={{target}}cn
#SBATCH --export=NONE
#SBATCH --job-name={{name}}
#SBATCH --mem={{mem}}
#SBATCH --nodes={{nnodes}}
{% if qos != 'np' -%}
#SBATCH --ntasks-per-node={{ntasks}}
#SBATCH --cpus-per-task={{openmp}}
{% endif -%}
#SBATCH --qos={{qos}}
#SBATCH --time={{time}}
#SBATCH --{{verbose}}
{% if billing_account is defined and billing_account -%}
#SBATCH --account={{billing_account}}
{% endif -%}
#MTOOL end
{% if billing_account_ft is defined and billing_account_ft -%}
#MTOOL extendprofile target={{target}}fe
#SBATCH --account={{billing_account_ft}}
#MTOOL end
{% endif -%}
{%- if billing_account_log is defined and billing_account_log -%}
#MTOOL extendprofile target={{target}}fe tag=autolog
#SBATCH --account={{billing_account_log}}
#MTOOL end
{% endif -%}
{%- endblock -%}