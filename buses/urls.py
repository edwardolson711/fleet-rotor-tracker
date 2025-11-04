from django.urls import path

from . import views

urlpatterns = [
    path("buses/<int:bus_id>/add-rotors/", views.add_rotors, name="add_rotors"),
]
