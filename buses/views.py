from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict

from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Bus, RotorMeasurement
from .services import (
    build_fleet_snapshot,
    get_lowest_rotor_summary,
    get_rotor_positions,
    initialize_rotors,
)


def home(request: HttpRequest) -> HttpResponse:
    buses = (
        Bus.objects.prefetch_related(
            Prefetch(
                "rotor_measurements",
                queryset=RotorMeasurement.objects.order_by(
                    "position", "measurement_date", "id"
                ),
            )
        )
        .all()
        .order_by("bus_number")
    )
    return render(
        request,
        "home.html",
        {
            "buses": [
                {
                    "id": bus.id,
                    "bus_number": bus.bus_number,
                    "bus_type": bus.bus_type,
                    "location": bus.location,
                    "current_mileage": bus.current_mileage,
                    "lowest_rotor": get_lowest_rotor_summary(bus),
                }
                for bus in buses
            ]
        },
    )


def maintenance(request: HttpRequest) -> HttpResponse:
    fleet_data = build_fleet_snapshot()
    return render(
        request,
        "maintenance.html",
        {
            "fleet_data": fleet_data,
        },
    )


def add_rotors(request: HttpRequest, bus_id: int) -> HttpResponse:
    bus = get_object_or_404(Bus, pk=bus_id)
    positions = get_rotor_positions(bus)

    last_measurements: Dict[str, Decimal] = {}
    for position in positions:
        measurement = (
            bus.rotor_measurements.filter(position=position)
            .order_by("-measurement_date", "-id")
            .first()
        )
        if measurement:
            last_measurements[position] = measurement.thickness_mm

    if request.method == "POST":
        measurement_date_raw = request.POST.get("measurement_date")
        mileage_raw = request.POST.get("mileage")
        measurement_date = (
            date.fromisoformat(measurement_date_raw)
            if measurement_date_raw
            else timezone.now().date()
        )
        mileage = int(mileage_raw) if mileage_raw else bus.current_mileage
        bus.current_mileage = max(bus.current_mileage, mileage)
        bus.save(update_fields=["current_mileage"])

        created = False
        for position in positions:
            field_name = f"thickness_{position.lower().replace('-', '_').replace(' ', '_')}"
            thickness_value = request.POST.get(field_name)
            if not thickness_value:
                continue
            thickness = Decimal(thickness_value)
            RotorMeasurement.objects.create(
                bus=bus,
                position=position,
                measurement_date=measurement_date,
                mileage_at_measurement=mileage,
                thickness_mm=thickness,
            )
            created = True

        if created:
            return redirect(reverse("maintenance") + f"#bus-{bus.id}")

    return render(
        request,
        "add_rotors.html",
        {
            "bus": bus,
            "positions": positions,
            "today": timezone.now().date(),
            "last_measurements": last_measurements,
        },
    )


def new_rotors_view(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("maintenance")

    bus_id = request.POST.get("bus_id")
    bus = get_object_or_404(Bus, pk=bus_id)
    initialize_rotors(bus)
    return redirect(reverse("maintenance") + f"#bus-{bus.id}")
