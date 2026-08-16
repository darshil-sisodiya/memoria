"""Shared API schema configuration."""

from pydantic import BaseModel, ConfigDict


class ReadSchema(BaseModel):
    """Base schema for serializing SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)

