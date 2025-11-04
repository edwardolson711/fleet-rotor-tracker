from django.apps import AppConfig


class BusesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'buses'


ROTOR_POSITIONS_STANDARD = (
    'Front-Left',
    'Front-Right',
    'Rear-Left',
    'Rear-Right',
)

ROTOR_POSITIONS_ARTICULATED = (
    'Front-Left',
    'Front-Right',
    'Center-Left',
    'Center-Right',
    'Rear-Left',
    'Rear-Right',
)
