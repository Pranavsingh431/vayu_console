"""SQLAlchemy ORM models.

Every model must be imported here. Alembic's autogenerate only sees what is
attached to `Base.metadata` at import time, so a model missing from this list is
silently invisible to migrations.
"""

from app.database.base import Base
from app.models.common import SRID, DataSource, ProvenanceMixin
from app.models.fire import FireDetection
from app.models.measurement import Measurement
from app.models.station import Sensor, Station
from app.models.weather import WeatherObservation

__all__ = [
    "SRID",
    "Base",
    "DataSource",
    "FireDetection",
    "Measurement",
    "ProvenanceMixin",
    "Sensor",
    "Station",
    "WeatherObservation",
]
