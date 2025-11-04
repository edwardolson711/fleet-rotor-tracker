from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List, Sequence

from django.db import models

from .apps import ROTOR_POSITIONS_ARTICULATED, ROTOR_POSITIONS_STANDARD


@dataclass
class RotorStats:
    """Aggregated rotor statistics for presentation."""

    position: str
    current_thickness: Decimal | None
    miles_left: int | None
    days_left: int | None
    alert: bool
    starting_mileage: int | None
    replacement_mileage: int | None
    service_life_miles: int | None


class Bus(models.Model):
    bus_number = models.CharField(max_length=50, unique=True)
    bus_type = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    current_mileage = models.PositiveIntegerField()
    is_articulating = models.BooleanField(default=False)
    min_rotor_thickness = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ["bus_number"]

    @property
    def rotor_positions(self) -> Sequence[str]:
        return (
            ROTOR_POSITIONS_ARTICULATED
            if self.is_articulating
            else ROTOR_POSITIONS_STANDARD
        )

    def __str__(self) -> str:  # pragma: no cover - repr convenience
        return f"Bus {self.bus_number}"


class RotorMeasurement(models.Model):
    bus = models.ForeignKey(
        Bus, related_name="rotor_measurements", on_delete=models.CASCADE
    )
    position = models.CharField(max_length=20)
    measurement_date = models.DateField()
    mileage_at_measurement = models.PositiveIntegerField()
    thickness_mm = models.DecimalField(max_digits=6, decimal_places=3)

    class Meta:
        ordering = ["measurement_date", "id"]
        unique_together = ("bus", "position", "measurement_date")

    def __str__(self) -> str:  # pragma: no cover - repr convenience
        return (
            f"RotorMeasurement(bus={self.bus_id}, position={self.position},"
            f" date={self.measurement_date})"
        )

    @classmethod
    def latest_for_positions(
        cls, bus: Bus, positions: Iterable[str]
    ) -> List["RotorMeasurement"]:
        measurements = (
            cls.objects.filter(bus=bus, position__in=positions)
            .order_by("position", "-measurement_date", "-id")
            .distinct("position")
        )
        return list(measurements)
