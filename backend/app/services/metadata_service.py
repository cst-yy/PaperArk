"""Fetch paper metadata from external APIs (Crossref, arXiv)."""

import httpx


class MetadataService:
    CROSSREF_API = "https://api.crossref.org/works"
    ARXIV_API = "http://export.arxiv.org/api/query"

    async def fetch_by_doi(self, doi: str) -> dict:
        """Fetch metadata from Crossref by DOI."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.CROSSREF_API}/{doi}", timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_crossref(data.get("message", {}))

    async def fetch_by_arxiv(self, arxiv_id: str) -> dict:
        """Fetch metadata from arXiv API."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.ARXIV_API,
                params={"id_list": arxiv_id},
                timeout=30,
            )
            resp.raise_for_status()
            return self._parse_arxiv(resp.text)

    def _parse_crossref(self, msg: dict) -> dict:
        authors = []
        for a in msg.get("author", []):
            name = f"{a.get('given', '')} {a.get('family', '')}".strip()
            authors.append({
                "name": name,
                "affiliation": a.get("affiliation", [{}])[0].get("name") if a.get("affiliation") else None,
            })

        return {
            "title": msg.get("title", [""])[0] if msg.get("title") else "",
            "abstract": msg.get("abstract", ""),
            "doi": msg.get("DOI"),
            "journal": msg.get("container-title", [""])[0] if msg.get("container-title") else None,
            "publisher": msg.get("publisher"),
            "publication_year": msg.get("published", {}).get("date-parts", [[None]])[0][0],
            "citation_count": msg.get("is-referenced-by-count"),
            "authors": authors,
            "url": msg.get("URL"),
        }

    def _parse_arxiv(self, xml_text: str) -> dict:
        # TODO: Parse arXiv Atom XML response
        # Use xml.etree.ElementTree or lxml
        return {}


metadata_service = MetadataService()
