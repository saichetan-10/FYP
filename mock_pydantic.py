"""Mock Pydantic implementation for basic functionality."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import json


class BaseModel:
    """Mock BaseModel that uses dataclasses internally."""

    def __init__(self, **data):
        # Get all class attributes that are Field objects
        for key in dir(self.__class__):
            if not key.startswith('_'):
                attr = getattr(self.__class__, key)
                if hasattr(attr, 'default_factory') and callable(attr.default_factory):
                    # It's a Field with default_factory
                    if key not in data:
                        data[key] = attr.default_factory()
                elif hasattr(attr, 'default'):
                    # It's a Field with default
                    if key not in data:
                        data[key] = attr.default

        # Set all attributes
        for key, value in data.items():
            setattr(self, key, value)

    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.__dict__

    def json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.dict())

    @classmethod
    def parse_obj(cls, obj: Dict[str, Any]):
        """Parse from dictionary."""
        return cls(**obj)

    @classmethod
    def parse_raw(cls, raw: str):
        """Parse from JSON string."""
        return cls.parse_obj(json.loads(raw))


def Field(default: Any = None, default_factory=None, **kwargs):
    """Mock Field function."""
    class MockField:
        def __init__(self, default=None, default_factory=None, **kwargs):
            self.default = default
            self.default_factory = default_factory
            self.kwargs = kwargs

    return MockField(default=default, default_factory=default_factory, **kwargs)


# Mock validation types
class ValidationError(Exception):
    pass