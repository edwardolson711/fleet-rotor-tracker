from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def rotor_field(label: str) -> str:
    return label.lower().replace("-", "_").replace(" ", "_")
