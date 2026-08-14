"""Parse PDF structure into sections (table of contents)."""

import re
from dataclasses import dataclass

from app.processors.pdf_parser import PageContent, ParsedPDF


@dataclass
class ParsedSection:
    title: str
    level: int
    section_type: str
    page_start: int | None
    page_end: int | None
    order_index: int
    content: str
    children: list["ParsedSection"]


class StructureParser:
    """Identify section headings and build a document outline."""

    # Common section heading patterns
    HEADING_PATTERNS = [
        # Numbered: "1 Introduction", "2. Related Work", "3.1 Method"
        re.compile(r"^(\d+(?:\.\d+)*)\s+([A-Z][A-Za-z\s:,\-]+)$"),
        # Explicit: "Abstract", "References", "Acknowledgments"
        re.compile(r"^(Abstract|References|Acknowledgments?|Appendix|Bibliography)$", re.I),
        # ALL CAPS headings (some papers)
        re.compile(r"^([A-Z][A-Z\s]{3,})$"),
    ]

    def parse(self, parsed_pdf: ParsedPDF) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        current_section: ParsedSection | None = None
        order = 0

        for page in parsed_pdf.pages:
            for line in page.text.split("\n"):
                line = line.strip()
                if not line or len(line) > 100:
                    if current_section:
                        current_section.content += line + "\n"
                    continue

                heading = self._match_heading(line)
                if heading:
                    if current_section:
                        sections.append(current_section)

                    title, level, section_type = heading
                    current_section = ParsedSection(
                        title=title,
                        level=level,
                        section_type=section_type,
                        page_start=page.page_number,
                        page_end=None,
                        order_index=order,
                        content="",
                        children=[],
                    )
                    order += 1
                elif current_section:
                    current_section.content += line + "\n"

        if current_section:
            sections.append(current_section)

        # Set page_end for each section (start of next section - 1)
        for i, sec in enumerate(sections):
            if i + 1 < len(sections):
                sec.page_end = (sections[i + 1].page_start or sec.page_start)
            else:
                sec.page_end = parsed_pdf.page_count

        return sections

    def _match_heading(self, line: str) -> tuple[str, int, str] | None:
        """Try to match a line as a section heading."""
        # Check explicit section names
        if line.lower() in ("abstract", "references", "acknowledgments", "acknowledgement", "bibliography"):
            level = 0 if line.lower() == "abstract" else 0
            return line, level, line.lower()

        # Check numbered headings: "1 Introduction", "3.2 Proposed Method"
        match = self.HEADING_PATTERNS[0].match(line)
        if match:
            number = match.group(1)
            title = match.group(2).strip()
            level = number.count(".")
            section_type = "section" if level == 0 else "subsection"
            return f"{number} {title}", level, section_type

        # Check ALL CAPS (but skip if too short or likely not a heading)
        if len(line) > 4 and line.isupper() and not line.isdigit():
            return line, 0, "section"

        return None


structure_parser = StructureParser()
