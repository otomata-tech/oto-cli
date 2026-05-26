"""LinkedIn search mixins: people, employees, companies."""

import re
from typing import Optional, List
from urllib.parse import quote

from ._js import JS_PEOPLE_RESULTS


class SearchMixin:
    """Search LinkedIn for people and companies."""

    async def _extract_people_results(self) -> List[dict]:
        """Extract people search results from the current page via JS."""
        return await self.page.evaluate(JS_PEOPLE_RESULTS)

    async def get_company_id(self, company_slug: str) -> Optional[str]:
        """Get numeric company ID from slug."""
        await self.check_rate_limit("company_scrape")

        url = f"https://www.linkedin.com/company/{company_slug}/"
        await self.goto(url)
        await self._raise_if_auth_wall()
        await self.wait(2)

        html = await self.get_html()
        match = re.search(r"urn:li:fs_normalized_company:(\d+)", html)
        return match.group(1) if match else None

    async def search_employees(
        self, company_slug: str, keywords: List[str] = None, limit: int = 10
    ) -> List[dict]:
        """
        Search employees via LinkedIn search with company filter.

        Returns:
            List of {name, headline, linkedin}
        """
        company_id = await self.get_company_id(company_slug)
        if not company_id:
            return []

        await self.check_rate_limit("search_export")

        kw_str = " OR ".join(keywords) if keywords else ""
        search_url = (
            f"https://www.linkedin.com/search/results/people/"
            f"?currentCompany=%5B%22{company_id}%22%5D"
            f"&keywords={quote(kw_str)}&origin=FACETED_SEARCH"
        )

        await self.goto(search_url)
        await self._raise_if_auth_wall()
        await self.wait(4)

        for i in range(8):
            await self.scroll_by((i + 1) * 400)
            await self.wait(1.5)

        results = await self._extract_people_results()
        return results[:limit]

    async def get_company_people(self, company_slug: str, limit: int = 20) -> List[dict]:
        """
        Get employees from company's People page (sorted by relevance).

        Returns:
            List of {name, headline, linkedin}
        """
        await self.check_rate_limit("search_export")

        people_url = f"https://www.linkedin.com/company/{company_slug}/people/"
        await self.goto(people_url)
        await self._raise_if_auth_wall()
        await self.wait(3)

        for _ in range(limit // 12 + 1):
            await self.scroll_to_bottom(times=1, delay=1)

            show_more = await self.query_selector("button.scaffold-finite-scroll__load-button")
            if show_more:
                try:
                    await show_more.click()
                    await self.wait(2)
                except Exception:
                    break
            else:
                break

        employees = []
        seen_urls = set()

        cards = await self.query_selector_all("li.org-people-profile-card__profile-card-spacing")

        for card in cards:
            if len(employees) >= limit:
                break

            link = await card.query_selector('a[href*="/in/"]')
            if not link:
                continue

            href = await link.get_attribute("href")
            if not href:
                continue

            url = href.split("?")[0]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            name = ""
            name_el = await card.query_selector(".artdeco-entity-lockup__title")
            if name_el:
                name = (await name_el.inner_text()).strip()
                name = re.sub(r"\s*·\s*\d*(er?|e|st|nd|rd|th)?\+?$", "", name).strip()

            if not name or len(name) < 2:
                continue

            headline = ""
            headline_el = await card.query_selector(".artdeco-entity-lockup__subtitle")
            if headline_el:
                headline = (await headline_el.inner_text()).strip()

            employees.append({
                "name": name,
                "headline": headline,
                "linkedin": url
            })

        return employees

    async def search_companies(self, query: str, limit: int = 5) -> List[dict]:
        """
        Search companies on LinkedIn.

        Returns:
            List of {name, slug, url, headline}
        """
        await self.check_rate_limit("search_export")

        search_url = (
            f"https://www.linkedin.com/search/results/companies/"
            f"?keywords={quote(query)}&origin=SWITCH_SEARCH_VERTICAL"
        )
        await self.goto(search_url)
        await self._raise_if_auth_wall()
        await self.wait(3)

        for i in range(3):
            await self.scroll_by((i + 1) * 400)
            await self.wait(1)

        # Si LinkedIn affiche "Aucun résultat", retourner [] sans scraper la page :
        # sinon le scraper rabat sur des liens parasites (sidebar, suggestions)
        # type "Otomata" qui contaminent les batches d'enrichissement.
        no_results = await self.page.evaluate(r"""() => {
            const els = document.querySelectorAll('h2, h3, [class*="no-results"]');
            for (const el of els) {
                const t = (el.textContent || '').trim();
                if (/aucun résultat|no results|0 result/i.test(t)) return true;
            }
            return false;
        }""")
        if no_results:
            return []

        companies = []
        seen_slugs = set()

        # Restreindre à <main> : exclut sidebar/header/nav qui peuvent contenir
        # des suggestions parasites (companies que l'utilisateur suit, etc.)
        links = await self.query_selector_all('main a[href*="/company/"]')

        for link in links:
            if len(companies) >= limit:
                break

            href = await link.get_attribute("href")
            if not href or "/company/" not in href:
                continue

            match = re.search(r"/company/([^/?]+)", href)
            if not match:
                continue

            slug = match.group(1)
            if slug in seen_slugs or slug in ("login", "signup"):
                continue
            # Rejeter les slugs purement numériques : ce sont des company_id
            # internes (pages sans nom canonique). Vraies companies = kebab-case.
            if slug.isdigit():
                continue
            seen_slugs.add(slug)

            text = (await link.inner_text()).strip()
            if not text or len(text) < 2:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if not lines:
                continue

            name = lines[0]
            if name.lower() in ["follow", "suivre", "message", "view", "voir"]:
                continue

            headline = lines[1] if len(lines) > 1 else ""
            url = f"https://www.linkedin.com/company/{slug}/"

            companies.append({
                "name": name,
                "slug": slug,
                "url": url,
                "headline": headline
            })

        return companies

    async def search_people(
        self, keywords: str, geo: str = None, network: str = None,
        limit: int = 50, pages: int = 5,
    ) -> List[dict]:
        """
        Search people on LinkedIn by keywords with optional geo/network filter.

        Returns:
            List of {name, headline, linkedin, location}
        """
        results = []
        seen_urls = set()

        for page in range(1, pages + 1):
            if len(results) >= limit:
                break

            await self.check_rate_limit("search_export")

            params = f"keywords={quote(keywords)}&origin=FACETED_SEARCH"
            if geo:
                params += f"&geoUrn=%5B%22{geo}%22%5D"
            if network:
                params += f"&network=%5B%22{network}%22%5D"
            if page > 1:
                params += f"&page={page}"

            search_url = f"https://www.linkedin.com/search/results/people/?{params}"
            await self.goto(search_url)
            await self._raise_if_auth_wall()
            await self.wait(4)

            for i in range(8):
                await self.scroll_by((i + 1) * 400)
                await self.wait(1)

            page_results = await self._extract_people_results()
            page_count = 0
            for r in page_results:
                if len(results) >= limit:
                    break
                if r["linkedin"] in seen_urls:
                    continue
                seen_urls.add(r["linkedin"])
                results.append(r)
                page_count += 1

            print(f"  Page {page}: {page_count} results (total: {len(results)})")

            if page_count == 0:
                break

        return results
