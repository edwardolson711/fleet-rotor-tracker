from django.contrib import admin
from django.urls import include, path

from buses.views import home, maintenance, new_rotors_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),                    # Root → home
    path('maintenance/', maintenance, name='maintenance'),
    path('new-rotors/', new_rotors_view, name='new_rotors'),

    # Include buses.urls for add_rotors, etc.
    path('', include('buses.urls')),                # ← MUST BE LAST
]
