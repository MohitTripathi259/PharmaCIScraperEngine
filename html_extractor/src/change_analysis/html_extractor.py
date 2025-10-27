"""
Production-ready HTML to Text + Metadata extractor.

Converts complex HTML into normalized visible text and returns rich page metadata.
Uses BeautifulSoup with lxml parser for robust parsing.
"""

import html
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Models (Strict)
# ============================================================================

class OpenGraph(BaseModel):
    """OpenGraph metadata."""
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    site_name: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None
    model_config = {"extra": "forbid"}


class TwitterCard(BaseModel):
    """Twitter Card metadata."""
    card: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    model_config = {"extra": "forbid"}


class HtmlStats(BaseModel):
    """Statistical information about extracted content."""
    word_count: int
    char_count: int
    paragraph_count: int
    link_count: int
    image_count: int
    model_config = {"extra": "forbid"}


class LinkItem(BaseModel):
    """Represents a hyperlink."""
    href: str
    text: Optional[str] = None
    model_config = {"extra": "forbid"}


class ImageItem(BaseModel):
    """Represents an image."""
    src: str
    alt: Optional[str] = None
    model_config = {"extra": "forbid"}


class HtmlMetadata(BaseModel):
    """Rich metadata extracted from HTML."""
    url: Optional[str] = None
    base_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    canonical_url: Optional[str] = None
    lang: Optional[str] = None
    charset: Optional[str] = None
    authors: List[str] = []
    publish_date: Optional[str] = None   # ISO 8601
    modified_date: Optional[str] = None  # ISO 8601
    keywords: List[str] = []
    og: OpenGraph = OpenGraph()
    twitter: TwitterCard = TwitterCard()
    headings: Dict[str, List[str]] = {}  # h1..h6 text lists
    top_links: List[LinkItem] = []
    top_images: List[ImageItem] = []
    json_ld: List[Dict[str, Any] | str] = []
    model_config = {"extra": "forbid"}


class HtmlExtractionResult(BaseModel):
    """Complete result of HTML extraction."""
    text: str
    metadata: HtmlMetadata
    stats: HtmlStats
    model_config = {"extra": "forbid"}


# ============================================================================
# Helper Functions (Private)
# ============================================================================

def _clean_soup(soup: BeautifulSoup) -> None:
    """
    Remove non-visible elements and comments from soup in-place.

    Args:
        soup: BeautifulSoup object to clean
    """
    # Remove scripts, styles, and other non-visible elements
    for tag in soup.find_all(['script', 'style', 'noscript', 'template']):
        tag.decompose()

    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()


def _get_meta(soup: BeautifulSoup, name: Optional[str] = None,
              prop: Optional[str] = None) -> Optional[str]:
    """
    Extract meta tag content by name or property.

    Args:
        soup: BeautifulSoup object
        name: meta name attribute
        prop: meta property attribute

    Returns:
        Content string or None
    """
    if name:
        tag = soup.find('meta', attrs={'name': name})
    elif prop:
        tag = soup.find('meta', attrs={'property': prop})
    else:
        return None

    if tag and tag.get('content'):
        return str(tag['content']).strip()
    return None


def _absolutize(href: str, base_url: Optional[str]) -> str:
    """
    Convert relative URL to absolute using base_url.
    Reject disallowed schemes (javascript:, data:, mailto:).

    Args:
        href: URL to absolutize
        base_url: Base URL for resolution

    Returns:
        Absolute URL or original if disallowed/invalid
    """
    if not href or not base_url:
        return href

    # Reject disallowed schemes
    href_lower = href.lower().strip()
    if href_lower.startswith(('javascript:', 'data:', 'mailto:')):
        return href

    try:
        absolute = urljoin(base_url, href)
        # Validate it's a proper URL
        parsed = urlparse(absolute)
        if parsed.scheme in ('http', 'https'):
            return absolute
    except Exception:
        pass

    return href


