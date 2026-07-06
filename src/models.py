from dataclasses import dataclass, field
from typing import List
import time


@dataclass(slots=True)
class Point:
    x: float
    y: float
    angle: float
    distance: float
    quality: int


@dataclass(slots=True)
class ScanFrame:
    frame_number: int
    timestamp: float = field(default_factory=time.time)
    points: List[Point] = field(default_factory=list)


@dataclass(slots=True)
class Person:
    id: int
    x: float
    y: float
    velocity: float = 0.0
    heading: float = 0.0