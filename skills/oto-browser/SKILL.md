---
name: oto-browser
description: "Browser automation: free-form browsing (any URL) + LinkedIn, Crunchbase, Pappers, Indeed, G2. Use for scraping ANY website, profiles, company pages, job searches, reviews."
---

# Browser Automation (oto browser / oto linkedin)

Prérequis : `oto` installé (pipx), `o-browser` installé (`pip install -e /data/projects/o-browser`). Pour LinkedIn, **un profil browser persistant loggé** (`oto linkedin login --profile <dir>`) — l'injection de cookie `LINKEDIN_COOKIE` dans un browser frais est bloquée par le fingerprinting TLS de LinkedIn (la session doit être créée dans le même browser qui la réutilise).

Toutes les commandes browser tournent en headless par défaut. Ajouter `--no-headless` pour debug visuel.

## Mode libre (any URL)

Pour scraper N'IMPORTE QUEL site (Instagram, Twitter, pages web quelconques...), utiliser `BrowserClient` directement en Python :

```python
from o_browser import BrowserClient

async with BrowserClient(headless=True) as browser:
    await browser.goto("https://example.com")
    text = await browser.get_text()          # texte de la page
    html = await browser.get_html()          # HTML complet
    await browser.screenshot("/tmp/page.png") # capture d'écran

    # Interactions
    await browser.click("button.submit")
    await browser.fill("input[name=search]", "query")
    await browser.type("input", "text", delay=50)  # frappe réaliste
    await browser.press("Enter")

    # Scroll (chargement dynamique)
    await browser.scroll_to_bottom(times=5)
    await browser.wait_for_content(min_length=500)
    await browser.wait_for_selector(".results")

    # JavaScript
    data = await browser.evaluate("document.title")
```

Options `BrowserClient` : `headless`, `cdp_url` (Chrome existant), `profile` (session persistante), `channel`, `record` (HAR+video), `interactive` (humain navigue), `proxy`.

**Quand utiliser le mode libre** : dès que le site n'est pas couvert par les commandes spécialisées ci-dessous, ou quand on veut naviguer librement sur un site.

## LinkedIn (oto linkedin)

```bash
# Profil d'une personne
oto linkedin profile "https://www.linkedin.com/in/john-doe/"

# Page entreprise
oto linkedin company "https://www.linkedin.com/company/otomata/"

# Recherche d'entreprises
oto linkedin search "fintech" --limit 10

# Liste des employés d'une entreprise (par slug)
oto linkedin people otomata --limit 20

# Recherche d'employés avec filtres
oto linkedin employees otomata --keywords "CTO,CEO" --limit 10

# Recherche de personnes par mots-clés + géo
oto linkedin search-people "credit manager" --geo 105015875 --limit 50 --pages 5

# Posts d'un profil
oto linkedin posts "https://www.linkedin.com/in/john-doe/" -n 10
```

Options communes LinkedIn : `--cookie`, `--cdp-url`, `--profile`, `--channel`, `--no-rate-limit`, `--no-headless`.

### Session : login profil persistant

```bash
# Une fois par profil : ouvre un browser headed, tu te connectes à la main, tu fermes la fenêtre → session persistée
oto linkedin login --profile ~/.config/browser/linkedin
```

Ensuite toutes les commandes LinkedIn s'utilisent avec `--profile ~/.config/browser/linkedin`.

### Messagerie & outreach

```bash
# Lire les conversations (liste) ou un thread précis
oto linkedin messages "Nom Contact" --profile <dir>
oto linkedin messages --thread <threadId> --profile <dir>

# Envoyer un MESSAGE direct (1er degré uniquement, ou InMail premium)
oto linkedin send "https://www.linkedin.com/in/john-doe/" "Bonjour …" --profile <dir>

# Envoyer une INVITATION de connexion (primitive cold-outreach), avec note optionnelle (<=300 car.)
oto linkedin connect "https://www.linkedin.com/in/john-doe/" --note "Bonjour …" --profile <dir>
```

**Flow cold typique** : `search-people`/`employees` (trouver) → `connect --note` (inviter) → après acceptation, `send` (messager). Le message direct échoue si le contact n'est pas en 1er degré (pas de bouton « Message »).

`--dry-run` (sur `send` et `connect`) : exécute tout sauf le clic d'envoi final et sauve un screenshot dans `/tmp` — pour valider sans contacter personne.

Rate limiting actif par défaut (presets conservateurs : free = 6 msg/h·40/j, 4 invit/h·15/j). `--no-rate-limit` pour passer outre.

## Crunchbase

```bash
# Fiche entreprise
oto browser crunchbase-company "otomata"
```

## Pappers (entreprises FR)

```bash
# Données entreprise par SIREN
oto browser pappers-siren "123456789"
```

## Indeed (offres d'emploi)

```bash
# Recherche d'offres
oto browser indeed-search "développeur python" --location "Paris" --country fr --limit 25
```

## G2 (avis produit)

```bash
# Scraper les avis
oto browser g2-reviews "https://www.g2.com/products/xxx/reviews" --limit 50
```

## Exemples

1. **Profil LinkedIn** : `oto linkedin profile "https://www.linkedin.com/in/alexis-laporte/"`
2. **Trouver les C-levels d'une boîte** : `oto linkedin employees stripe --keywords "CEO,CTO,CFO" --limit 5`
3. **Offres Indeed à Lyon** : `oto browser indeed-search "data engineer" --location "Lyon" --limit 20`
