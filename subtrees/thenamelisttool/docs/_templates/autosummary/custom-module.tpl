{{ fullname | escape | underline}}

.. automodule:: {{ fullname }}

{% block attributes %}
{% if attributes %}

{{ _('Module Attributes') | underline('-')  }}

{% for item in attributes %}

.. autodata:: {{ item }}
   :noindex:
{%- endfor %}
{% endif %}
{% endblock %}

{% block functions %}
{% if functions %}

{{ _('Functions') | underline('-')  }}
{% for item in functions %}

.. autofunction:: {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}

{% block classes %}
{% if classes %}

{{ _('Classes') | underline('-') }}
{% for item in classes %}

.. autoclass:: {{ item }}
   :show-inheritance:
   :members:
   :member-order: alphabetical
   {%- endfor %}
   {% endif %}
   {% endblock %}

{% block exceptions %}
{% if exceptions %}

{{ _('Exceptions') | underline('-')  }}
{% for item in exceptions %}

.. autoexception:: {{ item }}
   :show-inheritance:
   :members:
   :member-order: alphabetical
{%- endfor %}
{% endif %}
{% endblock %}

{% block modules %}
{% if modules %}
Sub-Modules
-----------

.. autosummary::
   :toctree:
   :template: autosummary/custom-module.tpl
   :recursive:
{% for item in modules %}
   {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
