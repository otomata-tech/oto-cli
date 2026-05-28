"""DVF — Demandes de Valeurs Foncières (transactions immobilières, open data).

Source : fichiers géolocalisés Etalab sur data.gouv.fr, maille commune/année.
  https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/communes/{dept}/{commune}.csv
Pas de clé. Licence Ouverte. Années dispo : 2021 → courante.

Use case CGP : valoriser un bien par comparables (€/m² médian d'une commune
pour un type de bien donné, sur les N dernières années).

Gotcha DVF : une mutation (vente) = N lignes CSV (un appartement + ses
dépendances + lots de copro). `valeur_fonciere` est le montant TOTAL de la
mutation, répété sur chaque ligne. Pour un €/m² fiable on ne garde que les
mutations "mono-bien" (une seule ligne bâtie du type ciblé) — les ventes
multi-lots polluent le ratio. Cf. `_clean_comparables`.
"""
from __future__ import annotations

import csv
import io
import math
import statistics
from datetime import datetime
from typing import Any, Optional

import requests


BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv"
BAN_URL = "https://api-adresse.data.gouv.fr/search/"
FIRST_YEAR = 2021

# type_local DVF → on ne calcule un €/m² que pour le bâti habitable.
BATI_TYPES = {"Appartement", "Maison"}

# Garde-fou outliers : un €/m² hors de cette plage = erreur de saisie, vente en
# indivision (quote-part), ou mutation atypique. Exclu des stats pour ne pas
# fausser la médiane/moyenne d'un CGP.
PRIX_M2_MIN = 100
PRIX_M2_MAX = 50000


