"""Best-effort, offline Paper metadata extraction from a PDF source."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import fitz

from app.parsers.reference_metadata_parser import normalize_arxiv_id, normalize_doi


_SPACE_RE = re.compile(r"\s+")
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_ARXIV_RE = re.compile(r"(?:arxiv\s*:\s*)?(\d{4}\.\d{4,5}(?:v\d+)?)", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_ABSTRACT_RE = re.compile(
    r"\babstract\b\s*[:—–-]?\s*(.+?)(?=\n\s*(?:keywords?|index\s+terms)\b|\n\s*(?:1\.?\s+)?introduction\b)",
    re.IGNORECASE | re.DOTALL,
)
@dataclass(frozen=True)
class ExtractedAuthor:
    name: str
    affiliation: str | None = None


@dataclass(frozen=True)
class ExtractedPaperMetadata:
    title: str | None = None
    abstract: str | None = None
    authors: list[ExtractedAuthor] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    doi: str | None = None
    arxiv_id: str | None = None
    journal: str | None = None
    conference: str | None = None
    publisher: str | None = None
    publication_year: int | None = None


class PaperMetadataExtractor:
    """Extract conservative metadata without network access or database writes."""

    def extract(self, pdf_path: Path, fallback_title: str | None = None) -> ExtractedPaperMetadata:
        with fitz.open(str(pdf_path)) as pdf:
            raw = pdf.metadata or {}
            pages = [pdf[index].get_text("text") for index in range(min(3, pdf.page_count))]
            text = "\n".join(pages)
            first_page = pdf[0] if pdf.page_count else None

            embedded_title = self._clean(raw.get("title"))
            title = embedded_title if self._useful_title(embedded_title, fallback_title) else None
            if not title and first_page is not None:
                title = self._title_from_layout(first_page)

            abstract = self._match_body(_ABSTRACT_RE, text, max_length=12_000)
            keywords = self._split_keywords(raw.get("keywords"))
            if not keywords:
                keywords = self._keywords_from_text(text)

            doi_match = _DOI_RE.search(text)
            arxiv_match = _ARXIV_RE.search(text)
            subject = self._clean(raw.get("subject"))
            journal = self._labeled_value(text, ("journal",))
            if not journal and first_page is not None:
                journal = self._journal_from_layout(first_page)
            conference = self._labeled_value(text, ("conference", "proceedings"))
            publisher = self._labeled_value(text, ("publisher", "published by"))
            if subject:
                journal = journal or self._prefixed_subject(subject, "journal")
                conference = conference or self._prefixed_subject(subject, "conference")

            embedded_authors = [ExtractedAuthor(name=name) for name in self._split_authors(raw.get("author"))]
            layout_authors = self._authors_from_layout(first_page) if first_page is not None else []
            # PDF Author metadata frequently names the file creator rather than
            # the paper authors. Prefer the visible title-page author block.
            authors = layout_authors or embedded_authors

            return ExtractedPaperMetadata(
                title=title,
                abstract=abstract,
                authors=authors,
                keywords=keywords,
                doi=normalize_doi(doi_match.group(0)) if doi_match else None,
                arxiv_id=normalize_arxiv_id(arxiv_match.group(1)) if arxiv_match else None,
                journal=journal,
                conference=conference,
                publisher=publisher,
                publication_year=self._publication_year(raw.get("creationDate"), text),
            )

    @staticmethod
    def _clean(value: str | None, max_length: int = 500) -> str | None:
        if not value:
            return None
        cleaned = _SPACE_RE.sub(" ", value).strip(" \t\r\n,;:-")
        return cleaned[:max_length] or None

    @classmethod
    def _useful_title(cls, title: str | None, fallback: str | None) -> bool:
        if not title or len(title) < 4:
            return False
        lowered = title.casefold()
        if lowered in {"untitled", "document", "microsoft word", "pdf"}:
            return False
        return not (fallback and lowered == fallback.strip().casefold())

    @classmethod
    def _title_from_layout(cls, page) -> str | None:
        spans: list[tuple[float, float, float, str]] = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    value = cls._clean(span.get("text"), 300)
                    bbox = span.get("bbox", (0, 0, 0, 0))
                    if value and bbox[1] < page.rect.height * 0.48:
                        spans.append((float(span.get("size", 0)), float(bbox[1]), float(bbox[0]), value))
        if not spans:
            return None
        max_size = max(item[0] for item in spans)
        candidates = [item for item in spans if item[0] >= max_size * 0.82 and len(item[3]) > 2]
        candidates.sort(key=lambda item: (item[1], item[2]))
        title = cls._clean(" ".join(item[3] for item in candidates), 1000)
        return title if title and len(title.split()) >= 2 else None

    @classmethod
    def _split_authors(cls, value: str | None) -> list[str]:
        cleaned = cls._clean(value, 2000)
        if not cleaned:
            return []
        parts = re.split(r"\s*(?:;|\n|\band\b|&)\s*", cleaned, flags=re.IGNORECASE)
        result: list[str] = []
        for part in parts:
            name = cls._clean(part, 200)
            if name and "@" not in name and name.casefold() not in {item.casefold() for item in result}:
                result.append(name)
        return result[:100]

    @classmethod
    def _authors_from_layout(cls, page) -> list[ExtractedAuthor]:
        lines: list[tuple[float, float, str]] = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = cls._clean(" ".join(span.get("text", "") for span in spans), 1000)
                if text:
                    bbox = line.get("bbox", (0, 0, 0, 0))
                    lines.append((float(bbox[1]), max((float(span.get("size", 0)) for span in spans), default=0), text))
        if not lines:
            return []
        heading_zone = [line for line in lines if line[0] < page.rect.height * 0.22]
        max_size = max((size for _, size, _ in heading_zone), default=0)
        title_lines = [line for line in heading_zone if line[1] >= max_size * 0.82]
        if not title_lines:
            return []
        title_bottom = max(y for y, _, _ in title_lines)
        affiliation_pattern = re.compile(r"\b(?:university|department|institute|laboratory|lab\b|school|college|faculty|centre|center|academy|corporation|company)\b", re.IGNORECASE)
        abstract_pattern = re.compile(r"\babstract\b", re.IGNORECASE)
        abstract_y = next((y for y, _, text in lines if y > title_bottom and abstract_pattern.search(text)), page.rect.height * 0.38)
        affiliation_y = next((y for y, _, text in lines if y > title_bottom and affiliation_pattern.search(text)), abstract_y)
        stop = min(abstract_y, affiliation_y)
        rejected = re.compile(r"\b(journal|conference|arxiv|abstract|corresponding|email|homepage)\b|@", re.IGNORECASE)
        candidates = [text for y, size, text in lines if title_bottom < y < stop and size < max_size * 0.82 and not rejected.search(text)]
        if not candidates:
            return []
        author_text = cls._join_author_lines(candidates[:4])
        parsed: list[tuple[str, set[str]]] = []
        roles = {"member", "senior member", "fellow", "ieee", "project leader", "corresponding author"}
        protected_markers = re.sub(r"(?<=\d),(?=\d)", "§", author_text)
        for part in re.split(r"\s*(?:;|,|\band\b|&)\s*", protected_markers, flags=re.IGNORECASE):
            part = part.replace("§", ",")
            markers = set(re.findall(r"\d+", part))
            cleaned = re.sub(r"[\d*†‡♠§]+", "", part)
            name = cls._clean(cleaned, 200)
            if not name or name.casefold() in roles or not (2 <= len(name.split()) <= 6):
                continue
            if sum(character.isalpha() for character in name) < 4:
                continue
            if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'’.-]+(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ'’.-]+){1,5}|[\u4e00-\u9fff]{2,8}", name):
                continue
            if name.casefold() not in {item[0].casefold() for item in parsed}:
                parsed.append((name, markers))

        affiliation_rows: list[tuple[set[str], str]] = []
        for y, _, text in lines:
            marker_match = re.match(r"^\s*(\d+(?:\s*,\s*\d+)*)", text)
            if not (affiliation_y <= y < abstract_y) or not (affiliation_pattern.search(text) or marker_match):
                continue
            markers = set(re.findall(r"\d+", marker_match.group(1))) if marker_match else set()
            affiliation = cls._clean(re.sub(r"^\s*[\d,]+\s*", "", text), 500)
            if affiliation:
                affiliation_rows.append((markers, affiliation))

        has_numbered_affiliations = any(markers for markers, _ in affiliation_rows)
        authors: list[ExtractedAuthor] = []
        for name, markers in parsed[:100]:
            matched = [value for row_markers, value in affiliation_rows if markers and markers & row_markers]
            if not matched and affiliation_rows and not has_numbered_affiliations:
                matched = [value for _, value in affiliation_rows]
            authors.append(ExtractedAuthor(name=name, affiliation=cls._clean("; ".join(dict.fromkeys(matched)), 512)))
        return authors

    @staticmethod
    def _join_author_lines(lines: list[str]) -> str:
        result = lines[0]
        for line in lines[1:]:
            previous_tail = result.rstrip().split(",")[-1].strip().split()
            next_head = line.lstrip(" ,").split(",")[0].strip().split()
            continues_wrapped_name = (
                not line.lstrip().startswith(",")
                and len(previous_tail) == 1
                and len(next_head) == 1
            )
            separator = " " if line.lstrip().startswith(",") or continues_wrapped_name else ", "
            result = f"{result}{separator}{line.lstrip(' ,')}"
        return result

    @classmethod
    def _journal_from_layout(cls, page) -> str | None:
        lines = [cls._clean(line, 500) for line in page.get_text("text").splitlines()]
        lines = [line for line in lines if line]
        for line in lines[:12]:
            match = re.match(r"(.+?\bjournal)\s*(?:,|\bvol\.?\b|$)", line, re.IGNORECASE)
            if match:
                return cls._clean(match.group(1), 255)
        for index, line in enumerate(lines[:12]):
            if "sciencedirect" in line.casefold() and index + 1 < len(lines):
                candidate = lines[index + 1]
                if not re.search(r"homepage|www\.|https?://", candidate, re.IGNORECASE):
                    return cls._clean(candidate, 255)
        return None

    @classmethod
    def _split_keywords(cls, value: str | None) -> list[str]:
        if not value:
            return []
        result: list[str] = []
        for part in re.split(r"\s*[,;|•·]\s*", value):
            keyword = cls._clean(part, 150)
            if keyword and 1 < len(keyword) and keyword.casefold() not in {item.casefold() for item in result}:
                result.append(keyword)
        return result[:50]

    @classmethod
    def _keywords_from_text(cls, text: str) -> list[str]:
        lines = text.splitlines()
        header = re.compile(r"^(?:key\s*words?|keywords?|index\s+terms)\s*[:—–-]\s*(.*)$", re.IGNORECASE)
        stop = re.compile(
            r"^(?:abstract\b|nomenclature\b|(?:\d+(?:\.\d+)*)\s+[A-Z]|introduction\b|references\b|a\s+b\s+s\s+t\s+r\s+a\s+c\s+t\b|a\s+r\s+t\s+i\s+c\s+l\s+e\s+i\s+n\s+f\s+o\b)",
            re.IGNORECASE,
        )
        for index, line in enumerate(lines):
            match = header.search(line.strip())
            if not match:
                continue
            chunks: list[str] = []
            if initial := match.group(1).strip():
                chunks.append(initial)
            for following in lines[index + 1:index + 9]:
                value = following.strip()
                if not value:
                    if chunks:
                        break
                    continue
                if stop.match(value) or (value.isupper() and len(value.split()) <= 6):
                    break
                chunks.append(value)
                if value.endswith("."):
                    break
            if not chunks:
                return []
            joined = chunks[0]
            for chunk in chunks[1:]:
                joined = f"{joined[:-1]}{chunk}" if joined.endswith("-") else f"{joined} {chunk}"
            return cls._split_keywords(joined.rstrip("."))
        return []

    @classmethod
    def _match_body(cls, pattern: re.Pattern[str], text: str, max_length: int) -> str | None:
        match = pattern.search(text)
        return cls._clean(match.group(1), max_length) if match else None

    @classmethod
    def _labeled_value(cls, text: str, labels: tuple[str, ...]) -> str | None:
        names = "|".join(re.escape(label) for label in labels)
        match = re.search(rf"(?:^|\n)\s*(?:{names})\s*[:—–-]\s*([^\n]+)", text, re.IGNORECASE)
        return cls._clean(match.group(1), 255) if match else None

    @classmethod
    def _prefixed_subject(cls, subject: str, prefix: str) -> str | None:
        match = re.match(rf"{prefix}\s*[:—–-]\s*(.+)", subject, re.IGNORECASE)
        return cls._clean(match.group(1), 255) if match else None

    @staticmethod
    def _publication_year(creation_date: str | None, text: str) -> int | None:
        upper = datetime.now(timezone.utc).year + 1
        if creation_date:
            match = re.search(r"(?:D:)?((?:19|20)\d{2})", creation_date)
            if match and 1900 <= int(match.group(1)) <= upper:
                return int(match.group(1))
        candidates = [int(value) for value in _YEAR_RE.findall(text[:8000])]
        valid = [value for value in candidates if 1900 <= value <= upper]
        return valid[0] if valid else None
