from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Sequence

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


def _group_measurements_by_position(
    bus: Bus,
) -> Dict[str, List[RotorMeasurement]]:
    grouped: Dict[str, List[RotorMeasurement]] = defaultdict(list)
    for measurement in bus.rotor_measurements.all():
        grouped[measurement.position].append(measurement)
    return grouped


def compute_rotor_details(bus: Bus) -> List[RotorStats]:
    grouped_measurements = _group_measurements_by_position(bus)
    rotor_details: List[RotorStats] = []
    for position in get_rotor_positions(bus):
        position_measurements = grouped_measurements.get(position, [])
        position_measurements.sort(key=lambda m: (m.measurement_date, m.id))
        stats = _compute_rotor_stats(bus, position_measurements)
        stats.position = position
        rotor_details.append(stats)
    return rotor_details


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
        rotor_details = compute_rotor_details(bus)
        alerts = [
            f"{detail.position} rotor due soon"
            for detail in rotor_details
            if detail.alert
        ]
        fleet.append(
            BusMaintenanceSnapshot(bus=bus, rotor_details=rotor_details, alerts=alerts)
        )
    return fleet


def get_lowest_rotor_summary(bus: Bus) -> Dict[str, object]:
    rotor_details = compute_rotor_details(bus)
    measured_rotors = [
        detail for detail in rotor_details if detail.current_thickness is not None
    ]

    if not measured_rotors:
        return {
            "position": None,
            "status_label": "Needs data",
            "status_class": "status-missing",
            "current_thickness": None,
        }

    lowest = min(measured_rotors, key=lambda detail: detail.current_thickness)
    status_label = "Attention" if lowest.alert else "Healthy"
    status_class = "status-alert" if lowest.alert else "status-ok"

    return {
        "position": lowest.position,
        "status_label": status_label,
        "status_class": status_class,
        "current_thickness": lowest.current_thickness,
    }


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
