import json
import pkg_resources


var_attrs = json.loads(pkg_resources.resource_string('common', 'resources/L4_vars_spec.json'))
var_short_name = json.loads(pkg_resources.resource_string('common', 'resources/L4_var_short_name_dict.json'))
