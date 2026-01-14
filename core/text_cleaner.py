"""
Text Cleaner Module
Prepares extracted text for TTS by cleaning and normalizing.
"""

import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class CleanerOptions:
    """Configuration options for text cleaning."""
    expand_abbreviations: bool = True
    handle_numbers: bool = True
    remove_urls: bool = True
    remove_emails: bool = True
    normalize_punctuation: bool = True
    handle_footnotes: bool = True
    max_pause_periods: int = 3  # Convert "..." beyond this to single pause
    add_chapter_announcement: bool = True


class TextCleaner:
    """
    Cleans and normalizes text for TTS output.
    Handles abbreviations, numbers, punctuation, and formatting.
    """

    # Common abbreviations and their expansions
    ABBREVIATIONS = {
        # Titles
        r'\bMr\.': 'Mister',
        r'\bMrs\.': 'Missus',
        r'\bMs\.': 'Miss',
        r'\bDr\.': 'Doctor',
        r'\bProf\.': 'Professor',
        r'\bSr\.': 'Senior',
        r'\bJr\.': 'Junior',
        r'\bSt\.': 'Saint',
        r'\bRev\.': 'Reverend',
        r'\bGen\.': 'General',
        r'\bCol\.': 'Colonel',
        r'\bCapt\.': 'Captain',
        r'\bLt\.': 'Lieutenant',
        r'\bSgt\.': 'Sergeant',

        # Common abbreviations
        r'\betc\.': 'et cetera',
        r'\be\.g\.': 'for example',
        r'\bi\.e\.': 'that is',
        r'\bvs\.': 'versus',
        r'\bvs\b': 'versus',
        r'\bno\.': 'number',
        r'\bNo\.': 'Number',
        r'\bvol\.': 'volume',
        r'\bVol\.': 'Volume',
        r'\bch\.': 'chapter',
        r'\bCh\.': 'Chapter',
        r'\bp\.': 'page',
        r'\bpp\.': 'pages',
        r'\bfig\.': 'figure',
        r'\bFig\.': 'Figure',
        r'\besp\.': 'especially',
        r'\bapprox\.': 'approximately',
        r'\bca\.': 'circa',

        # Time
        r'\ba\.m\.': 'A M',
        r'\bp\.m\.': 'P M',
        r'\bAM\b': 'A M',
        r'\bPM\b': 'P M',

        # Measurements (keep simple for TTS)
        r'\bft\.': 'feet',
        r'\bin\.': 'inches',
        r'\blb\.': 'pounds',
        r'\blbs\.': 'pounds',
        r'\boz\.': 'ounces',
        r'\bkm\b': 'kilometers',
        r'\bm\b(?=\s|$|[,\.])': 'meters',
        r'\bcm\b': 'centimeters',
        r'\bmm\b': 'millimeters',
        r'\bkg\b': 'kilograms',
        r'\bmph\b': 'miles per hour',
        r'\bkph\b': 'kilometers per hour',
    }

    # Number words for conversion
    ONES = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
            'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
            'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
    TENS = ['', '', 'twenty', 'thirty', 'forty', 'fifty',
            'sixty', 'seventy', 'eighty', 'ninety']

    def __init__(self, options: Optional[CleanerOptions] = None):
        self.options = options or CleanerOptions()

    def clean(self, text: str, chapter_title: Optional[str] = None) -> str:
        """
        Clean text for TTS output.

        Args:
            text: Raw text to clean
            chapter_title: Optional chapter title to announce

        Returns:
            Cleaned text ready for TTS
        """
        if not text:
            return ""

        result = text

        # Add chapter announcement if requested
        if self.options.add_chapter_announcement and chapter_title:
            result = f"{chapter_title}.\n\n{result}"

        # Remove URLs and emails first (before other processing)
        if self.options.remove_urls:
            result = self._remove_urls(result)

        if self.options.remove_emails:
            result = self._remove_emails(result)

        # Handle footnotes
        if self.options.handle_footnotes:
            result = self._handle_footnotes(result)

        # Expand abbreviations
        if self.options.expand_abbreviations:
            result = self._expand_abbreviations(result)

        # Handle numbers
        if self.options.handle_numbers:
            result = self._handle_numbers(result)

        # Normalize punctuation
        if self.options.normalize_punctuation:
            result = self._normalize_punctuation(result)

        # Final cleanup
        result = self._final_cleanup(result)

        return result

    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text."""
        # Match http/https URLs
        text = re.sub(
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            '',
            text
        )
        # Match www URLs
        text = re.sub(
            r'www\.[^\s<>"{}|\\^`\[\]]+',
            '',
            text
        )
        return text

    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text."""
        return re.sub(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            '',
            text
        )

    def _handle_footnotes(self, text: str) -> str:
        """Handle footnote markers and references."""
        # Remove superscript-style footnote markers [1], [2], etc.
        text = re.sub(r'\[\d+\]', '', text)

        # Remove footnote markers like ¹, ², ³
        text = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]+', '', text)

        # Remove asterisk footnotes
        text = re.sub(r'\*{1,3}(?!\*)', '', text)

        return text

    def _expand_abbreviations(self, text: str) -> str:
        """Expand common abbreviations."""
        for pattern, replacement in self.ABBREVIATIONS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _handle_numbers(self, text: str) -> str:
        """Convert numbers to spoken form for better TTS."""
        # Handle years (1900-2099)
        text = re.sub(
            r'\b(19|20)(\d{2})\b',
            lambda m: self._year_to_words(int(m.group(0))),
            text
        )

        # Handle currency
        text = re.sub(
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            lambda m: self._currency_to_words(m.group(1)),
            text
        )

        # Handle percentages
        text = re.sub(
            r'(\d+(?:\.\d+)?)\s*%',
            lambda m: f"{self._number_to_words(m.group(1))} percent",
            text
        )

        # Handle ordinals (1st, 2nd, 3rd, etc.)
        text = re.sub(
            r'\b(\d+)(st|nd|rd|th)\b',
            lambda m: self._ordinal_to_words(int(m.group(1))),
            text
        )

        # Handle time (12:30, 3:45 PM)
        text = re.sub(
            r'\b(\d{1,2}):(\d{2})\b',
            lambda m: self._time_to_words(m.group(1), m.group(2)),
            text
        )

        # Handle remaining plain numbers (keep reasonable sizes)
        text = re.sub(
            r'\b(\d{1,4})\b',
            lambda m: self._number_to_words(m.group(1)),
            text
        )

        return text

    def _number_to_words(self, num_str: str) -> str:
        """Convert a number string to words."""
        try:
            # Handle decimals
            if '.' in num_str:
                parts = num_str.split('.')
                whole = self._int_to_words(int(parts[0].replace(',', '')))
                decimal = ' point ' + ' '.join(
                    self._int_to_words(int(d)) for d in parts[1]
                )
                return whole + decimal

            return self._int_to_words(int(num_str.replace(',', '')))
        except ValueError:
            return num_str

    def _int_to_words(self, n: int) -> str:
        """Convert integer to words."""
        if n < 0:
            return 'negative ' + self._int_to_words(-n)
        if n < 20:
            return self.ONES[n] if n > 0 else 'zero'
        if n < 100:
            tens, ones = divmod(n, 10)
            return self.TENS[tens] + ('' if ones == 0 else ' ' + self.ONES[ones])
        if n < 1000:
            hundreds, remainder = divmod(n, 100)
            result = self.ONES[hundreds] + ' hundred'
            if remainder:
                result += ' ' + self._int_to_words(remainder)
            return result
        if n < 1000000:
            thousands, remainder = divmod(n, 1000)
            result = self._int_to_words(thousands) + ' thousand'
            if remainder:
                result += ' ' + self._int_to_words(remainder)
            return result
        # For very large numbers, just return digits
        return str(n)

    def _year_to_words(self, year: int) -> str:
        """Convert year to spoken form."""
        if 2000 <= year <= 2009:
            return f"two thousand {'and ' + self.ONES[year - 2000] if year > 2000 else ''}"
        if 2010 <= year <= 2099:
            return f"twenty {self._int_to_words(year - 2000)}"
        if 1900 <= year <= 1999:
            first = year // 100
            second = year % 100
            return f"nineteen {self._int_to_words(second)}"
        return self._int_to_words(year)

    def _ordinal_to_words(self, n: int) -> str:
        """Convert ordinal number to words."""
        ordinal_suffix = {
            1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth',
            6: 'sixth', 7: 'seventh', 8: 'eighth', 9: 'ninth', 10: 'tenth',
            11: 'eleventh', 12: 'twelfth', 13: 'thirteenth', 14: 'fourteenth',
            15: 'fifteenth', 16: 'sixteenth', 17: 'seventeenth', 18: 'eighteenth',
            19: 'nineteenth', 20: 'twentieth', 30: 'thirtieth', 40: 'fortieth',
            50: 'fiftieth', 60: 'sixtieth', 70: 'seventieth', 80: 'eightieth',
            90: 'ninetieth', 100: 'hundredth'
        }

        if n in ordinal_suffix:
            return ordinal_suffix[n]

        if n < 100:
            tens, ones = divmod(n, 10)
            if ones == 0:
                return ordinal_suffix.get(n, f"{self._int_to_words(n)}th")
            return self.TENS[tens] + ' ' + ordinal_suffix[ones]

        return f"{self._int_to_words(n)}th"

    def _currency_to_words(self, amount: str) -> str:
        """Convert currency to spoken form."""
        amount = amount.replace(',', '')
        if '.' in amount:
            dollars, cents = amount.split('.')
            result = self._int_to_words(int(dollars)) + ' dollars'
            if int(cents) > 0:
                result += ' and ' + self._int_to_words(int(cents)) + ' cents'
            return result
        return self._int_to_words(int(amount)) + ' dollars'

    def _time_to_words(self, hour: str, minute: str) -> str:
        """Convert time to spoken form."""
        h = int(hour)
        m = int(minute)

        if m == 0:
            return f"{self._int_to_words(h)} o'clock"
        if m == 30:
            return f"half past {self._int_to_words(h)}"
        if m == 15:
            return f"quarter past {self._int_to_words(h)}"
        if m == 45:
            return f"quarter to {self._int_to_words(h + 1)}"

        return f"{self._int_to_words(h)} {self._int_to_words(m)}"

    def _normalize_punctuation(self, text: str) -> str:
        """Normalize punctuation for better TTS."""
        # Convert fancy quotes to simple ones
        text = re.sub(r'[""„]', '"', text)
        text = re.sub(r"[''‚]", "'", text)

        # Convert em/en dashes to pauses (commas or periods)
        text = re.sub(r'[—–]', ', ', text)

        # Handle ellipsis
        text = re.sub(r'\.{3,}', '...', text)  # Normalize to three dots
        text = re.sub(r'…', '...', text)  # Unicode ellipsis

        # Remove multiple exclamation/question marks
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\?{2,}', '?', text)

        # Handle parentheses - convert to commas for natural pauses
        text = re.sub(r'\s*\(\s*', ', ', text)
        text = re.sub(r'\s*\)\s*', ', ', text)

        # Handle brackets
        text = re.sub(r'\s*\[\s*', ', ', text)
        text = re.sub(r'\s*\]\s*', ', ', text)

        # Remove angle brackets and their content (likely HTML remnants)
        text = re.sub(r'<[^>]+>', '', text)

        # Normalize spacing around punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        text = re.sub(r'([.,!?;:])\s*([.,!?;:])', r'\1 \2', text)

        return text

    def _final_cleanup(self, text: str) -> str:
        """Final cleanup pass."""
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)

        # Remove multiple newlines (keep max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove spaces at beginning/end of lines
        text = re.sub(r'^ +', '', text, flags=re.MULTILINE)
        text = re.sub(r' +$', '', text, flags=re.MULTILINE)

        # Ensure sentences end with proper punctuation for pacing
        text = re.sub(r'(\w)\n', r'\1.\n', text)

        # Remove any remaining control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

        return text.strip()