class DvfClient:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    def _commune_csv(self, code_commune: str, year: int) -> list[dict[str, Any]]:
        """Récupère + parse le CSV d'une commune pour une année. [] si 404."""
        dept = _dept_from_commune(code_commune)
        url = f"{BASE_URL}/{year}/communes/{dept}/{code_commune}.csv"
        r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        return list(reader)

    def _rows_for(self, code_commune: str, years: int) -> list[dict[str, Any]]:
        """Les `years` dernières années AVEC data (DVF a ~6 mois de lag, donc
        l'année courante est souvent vide — on l'ignore et on remonte)."""
        current = datetime.now().year
        rows: list[dict[str, Any]] = []
        collected = 0
        y = current
        while y >= FIRST_YEAR and collected < years:
            year_rows = self._commune_csv(code_commune, y)
            if year_rows:
                rows.extend(year_rows)
                collected += 1
            y -= 1
        return rows

    def comparables(
        self,
        code_commune: str,
        type_local: Optional[str] = None,
        surface_min: Optional[float] = None,
        surface_max: Optional[float] = None,
        years: int = 2,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Transactions comparables pour une commune (mono-bien bâti), avec €/m².

        Args:
            code_commune: code INSEE 5 chiffres (ex. "13201").
            type_local: "Appartement" | "Maison" (défaut : les deux).
            surface_min/max: bornes surface bâtie m².
            years: profondeur en années (défaut 2, max ~5 selon dispo).
            limit: nb max de comparables retournés (les plus récents).
        """
        rows = self._rows_for(code_commune, years)
        comps = _clean_comparables(rows, type_local, surface_min, surface_max)
        comps.sort(key=lambda c: c["date_mutation"], reverse=True)
        return {
            "code_commune": code_commune,
            "type_local": type_local,
            "years": years,
            "count": len(comps),
            "comparables": comps[:limit],
        }

    def geocode(self, adresse: str) -> Optional[dict[str, Any]]:
        """Géocode une adresse via la BAN (Base Adresse Nationale, keyless).

        Renvoie {lon, lat, code_commune, label, score} ou None si pas de match.
        """
        r = self.session.get(BAN_URL, params={"q": adresse, "limit": 1}, timeout=self.timeout)
        r.raise_for_status()
        feats = r.json().get("features", [])
        if not feats:
            return None
        f = feats[0]
        lon, lat = f["geometry"]["coordinates"]
        p = f["properties"]
        return {
            "lon": lon,
            "lat": lat,
            "code_commune": p.get("citycode"),
            "label": p.get("label"),
            "score": p.get("score"),
        }

    def comparables_by_address(
        self,
        adresse: str,
        radius_m: int = 500,
        type_local: Optional[str] = None,
        surface_min: Optional[float] = None,
        surface_max: Optional[float] = None,
        years: int = 3,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Comparables autour d'une adresse précise (géocode BAN + filtre rayon).

        Args:
            adresse: adresse libre (ex. "44 la canebière marseille").
            radius_m: rayon de recherche en mètres autour du point géocodé.
            type_local / surface_min / surface_max / years / limit : cf. comparables().
        """
        geo = self.geocode(adresse)
        if not geo or not geo.get("code_commune"):
            return {"adresse": adresse, "error": "geocode_failed", "comparables": [], "count": 0}

        base = self.comparables(
            code_commune=geo["code_commune"],
            type_local=type_local,
            surface_min=surface_min,
            surface_max=surface_max,
            years=years,
            limit=100000,  # on filtre par distance après, pas avant
        )
        near: list[dict[str, Any]] = []
        for c in base["comparables"]:
            if c["latitude"] is None or c["longitude"] is None:
                continue
            dist = _haversine_m(geo["lat"], geo["lon"], c["latitude"], c["longitude"])
            if dist <= radius_m:
                near.append({**c, "distance_m": round(dist)})
        near.sort(key=lambda c: c["distance_m"])

        prix_m2 = [c["prix_m2"] for c in near if c["prix_m2"]]
        return {
            "adresse_geocodee": geo["label"],
            "code_commune": geo["code_commune"],
            "radius_m": radius_m,
            "type_local": type_local,
            "years": years,
            "count": len(near),
            "median_prix_m2": round(statistics.median(prix_m2)) if prix_m2 else None,
            "comparables": near[:limit],
        }

    def stats(
        self,
        code_commune: str,
        type_local: Optional[str] = None,
        years: int = 3,
    ) -> dict[str, Any]:
        """Stats €/m² d'une commune : médiane/moyenne/min/max + ventilation annuelle.

        Args:
            code_commune: code INSEE 5 chiffres.
            type_local: "Appartement" | "Maison" (défaut : les deux).
            years: profondeur (défaut 3).
        """
        rows = self._rows_for(code_commune, years)
        comps = _clean_comparables(rows, type_local, None, None)
        prix_m2 = [c["prix_m2"] for c in comps if c["prix_m2"]]

        by_year: dict[str, dict[str, Any]] = {}
        for c in comps:
            yr = c["date_mutation"][:4]
            by_year.setdefault(yr, {"count": 0, "_pm2": []})
            by_year[yr]["count"] += 1
            if c["prix_m2"]:
                by_year[yr]["_pm2"].append(c["prix_m2"])
        for yr, d in by_year.items():
            pm2 = d.pop("_pm2")
            d["median_prix_m2"] = round(statistics.median(pm2)) if pm2 else None

        return {
            "code_commune": code_commune,
            "type_local": type_local,
            "years": years,
            "count": len(comps),
            "median_prix_m2": round(statistics.median(prix_m2)) if prix_m2 else None,
            "mean_prix_m2": round(statistics.mean(prix_m2)) if prix_m2 else None,
            "min_prix_m2": round(min(prix_m2)) if prix_m2 else None,
            "max_prix_m2": round(max(prix_m2)) if prix_m2 else None,
            "by_year": dict(sorted(by_year.items())),
        }


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en mètres entre 2 points (lat/lon degrés)."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _dept_from_commune(code_commune: str) -> str:
    """Département depuis le code commune INSEE. Gère la Corse (2A/2B) + DOM (97x)."""
    if code_commune[:2] in ("2A", "2B"):
        return code_commune[:2]
    if code_commune[:2] == "97":
        return code_commune[:3]
    return code_commune[:2]


def _to_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _clean_comparables(
    rows: list[dict[str, Any]],
    type_local: Optional[str],
    surface_min: Optional[float],
    surface_max: Optional[float],
) -> list[dict[str, Any]]:
    """Garde les mutations mono-bien (1 ligne bâtie du type ciblé) → €/m² fiable.

    Une mutation multi-lots (plusieurs bâtis, ou bâti + gros terrain) est exclue
    du calcul €/m² parce que `valeur_fonciere` est globale et fausserait le ratio.
    """
    targets = {type_local} if type_local else BATI_TYPES

    # Regroupe les lignes par mutation.
    by_mutation: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("nature_mutation") != "Vente":
            continue
        by_mutation.setdefault(r["id_mutation"], []).append(r)

    out: list[dict[str, Any]] = []
    for mut_id, mut_rows in by_mutation.items():
        bati = [r for r in mut_rows if r.get("type_local") in BATI_TYPES]
        # Mono-bien : exactement 1 ligne bâtie habitable.
        if len(bati) != 1:
            continue
        row = bati[0]
        if row.get("type_local") not in targets:
            continue
        surface = _to_float(row.get("surface_reelle_bati"))
        valeur = _to_float(row.get("valeur_fonciere"))
        if not surface or not valeur or surface <= 0:
            continue
        if surface_min and surface < surface_min:
            continue
        if surface_max and surface > surface_max:
            continue
        prix_m2 = round(valeur / surface)
        if prix_m2 < PRIX_M2_MIN or prix_m2 > PRIX_M2_MAX:
            continue
        adresse = " ".join(
            str(row.get(k) or "").strip()
            for k in ("adresse_numero", "adresse_suffixe", "adresse_nom_voie")
        ).strip()
        out.append({
            "id_mutation": mut_id,
            "date_mutation": row.get("date_mutation"),
            "valeur_fonciere": round(valeur),
            "type_local": row.get("type_local"),
            "surface_reelle_bati": round(surface),
            "nombre_pieces_principales": row.get("nombre_pieces_principales") or None,
            "prix_m2": prix_m2,
            "adresse": adresse or None,
            "code_postal": row.get("code_postal") or None,
            "commune": row.get("nom_commune") or None,
            "longitude": _to_float(row.get("longitude")),
            "latitude": _to_float(row.get("latitude")),
        })
    return out
