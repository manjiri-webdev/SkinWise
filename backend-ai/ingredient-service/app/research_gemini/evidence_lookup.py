import re
from typing import Optional, List, Dict
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


class EvidenceLookupService:
    """
    Source-first evidence collection for cosmetic ingredients.

    Sources:
    - COSMILE Europe: cosmetic ingredient information/functions
    - CosIng: EU cosmetic identity/regulatory context
    - CIR: cosmetic safety assessments
    - PubChem: chemical identity, canonical names, aliases
    - PubMed: clinical/dermatology literature
    - Incidecoder: supplementary cosmetic information
    """

    def __init__(self):
        self.timeout = 12

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        }

        self.sources = [
            {
                "name": "COSMILE Europe",
                "type": "cosmetic_information",
                "domain": "cosmileeurope.eu",
            },
            {
                "name": "CosIng",
                "type": "cosmetic_identity_regulatory",
                "domain": "ec.europa.eu",
            },
            {
                "name": "CIR (Cosmetic Ingredient Review)",
                "type": "cosmetic_safety",
                "domain": "cir-safety.org",
            },
            {
                "name": "PubChem",
                "type": "chemical_identity",
                "domain": "pubchem.ncbi.nlm.nih.gov",
            },
            {
                "name": "PubMed",
                "type": "clinical_literature",
                "domain": "pubmed.ncbi.nlm.nih.gov",
            },
            {
                "name": "Incidecoder",
                "type": "cosmetic_information_supplementary",
                "domain": "incidecoder.com",
            },
        ]

    def lookup_evidence(self, ingredient: str) -> Optional[List[Dict]]:
        """Collect source-attributed evidence for one ingredient."""

        if not ingredient or not ingredient.strip():
            return None

        ingredient = ingredient.strip()
        evidence_items: List[Dict] = []

        for source in self.sources:
            try:
                item = self._fetch_evidence_from_source(ingredient, source)

                if item:
                    evidence_items.append(item)

            except Exception as exc:
                print(
                    f"Evidence lookup failed for "
                    f"{source['name']} / {ingredient}: {exc}"
                )

        return evidence_items or None

    def _fetch_evidence_from_source(
        self,
        ingredient: str,
        source: Dict
    ) -> Optional[Dict]:
        """Dispatch source-specific retrieval."""

        source_type = source["type"]

        if source_type == "chemical_identity":
            return self._fetch_pubchem(ingredient, source)

        if source_type == "clinical_literature":
            return self._fetch_pubmed(ingredient, source)

        if source_type == "cosmetic_information":
            return self._fetch_cosmile(ingredient, source)

        return self._fetch_html_source(ingredient, source)

    # ------------------------------------------------------------------
    # PubChem
    # ------------------------------------------------------------------

    def _fetch_pubchem(
        self,
        ingredient: str,
        source: Dict
    ) -> Optional[Dict]:
        """
        PubChem PUG REST.
        Used primarily for identity, canonical/IUPAC names and synonyms.
        """

        encoded = quote(ingredient, safe="")

        url = (
            "https://pubchem.ncbi.nlm.nih.gov/"
            f"rest/pug/compound/name/{encoded}/property/"
            "IUPACName,MolecularFormula,MolecularWeight/JSON"
        )

        synonyms_url = (
            "https://pubchem.ncbi.nlm.nih.gov/"
            f"rest/pug/compound/name/{encoded}/synonyms/JSON"
        )

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )

            if response.status_code != 200:
                return None

            data = response.json()

            properties = {}
            compounds = data.get("PropertyTable", {}).get("Properties", [])

            if compounds:
                properties = compounds[0]

            synonyms = []

            try:
                synonym_response = requests.get(
                    synonyms_url,
                    headers=self.headers,
                    timeout=self.timeout
                )

                if synonym_response.status_code == 200:
                    synonym_data = synonym_response.json()
                    synonym_groups = synonym_data.get(
                        "InformationList", {}
                    ).get("Information", [])

                    if synonym_groups:
                        synonyms = synonym_groups[0].get(
                            "Synonym", []
                        )
            except Exception as exc:
                print(f"PubChem synonym lookup failed: {exc}")

            evidence_parts = []

            if properties.get("IUPACName"):
                evidence_parts.append(
                    f"IUPAC name: {properties['IUPACName']}"
                )

            if properties.get("MolecularFormula"):
                evidence_parts.append(
                    f"Molecular formula: {properties['MolecularFormula']}"
                )

            if properties.get("MolecularWeight"):
                evidence_parts.append(
                    f"Molecular weight: {properties['MolecularWeight']}"
                )

            if synonyms:
                # Remove exact duplicate and keep a manageable amount.
                unique_synonyms = []
                seen = set()

                for synonym in synonyms:
                    normalized = synonym.strip().lower()

                    if normalized and normalized not in seen:
                        seen.add(normalized)
                        unique_synonyms.append(synonym.strip())

                if unique_synonyms:
                    evidence_parts.append(
                        "Synonyms: " + ", ".join(unique_synonyms[:30])
                    )

            if not evidence_parts:
                return None

            compound_url = (
                "https://pubchem.ncbi.nlm.nih.gov/"
                f"#query={encoded}"
            )

            return {
                "source_name": source["name"],
                "source_url": compound_url,
                "source_type": source["type"],
                "evidence_text": ". ".join(evidence_parts),
            }

        except Exception as exc:
            print(f"PubChem error for '{ingredient}': {exc}")
            return None

    # ------------------------------------------------------------------
    # PubMed
    # ------------------------------------------------------------------

    def _fetch_pubmed(
        self,
        ingredient: str,
        source: Dict
    ) -> Optional[Dict]:
        """
        Use NCBI E-utilities instead of scraping PubMed HTML.
        Fetches a small number of relevant article abstracts.
        """

        search_term = (
            f'"{ingredient}" AND '
            "(cosmetic OR skin OR dermatology OR topical)"
        )

        esearch_url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            f"esearch.fcgi?db=pubmed&retmode=json&retmax=5"
            f"&term={quote(search_term, safe='')}"
        )

        try:
            search_response = requests.get(
                esearch_url,
                headers=self.headers,
                timeout=self.timeout
            )

            if search_response.status_code != 200:
                return None

            search_data = search_response.json()

            ids = (
                search_data
                .get("esearchresult", {})
                .get("idlist", [])
            )

            if not ids:
                return None

            id_string = ",".join(ids)

            efetch_url = (
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
                f"efetch.fcgi?db=pubmed&id={id_string}"
                "&retmode=xml"
            )

            fetch_response = requests.get(
                efetch_url,
                headers=self.headers,
                timeout=self.timeout
            )

            if fetch_response.status_code != 200:
                return None

            soup = BeautifulSoup(
                fetch_response.text,
                "xml"
            )

            evidence_parts = []

            articles = soup.find_all("PubmedArticle")

            for article in articles:
                pmid = article.find("PMID")

                title = article.find("ArticleTitle")

                abstract_nodes = article.find_all(
                    "AbstractText"
                )

                title_text = (
                    title.get_text(" ", strip=True)
                    if title
                    else ""
                )

                abstract_text = " ".join(
                    node.get_text(" ", strip=True)
                    for node in abstract_nodes
                )

                if title_text:
                    evidence_parts.append(
                        f"PMID {pmid.get_text(strip=True) if pmid else 'unknown'} "
                        f"title: {title_text}"
                    )

                if abstract_text:
                    evidence_parts.append(
                        f"Abstract: {abstract_text}"
                    )

            if not evidence_parts:
                return None

            return {
                "source_name": source["name"],
                "source_url": (
                    "https://pubmed.ncbi.nlm.nih.gov/"
                    f"?term={quote(search_term, safe='')}"
                ),
                "source_type": source["type"],
                "evidence_text": "\n\n".join(
                    evidence_parts[:10]
                ),
            }

        except Exception as exc:
            print(f"PubMed error for '{ingredient}': {exc}")
            return None

    # ------------------------------------------------------------------
    # COSMILE
    # ------------------------------------------------------------------

    def _fetch_cosmile(
        self,
        ingredient: str,
        source: Dict
    ) -> Optional[Dict]:
        """
        COSMILE ingredient pages are the preferred cosmetic-information
        source. Because COSMILE's public database is interactive, first
        try likely direct slugs and then fall back to its database page.
        """

        slug = self._to_slug(ingredient)

        candidate_urls = [
            f"https://cosmileeurope.eu/inci/detail/{slug}/",
            f"https://cosmileeurope.eu/inci/{slug}/",
        ]

        for url in candidate_urls:
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )

                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(
                    response.text,
                    "html.parser"
                )

                title = soup.find("h1")

                page_text = self._extract_main_page_text(soup)

                if not page_text:
                    continue

                if not self._ingredient_matches_page(
                    ingredient,
                    page_text,
                    title
                ):
                    continue

                return {
                    "source_name": source["name"],
                    "source_url": response.url,
                    "source_type": source["type"],
                    "evidence_text": page_text,
                }

            except Exception as exc:
                print(
                    f"COSMILE lookup failed for '{ingredient}': {exc}"
                )

        return None

    # ------------------------------------------------------------------
    # Generic HTML sources
    # ------------------------------------------------------------------

    def _fetch_html_source(
        self,
        ingredient: str,
        source: Dict
    ) -> Optional[Dict]:
        """Fetch CIR, CosIng and Incidecoder pages."""

        url = self._generate_source_url(
            ingredient,
            source
        )

        if not url:
            return None

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True
            )

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            page_text = self._extract_main_page_text(soup)

            if not page_text:
                return None

            # Avoid accepting a completely unrelated search page.
            if not self._ingredient_matches_page(
                ingredient,
                page_text,
                soup.find("h1")
            ):
                return None

            return {
                "source_name": source["name"],
                "source_url": response.url,
                "source_type": source["type"],
                "evidence_text": page_text,
            }

        except Exception as exc:
            print(
                f"{source['name']} error for "
                f"'{ingredient}': {exc}"
            )
            return None

    def _generate_source_url(
        self,
        ingredient: str,
        source: Dict
    ) -> Optional[str]:

        encoded = quote(
            ingredient.strip(),
            safe=""
        )

        slug = self._to_slug(ingredient)

        source_type = source["type"]
        domain = source["domain"]

        if source_type == "cosmetic_identity_regulatory":
            # Official CosIng quick-search URL.
            return (
                "https://ec.europa.eu/growth/tools-databases/"
                "cosing/index.cfm?fuseaction=search.results"
                f"&search_term={encoded}"
            )

        if source_type == "cosmetic_safety":
            return (
                "https://cir-safety.org/search/"
                f"?searchterm={encoded}"
            )

        if source_type == "cosmetic_information_supplementary":
            return (
                f"https://incidecoder.com/ingredients/{slug}"
            )

        if domain == "ec.europa.eu":
            return (
                "https://ec.europa.eu/growth/tools-databases/"
                "cosing/index.cfm?fuseaction=search.results"
                f"&search_term={encoded}"
            )

        return None

    # ------------------------------------------------------------------
    # HTML extraction
    # ------------------------------------------------------------------

    def _extract_main_page_text(
        self,
        soup: BeautifulSoup
    ) -> Optional[str]:
        """
        Extract meaningful visible content.

        Unlike the old implementation, this does not split the complete
        page into arbitrary sentences and select them by character count.
        """

        # Remove obvious non-content elements.
        for element in soup(
            [
                "script",
                "style",
                "noscript",
                "iframe",
                "svg",
                "nav",
                "footer",
                "header",
                "aside",
                "form",
            ]
        ):
            element.decompose()

        # Prefer semantic/main content containers.
        candidates = []

        for selector in [
            "main",
            "article",
            "[role='main']",
            ".main-content",
            ".content",
            ".page-content",
            ".ingredient",
        ]:
            candidates.extend(soup.select(selector))

        if candidates:
            # Use the largest meaningful candidate.
            candidates.sort(
                key=lambda node: len(
                    node.get_text(" ", strip=True)
                ),
                reverse=True
            )

            root = candidates[0]
        else:
            root = soup.body or soup

        text = root.get_text(
            separator=" ",
            strip=True
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        # Remove common citation-marker artifacts only.
        text = re.sub(
            r"\[\s*\d+(?:\s*,\s*\d+)*\s*\]",
            "",
            text
        )

        # Avoid gigantic page dumps.
        if len(text) > 18000:
            text = text[:18000]

        return text if len(text) >= 80 else None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _ingredient_matches_page(
        self,
        ingredient: str,
        text: str,
        title
    ) -> bool:
        """Check whether the returned page actually refers to the ingredient."""

        ingredient_norm = self._normalize_for_match(
            ingredient
        )

        title_text = (
            title.get_text(" ", strip=True)
            if title
            else ""
        )

        title_norm = self._normalize_for_match(
            title_text
        )

        text_norm = self._normalize_for_match(
            text
        )

        if ingredient_norm and ingredient_norm in title_norm:
            return True

        if ingredient_norm and ingredient_norm in text_norm:
            return True

        # Allow common identity relationships for simple names.
        aliases = {
            "hyaluronic acid": [
                "sodium hyaluronate",
                "hyaluronan",
            ],
            "glycerin": [
                "glycerol",
                "glycerine",
            ],
            "niacinamide": [
                "nicotinamide",
                "vitamin b3",
            ],
        }

        for alias in aliases.get(
            ingredient_norm,
            []
        ):
            if (
                alias in title_norm
                or alias in text_norm
            ):
                return True

        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_slug(value: str) -> str:
        slug = value.strip().lower()
        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            slug
        )
        return slug.strip("-")

    @staticmethod
    def _normalize_for_match(value: str) -> str:
        value = value.lower().strip()
        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value
        )
        return " ".join(value.split())