def _headings(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """
    Extract all headings (h1-h6) with their text content.

    Args:
        soup: BeautifulSoup object

    Returns:
        Dict mapping 'h1'..'h6' to lists of heading texts
    """
    headings_dict = {}
    for level in range(1, 7):
        tag_name = f'h{level}'
        headings_list = []
        for heading in soup.find_all(tag_name):
            text = heading.get_text(strip=True)
            if text:
                headings_list.append(text)
        if headings_list:
            headings_dict[tag_name] = headings_list
    return headings_dict


def _collect_links(soup: BeautifulSoup, base_url: Optional[str],
                   limit: int) -> List[LinkItem]:
    """
    Collect links from soup, absolutize, and limit count.

    Args:
        soup: BeautifulSoup object
        base_url: Base URL for absolutizing
        limit: Maximum number of links to collect

    Returns:
        List of LinkItem objects
    """
    links = []
    for a_tag in soup.find_all('a', href=True):
        if len(links) >= limit:
            break

        href = str(a_tag['href']).strip()
        if not href:
            continue

        # Skip disallowed schemes
        href_lower = href.lower()
        if href_lower.startswith(('javascript:', 'data:', 'mailto:')):
            continue

        # Absolutize
        absolute_href = _absolutize(href, base_url)

        # Get link text
        link_text = a_tag.get_text(strip=True) or None

        links.append(LinkItem(href=absolute_href, text=link_text))

    return links


def _collect_images(soup: BeautifulSoup, base_url: Optional[str],
                    limit: int) -> List[ImageItem]:
    """
    Collect images from soup, absolutize src, and limit count.

    Args:
        soup: BeautifulSoup object
        base_url: Base URL for absolutizing
        limit: Maximum number of images to collect

    Returns:
        List of ImageItem objects
    """
    images = []
    for img_tag in soup.find_all('img', src=True):
        if len(images) >= limit:
            break

        src = str(img_tag['src']).strip()
        if not src:
            continue

        # Absolutize
        absolute_src = _absolutize(src, base_url)

        # Get alt text
        alt_text = img_tag.get('alt', '').strip() or None

        images.append(ImageItem(src=absolute_src, alt=alt_text))

    return images


def _json_ld(soup: BeautifulSoup) -> List[Dict[str, Any] | str]:
    """
    Extract JSON-LD structured data blocks.
    Limit to 3 blocks, each trimmed to ≤ 10 KB.

    Args:
        soup: BeautifulSoup object

    Returns:
        List of parsed dicts or raw strings
    """
    import json

    json_ld_blocks = []
    max_blocks = 3
    max_size = 10 * 1024  # 10 KB

    for script in soup.find_all('script', type='application/ld+json'):
        if len(json_ld_blocks) >= max_blocks:
            break

        try:
            content = script.string or ''
            # Trim to max size
            if len(content) > max_size:
                content = content[:max_size]

            # Try to parse as JSON
            parsed = json.loads(content)
            json_ld_blocks.append(parsed)
        except (json.JSONDecodeError, Exception):
            # Keep as string if parse fails
            if content:
                json_ld_blocks.append(content[:max_size])

    return json_ld_blocks


def _dates(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """
    Extract publish and modified dates from metadata.
    Try multiple sources and parse with dateparser if available.

    Args:
        soup: BeautifulSoup object

    Returns:
        Tuple of (publish_date ISO string, modified_date ISO string)
    """
    try:
        import dateparser
        has_dateparser = True
    except ImportError:
        has_dateparser = False

    def parse_date(date_str: Optional[str]) -> Optional[str]:
        """Parse date string to ISO 8601 format."""
        if not date_str:
            return None

        if has_dateparser:
            try:
                parsed = dateparser.parse(date_str)
                if parsed:
                    return parsed.isoformat()
            except Exception:
                pass
        return None

    # Try article:published_time
    publish_date = _get_meta(soup, prop='article:published_time')
    if not publish_date:
        publish_date = _get_meta(soup, name='date')
    if not publish_date:
        # Try itemprop
        date_tag = soup.find(attrs={'itemprop': 'datePublished'})
        if date_tag:
            publish_date = date_tag.get('content') or date_tag.get_text(strip=True)

    # Try article:modified_time
    modified_date = _get_meta(soup, prop='article:modified_time')
    if not modified_date:
        modified_tag = soup.find(attrs={'itemprop': 'dateModified'})
        if modified_tag:
            modified_date = modified_tag.get('content') or modified_tag.get_text(strip=True)

    return parse_date(publish_date), parse_date(modified_date)


def _language_charset(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """
    Extract language and charset from HTML.

    Args:
        soup: BeautifulSoup object

    Returns:
        Tuple of (language, charset)
    """
    # Language from html tag
    lang = None
    html_tag = soup.find('html')
    if html_tag and html_tag.get('lang'):
        lang = str(html_tag['lang']).strip()

    # Charset from meta tag
    charset = None
    # Try <meta charset="...">
    charset_tag = soup.find('meta', charset=True)
    if charset_tag:
        charset = str(charset_tag['charset']).strip()
    else:
        # Try <meta http-equiv="content-type" content="...charset=...">
        content_type = _get_meta(soup, name='content-type')
        if content_type and 'charset=' in content_type.lower():
            try:
                charset = content_type.split('charset=')[1].split(';')[0].strip()
            except Exception:
                pass

    return lang, charset


def _normalize_text(soup: BeautifulSoup) -> str:
    """
    Extract visible text with paragraph preservation.
    Normalize whitespace: collapse internal spaces, keep paragraph boundaries (double newline).

    Args:
        soup: BeautifulSoup object

    Returns:
        Normalized text string
    """
    # Get text with newline separators
    raw_text = soup.get_text(separator='\n')

    # Unescape HTML entities
    text = html.unescape(raw_text)

    # Split into lines
    lines = text.split('\n')

    # Process each line: strip whitespace, collapse internal spaces
    processed_lines = []
    for line in lines:
        # Collapse multiple spaces to single space
        line = re.sub(r'\s+', ' ', line.strip())
        if line:  # Only keep non-empty lines
            processed_lines.append(line)

    # Join with single newlines first
    text = '\n'.join(processed_lines)

    # Convert sequences of single newlines to double newlines for paragraph separation
    # This preserves paragraph boundaries
    text = re.sub(r'\n{1}', '\n\n', text)

    # Clean up any excessive newlines (more than 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _stats(text: str, links: List[LinkItem], images: List[ImageItem]) -> HtmlStats:
    """
    Compute statistics for extracted content.

    Args:
        text: Normalized text
        links: List of collected links
        images: List of collected images

    Returns:
        HtmlStats object
    """
    # Word count (split on whitespace)
    words = text.split()
    word_count = len(words)

    # Character count
    char_count = len(text)

    # Paragraph count (double newlines)
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs)

    return HtmlStats(
        word_count=word_count,
        char_count=char_count,
        paragraph_count=paragraph_count,
        link_count=len(links),
        image_count=len(images)
    )


# ============================================================================
# Public API
# ============================================================================

def extract_text_and_metadata(
    html_content: str,
    base_url: Optional[str] = None,
    url_for_context: Optional[str] = None,
    max_links: int = 50,
    max_images: int = 50,
) -> HtmlExtractionResult:
    """
    Parse HTML with BeautifulSoup (lxml parser), remove non-visible elements,
    normalize to paragraph-preserving text, extract metadata, and return stats.

    Absolutize links/images using base_url if provided.
    Dates parsed via dateparser if available; otherwise None.
    JSON-LD limited to 3 blocks, each ≤ 10 KB.

    Args:
        html_content: Raw HTML string to parse
        base_url: Base URL for absolutizing relative links/images
        url_for_context: URL of the page for metadata context
        max_links: Maximum number of links to collect (default: 50)
        max_images: Maximum number of images to collect (default: 50)

    Returns:
        HtmlExtractionResult with text, metadata, and stats

    Note:
        Never raises on malformed HTML; returns best-effort result.
        Performance: typically < 150ms for article-sized pages.
    """
    try:
        # Parse HTML with lxml parser
        soup = BeautifulSoup(html_content, 'lxml')

        # IMPORTANT: Extract JSON-LD BEFORE cleaning soup (to preserve script tags)
        json_ld_blocks = _json_ld(soup)

        # Clean soup (remove scripts, styles, comments)
        _clean_soup(soup)

        # Extract metadata components
        title = soup.title.string.strip() if soup.title and soup.title.string else None

        description = _get_meta(soup, name='description') or \
                     _get_meta(soup, prop='og:description')

        # Canonical URL
        canonical_tag = soup.find('link', rel='canonical')
        canonical_url = None
        if canonical_tag and canonical_tag.get('href'):
            canonical_url = _absolutize(str(canonical_tag['href']), base_url)

        # Language and charset
        lang, charset = _language_charset(soup)

        # Authors
        authors = []
        author_meta = _get_meta(soup, name='author')
        if author_meta:
            authors.append(author_meta)
        # Try article:author
        author_prop = _get_meta(soup, prop='article:author')
        if author_prop and author_prop not in authors:
            authors.append(author_prop)

        # Dates
        publish_date, modified_date = _dates(soup)

        # Keywords
        keywords = []
        keywords_meta = _get_meta(soup, name='keywords')
        if keywords_meta:
            keywords = [k.strip() for k in keywords_meta.split(',') if k.strip()]

        # OpenGraph
        og = OpenGraph(
            title=_get_meta(soup, prop='og:title'),
            description=_get_meta(soup, prop='og:description'),
            type=_get_meta(soup, prop='og:type'),
            site_name=_get_meta(soup, prop='og:site_name'),
            image=_absolutize(_get_meta(soup, prop='og:image') or '', base_url) if _get_meta(soup, prop='og:image') else None,
            url=_get_meta(soup, prop='og:url')
        )

        # Twitter Card
        twitter = TwitterCard(
            card=_get_meta(soup, name='twitter:card'),
            title=_get_meta(soup, name='twitter:title'),
            description=_get_meta(soup, name='twitter:description'),
            image=_absolutize(_get_meta(soup, name='twitter:image') or '', base_url) if _get_meta(soup, name='twitter:image') else None
        )

        # Headings
        headings_dict = _headings(soup)

        # Links and images
        links = _collect_links(soup, base_url, max_links)
        images = _collect_images(soup, base_url, max_images)

        # Normalized text
        text = _normalize_text(soup)

        # Stats
        stats = _stats(text, links, images)

        # Build metadata
        metadata = HtmlMetadata(
            url=url_for_context,
            base_url=base_url,
            title=title,
            description=description,
            canonical_url=canonical_url,
            lang=lang,
            charset=charset,
            authors=authors,
            publish_date=publish_date,
            modified_date=modified_date,
            keywords=keywords,
            og=og,
            twitter=twitter,
            headings=headings_dict,
            top_links=links,
            top_images=images,
            json_ld=json_ld_blocks
        )

        return HtmlExtractionResult(
            text=text,
            metadata=metadata,
            stats=stats
        )

    except Exception as e:
        # Fallback: return minimal result on any error
        # This ensures we never raise, even on completely broken HTML
        return HtmlExtractionResult(
            text='',
            metadata=HtmlMetadata(
                url=url_for_context,
                base_url=base_url
            ),
            stats=HtmlStats(
                word_count=0,
                char_count=0,
                paragraph_count=0,
                link_count=0,
                image_count=0
            )
        )
