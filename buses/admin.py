from __future__ import annotations

from django.contrib import admin

from .models import Bus, RotorMeasurement


class RotorMeasurementInline(admin.TabularInline):
    model = RotorMeasurement
    extra = 0
    ordering = ("-measurement_date", "position")


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = (
        "bus_number",
        "bus_type",
        "location",
        "current_mileage",
        "is_articulating",
        "min_rotor_thickness",
    )
    search_fields = ("bus_number", "location", "bus_type")
    list_filter = ("is_articulating", "location")
    inlines = [RotorMeasurementInline]


@admin.register(RotorMeasurement)
class RotorMeasurementAdmin(admin.ModelAdmin):
    list_display = (
        "bus",
        "position",
        "measurement_date",
        "mileage_at_measurement",
        "thickness_mm",
    )
    search_fields = ("bus__bus_number", "position")
    list_filter = ("position", "measurement_date", "bus")
    date_hierarchy = "measurement_date"
    list_select_related = ("bus",)
