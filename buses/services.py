from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Sequence

from django.db.models import Prefetch
from django.utils import timezone

from .apps import ROTOR_POSITIONS_ARTICULATED, ROTOR_POSITIONS_STANDARD
from .models import Bus, RotorMeasurement, RotorStats


@dataclass
class BusMaintenanceSnapshot:
    bus: Bus
    rotor_details: List[RotorStats]
    alerts: List[str]


def get_rotor_positions(bus: Bus) -> Sequence[str]:
    return ROTOR_POSITIONS_ARTICULATED if bus.is_articulating else ROTOR_POSITIONS_STANDARD


def _compute_daily_miles(measurements: Sequence[RotorMeasurement]) -> float | None:
    if len(measurements) < 2:
        return None
    first, last = measurements[0], measurements[-1]
    day_span = (last.measurement_date - first.measurement_date).days
    miles_span = last.mileage_at_measurement - first.mileage_at_measurement
    if day_span <= 0 or miles_span <= 0:
        return None
    return miles_span / day_span


def _compute_rotor_stats(bus: Bus, measurements: Sequence[RotorMeasurement]) -> RotorStats:
    if not measurements:
        return RotorStats(
            position="",
            current_thickness=None,
            miles_left=None,
            days_left=None,
            alert=False,
            starting_mileage=None,
            replacement_mileage=None,
            service_life_miles=None,
        )

    first = measurements[0]
    last = measurements[-1]
    position = last.position
    starting_mileage = first.mileage_at_measurement
    starting_thickness = Decimal(first.thickness_mm)
    current_thickness = Decimal(last.thickness_mm)

    miles_driven = last.mileage_at_measurement - starting_mileage
    wear = starting_thickness - current_thickness

    wear_rate = None
    if miles_driven > 0 and wear > 0:
        wear_rate = wear / Decimal(miles_driven)

    replacement_mileage = None
    service_life_miles = None
    miles_left = None

    if wear_rate and wear_rate > 0:
        remaining_thickness = starting_thickness - Decimal(bus.min_rotor_thickness)
        service_life = remaining_thickness / wear_rate
        service_life_miles = max(
            int(service_life.to_integral_value(rounding=ROUND_HALF_UP)),
            0,
        )
        replacement_mileage = starting_mileage + service_life_miles
        miles_left = max(replacement_mileage - bus.current_mileage, 0)

    daily_miles = _compute_daily_miles(measurements)
    days_left = None
    if miles_left is not None and daily_miles:
        days_left = max(int(round(miles_left / daily_miles)), 0)

    alert = False
    if miles_left is not None:
        alert = miles_left <= 5000

    return RotorStats(
        position=position,
        current_thickness=current_thickness,
        miles_left=miles_left,
        days_left=days_left,
        alert=alert,
        starting_mileage=starting_mileage,
        replacement_mileage=replacement_mileage,
        service_life_miles=service_life_miles,
    )


def build_fleet_snapshot() -> List[BusMaintenanceSnapshot]:
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

    fleet: List[BusMaintenanceSnapshot] = []
    for bus in buses:
        rotor_details: List[RotorStats] = []
        alerts: List[str] = []
        for position in get_rotor_positions(bus):
            position_measurements = [
                m for m in bus.rotor_measurements.all() if m.position == position
            ]
            stats = _compute_rotor_stats(bus, position_measurements)
            stats.position = position
            rotor_details.append(stats)
            if stats.alert:
                alerts.append(f"{position} rotor due soon")
        fleet.append(BusMaintenanceSnapshot(bus=bus, rotor_details=rotor_details, alerts=alerts))
    return fleet


def initialize_rotors(bus: Bus, measurement_date: date | None = None) -> None:
    measurement_date = measurement_date or timezone.now().date()
    baseline_thickness = Decimal(bus.min_rotor_thickness) + Decimal("8.0")
    for position in get_rotor_positions(bus):
        RotorMeasurement.objects.update_or_create(
            bus=bus,
            position=position,
            measurement_date=measurement_date,
            defaults={
                "mileage_at_measurement": bus.current_mileage,
                "thickness_mm": baseline_thickness,
            },
        )
