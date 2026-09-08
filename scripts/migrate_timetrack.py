"""One-shot — migre /mnt/otomata/time-entries.json vers le namespace `timetrack`
du datastore (PostgreSQL via MCP).

Prérequis :
- `OTO_API_KEY` configuré dans SOPS (token issu via `scripts/issue_token.py`).

L'`id` legacy (`YYYY-MM-DD-NNN`) est ignoré — `date` + `_created_at` suffisent
à retrouver l'origine. Le `_id` UUID du datastore est généré côté serveur.

Usage :
    python3 -m scripts.migrate_timetrack [--dry-run] [--rate-limit 0.5]

Idempotence : la commande échoue si le namespace `timetrack` existe déjà
(évite les doublons). Pour rejouer : `oto data rm timetrack` puis relancer.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


SOURCE = Path("/mnt/otomata/time-entries.json")
NAMESPACE = "timetrack"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche ce qui serait fait sans rien écrire")
    parser.add_argument("--rate-limit", type=float, default=0.5,
                        help="Sleep (s) entre chaque append")
    parser.add_argument("--source", type=Path, default=SOURCE)
    args = parser.parse_args()

    if not args.source.exists():
        print(f"source introuvable: {args.source}", file=sys.stderr)
        return 2

    payload = json.loads(args.source.read_text())
    entries = payload.get("entries", [])
    print(f"source: {args.source} ({len(entries)} entries)")

    if args.dry_run:
        print("--dry-run : aucune écriture.")
        for e in entries[:3]:
            row = _entry_to_row(e)
            print("  →", json.dumps(row, ensure_ascii=False))
        print(f"  … +{max(0, len(entries) - 3)} autres")
        return 0

    from oto.tools.datastore.client import DatastoreClient, DatastoreError
    client = DatastoreClient()

    # 1. Crée le namespace (échoue si déjà présent → forcer un cleanup manuel)
    try:
        ns = client.create_namespace(NAMESPACE)
    except DatastoreError as e:
        if e.status == 409:
            print(f"namespace `{NAMESPACE}` existe déjà — `oto data rm {NAMESPACE}` "
                  "pour repartir de zéro", file=sys.stderr)
            return 3
        raise
    print(f"namespace créé: {ns['url']}")

    # 2. Injecte chaque entrée
    ok = 0
    failed = []
    for i, e in enumerate(entries, 1):
        row = _entry_to_row(e)
        try:
            client.append(NAMESPACE, row)
            ok += 1
            print(f"  [{i}/{len(entries)}] {row['date']} {row['project']} {row['hours']}h")
        except DatastoreError as err:
            failed.append((row.get("date"), err))
            print(f"  [{i}/{len(entries)}] FAIL {row.get('date')}: {err}", file=sys.stderr)
        if args.rate_limit:
            time.sleep(args.rate_limit)

    print(f"\nterminé: {ok}/{len(entries)} OK, {len(failed)} fail")
    if failed:
        return 1
    print(f"\n→ ouvre le tableau: {ns['url']}")
    return 0


def _entry_to_row(e: dict) -> dict:
    return {
        "date": e.get("date"),
        "project": e.get("project"),
        "hours": e.get("hours"),
        "billed": bool(e.get("billed")),
        "invoiceId": e.get("invoiceId"),
        "note": e.get("note"),
    }


if __name__ == "__main__":
    sys.exit(main())
