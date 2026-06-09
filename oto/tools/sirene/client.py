"""SireneClient — logique dans la lib partagée france-opendata (source unique).

Variante oto : conserve le défaut historique de résolution de clé via SOPS
(`oto.config.get_secret`) quand aucune clé n'est passée, attendu par les commandes
CLI `oto fr` qui instancient `SireneClient()` sans argument.
"""
from france_opendata.sirene import SireneClient as _BaseSireneClient, EMPLOYEE_RANGES

from ...config import get_secret

__all__ = ["SireneClient", "EMPLOYEE_RANGES"]


class SireneClient(_BaseSireneClient):
    def __init__(self, api_key: str = None, secret: str = None):
        super().__init__(
            api_key=api_key or get_secret("SIRENE_API_KEY"),
            secret=secret or get_secret("SIRENE_SECRET"),
        )
