"""Exception hierarchy for the paraiso package.

Everything raised by paraiso derives from :class:`ParaisoError`, so callers can
catch the whole family with a single ``except``.
"""

from __future__ import annotations


class ParaisoError(Exception):
    """Base class for every error raised by paraiso."""


class NotFoundError(ParaisoError):
    """A referenced entity does not exist in this workspace."""


class CaptureNotFoundError(NotFoundError):
    pass


class ItemNotFoundError(NotFoundError):
    pass


class AreaNotFoundError(NotFoundError):
    pass


class ObjectiveNotFoundError(NotFoundError):
    pass


class InvalidBucketError(ParaisoError):
    """A value could not be interpreted as a PARAISO bucket."""


class AmbiguousIdError(ParaisoError):
    """An id prefix matched more than one entity; be more specific."""


class AlreadyProcessedError(ParaisoError):
    """A capture has already been filed or discarded."""


class SpaceExistsError(ParaisoError):
    """A workspace with this name already exists in the store."""


class SpaceNotFoundError(NotFoundError):
    """No workspace with this name exists in the store."""
