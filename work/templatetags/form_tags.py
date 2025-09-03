from django import template

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css):
    """Thêm class CSS vào widget hiện tại của field."""
    attrs = field.field.widget.attrs
    existing = attrs.get("class", "")
    attrs["class"] = (existing + " " + css).strip()
    return field.as_widget(attrs=attrs)

@register.filter(name="attr")
def attr(field, arg):
    """
    Set tuỳ ý 1 attribute cho widget:  {{ form.username|attr:"placeholder:Nhập tên" }}
    """
    k, v = arg.split(":", 1)
    attrs = field.field.widget.attrs
    attrs[k] = v
    return field.as_widget(attrs=attrs)

