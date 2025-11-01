# grup_yonetimi/templatetags/custom_filters.py

from django import template

# Registry objesini oluşturuyoruz. Django buradan filtreleri okur.
register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Sözlükten dinamik olarak anahtar çekmek için kullanılan filtre.
    Kullanım: {{ my_dictionary|get_item:key_name }}
    """
    return dictionary.get(key)