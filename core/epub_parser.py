"""
ePub Parser Module
Extracts text content, chapters, and metadata from ePub files.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


@dataclass
class Chapter:
    """Represents a single chapter from an ePub."""
    number: int
    title: str
    content: str  # Plain text content
    html_content: str = ""  # Original HTML
    file_name: str = ""
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.content.split())


@dataclass
class BookMetadata:
    """Metadata extracted from ePub."""
    title: str = "Unknown Title"
    author: str = "Unknown Author"
    language: str = "en"
    publisher: str = ""
    description: str = ""
    cover_image: Optional[bytes] = None
    cover_mime_type: str = "image/jpeg"
    identifier: str = ""


class EPubParser:
    """
    Parser for ePub files.
    Extracts chapters, text content, and metadata.
    """

    def __init__(self, epub_path: str):
        self.epub_path = Path(epub_path)
        if not self.epub_path.exists():
            raise FileNotFoundError(f"ePub file not found: {epub_path}")
        if not self.epub_path.suffix.lower() == '.epub':
            raise ValueError(f"File is not an ePub: {epub_path}")

        self.book: Optional[epub.EpubBook] = None
        self.metadata: Optional[BookMetadata] = None
        self.chapters: list[Chapter] = []

    def parse(self) -> 'EPubParser':
        """Parse the ePub file and extract all content."""
        self.book = epub.read_epub(str(self.epub_path))
        self._extract_metadata()
        self._extract_chapters()
        return self

    def _extract_metadata(self) -> None:
        """Extract book metadata."""
        if not self.book:
            return

        self.metadata = BookMetadata()

        # Title
        title = self.book.get_metadata('DC', 'title')
        if title:
            self.metadata.title = title[0][0]

        # Author
        creator = self.book.get_metadata('DC', 'creator')
        if creator:
            self.metadata.author = creator[0][0]

        # Language
        language = self.book.get_metadata('DC', 'language')
        if language:
            self.metadata.language = language[0][0]

        # Publisher
        publisher = self.book.get_metadata('DC', 'publisher')
        if publisher:
            self.metadata.publisher = publisher[0][0]

        # Description
        description = self.book.get_metadata('DC', 'description')
        if description:
            self.metadata.description = description[0][0]

        # Identifier (ISBN, etc.)
        identifier = self.book.get_metadata('DC', 'identifier')
        if identifier:
            self.metadata.identifier = identifier[0][0]

        # Cover image
        self._extract_cover()

    def _extract_cover(self) -> None:
        """Extract cover image from ePub."""
        if not self.book or not self.metadata:
            return

        # Try to find cover in metadata
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_COVER:
                self.metadata.cover_image = item.get_content()
                self.metadata.cover_mime_type = item.media_type
                return

        # Try to find cover by name/id patterns
        cover_patterns = ['cover', 'cover-image', 'coverimage']
        for item in self.book.get_items_of_type(ebooklib.ITEM_IMAGE):
            item_name = item.get_name().lower()
            if any(pattern in item_name for pattern in cover_patterns):
                self.metadata.cover_image = item.get_content()
                self.metadata.cover_mime_type = item.media_type
                return

    def _extract_chapters(self) -> None:
        """Extract chapters from ePub."""
        if not self.book:
            return

        self.chapters = []
        chapter_num = 0

        # Get spine order (reading order)
        spine_items = []
        for item_id, linear in self.book.spine:
            item = self.book.get_item_with_id(item_id)
            if item:
                spine_items.append(item)

        # If no spine, fall back to document items
        if not spine_items:
            spine_items = list(self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

        # Build TOC lookup for chapter titles
        toc_titles = self._build_toc_lookup()

        for item in spine_items:
            if item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue

            html_content = item.get_content().decode('utf-8', errors='ignore')
            text_content = self._html_to_text(html_content)

            # Skip empty or very short content (likely front matter)
            if len(text_content.strip()) < 50:
                continue

            chapter_num += 1

            # Try to get title from TOC, then from content
            file_name = item.get_name()
            title = toc_titles.get(file_name, "")

            if not title:
                title = self._extract_chapter_title(html_content, text_content)

            if not title:
                title = f"Chapter {chapter_num}"

            chapter = Chapter(
                number=chapter_num,
                title=title,
                content=text_content,
                html_content=html_content,
                file_name=file_name
            )
            self.chapters.append(chapter)

    def _build_toc_lookup(self) -> dict[str, str]:
        """Build a lookup dict from file names to TOC titles."""
        toc_titles = {}

        def process_toc_item(item):
            if isinstance(item, tuple):
                section, children = item
                if hasattr(section, 'href') and hasattr(section, 'title'):
                    # Remove fragment identifier from href
                    href = section.href.split('#')[0]
                    toc_titles[href] = section.title
                for child in children:
                    process_toc_item(child)
            elif hasattr(item, 'href') and hasattr(item, 'title'):
                href = item.href.split('#')[0]
                toc_titles[href] = item.title

        if self.book:
            for item in self.book.toc:
                process_toc_item(item)

        return toc_titles

    def _extract_chapter_title(self, html: str, text: str) -> str:
        """Extract chapter title from HTML content."""
        soup = BeautifulSoup(html, 'lxml')

        # Try heading tags in order of preference
        for tag in ['h1', 'h2', 'h3', 'title']:
            heading = soup.find(tag)
            if heading:
                title = heading.get_text(strip=True)
                if title and len(title) < 200:  # Reasonable title length
                    return title

        # Fall back to first line of text
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line) < 100:
                return first_line

        return ""

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        soup = BeautifulSoup(html, 'lxml')

        # Remove script and style elements
        for element in soup(['script', 'style', 'head', 'meta', 'link']):
            element.decompose()

        # Handle special elements
        # Convert <br> to newlines
        for br in soup.find_all('br'):
            br.replace_with('\n')

        # Add newlines after block elements
        block_tags = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                      'li', 'tr', 'blockquote', 'section', 'article']
        for tag in soup.find_all(block_tags):
            tag.append('\n')

        # Get text
        text = soup.get_text(separator=' ')

        # Clean up whitespace
        text = re.sub(r'[ \t]+', ' ', text)  # Collapse horizontal whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
        text = re.sub(r' +\n', '\n', text)  # Remove trailing spaces
        text = re.sub(r'\n +', '\n', text)  # Remove leading spaces after newlines

        return text.strip()

    def get_total_word_count(self) -> int:
        """Get total word count across all chapters."""
        return sum(ch.word_count for ch in self.chapters)

    def get_estimated_duration(self, words_per_minute: int = 150) -> int:
        """Estimate audiobook duration in seconds."""
        total_words = self.get_total_word_count()
        return int((total_words / words_per_minute) * 60)
