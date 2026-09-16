# Release PyPI (rare)

oto-cli est **basse priorité** et n'a **aucun workflow de publication** : la release est un geste
manuel, fait quand quelqu'un hors de l'infra Otomata en a besoin. (oto-core, lui, publie
automatiquement au tag — ne pas confondre les deux.)

⚠️ `hatch build` / `hatch publish` ne marchent pas sur cette machine (pas de `python`, hatchling non
bootstrappé). Passer par `build` + `twine` dans un venv dédié, et builder depuis `git archive HEAD`
pour **exclure le WIP non commité** de la release.

## Le geste

1. Bumper `version` dans `pyproject.toml` — **seul endroit** (pas d'`oto/__init__.py` depuis le split
   oto-core, pas de lock). Commit + push.
2. Puis :

```bash
python3 -m venv /tmp/buildenv && /tmp/buildenv/bin/pip install build twine
rm -rf /tmp/rel && mkdir -p /tmp/rel && git archive HEAD | tar -x -C /tmp/rel && cd /tmp/rel
/tmp/buildenv/bin/python -m build
TWINE_USERNAME=__token__ \
TWINE_PASSWORD="$(op read 'op://oto/PyPI publication oto-core et oto-cli/credential')" \
  /tmp/buildenv/bin/twine upload dist/*
gh release create vX.Y.Z --generate-notes dist/*
```

Le jeton vit dans **1Password**, coffre `oto`, item « PyPI publication oto-core et oto-cli »
(migré depuis SOPS le 16/09/2026). La copie SOPS existe encore en lecture seule et n'est plus la
référence — cf. `/data/infra/docs/secrets.md`.
