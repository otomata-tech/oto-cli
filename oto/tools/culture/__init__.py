"""Min. Culture open data — Opendatasoft portals (data.culture.gouv.fr).

Currently exposes:
- spectacle: Licences entrepreneurs de spectacles vivants (LES)
"""

from .opendatasoft import OpendatasoftClient
from .spectacle import SpectacleClient

__all__ = ["OpendatasoftClient", "SpectacleClient"]
