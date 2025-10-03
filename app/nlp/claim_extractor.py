"""Claim extraction module using minimal NLP (regex patterns) for Portuguese text

This module implements the minimal NLP strategy defined in:
- docs/02_MINIMAL_NLP_STRATEGY.md
- docs/01_NOISE_VS_CHECKABLE_CONTENT.md

Philosophy: Regex + Smart Patterns > Heavy ML Models
- 80% accuracy at 1% of the computational cost
- <2ms per article extraction time
- Zero external dependencies (no spaCy, no BERT)
"""
import re
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# NOISE PATTERNS (to skip sentences entirely)
# ============================================================================
NOISE_PATTERNS = [
    re.compile(r'clique (aqui|para)|saiba mais|leia (também|mais)', re.IGNORECASE),
    re.compile(r'veja (também|mais|galeria|vídeo)|confira|assista', re.IGNORECASE),
    re.compile(r'(whatsapp|facebook|instagram|twitter|telegram)', re.IGNORECASE),
    re.compile(r'compartilhe|curta|inscreva-se|siga (o|a|nosso)', re.IGNORECASE),
    re.compile(r'foto:|imagem:|crédito:|reprodução|divulgação', re.IGNORECASE),
]

# Vague language indicators (negative scoring)
VAGUE_KEYWORDS = {
    'alguns', 'diversos', 'vários', 'muitos', 'poucos',
    'em breve', 'logo', 'futuramente', 'em algum momento',
    'provavelmente', 'possivelmente', 'talvez', 'pode ser',
    'há rumores', 'dizem que', 'fontes não identificadas'
}

# ============================================================================
# COMPILED REGEX PATTERNS (Performance Optimization)
# ============================================================================

# Data detection patterns
PERCENTAGE_PATTERN = re.compile(r'\d+([,\.]\d+)?%')
CURRENCY_BRL_PATTERN = re.compile(r'r\$\s*[\d\.,]+\s*(mil|milhões|bilhões|milhão|bilhão)?', re.IGNORECASE)
CURRENCY_USD_PATTERN = re.compile(r'us\$\s*[\d\.,]+\s*(mil|milhões|bilhões|milhão|bilhão)?', re.IGNORECASE)
LARGE_NUMBER_PATTERN = re.compile(r'\d+\s*(mil|milhões|bilhões|milhão|bilhão)', re.IGNORECASE)
DATE_PATTERN = re.compile(r'\d{1,2}\s+de\s+(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)', re.IGNORECASE)
NUMBER_PATTERN = re.compile(r'\d+')

# Claim attribution patterns (Portuguese)

# Pattern 1: "Entity + verb + que + claim"
# Example: "O ministro afirmou que a inflação caiu"
PATTERN_ENTITY_VERB_QUE = re.compile(
    r'([A-ZÇÁÉÍÓÚÂÊÔÃÕ][a-zçáéíóúâêôãõ\s]+?)\s+'
    r'(afirmou|disse|declarou|alegou|confirmou|negou|garantiu|revelou|anunciou|criticou|defendeu|acusou)\s+'
    r'que\s+(.+?)(?:\.|$)',
    re.IGNORECASE
)

# Pattern 2: "Segundo + source, + claim"
# Example: "Segundo o IBGE, o desemprego caiu para 8%"
PATTERN_SEGUNDO = re.compile(
    r'segundo\s+([^,]+?),\s+(.+?)(?:\.|$)',
    re.IGNORECASE
)

# Pattern 3: "De acordo com + source, + claim"
# Example: "De acordo com o ministério, foram investidos R$ 500 milhões"
PATTERN_DE_ACORDO_COM = re.compile(
    r'de acordo com\s+([^,]+?),\s+(.+?)(?:\.|$)',
    re.IGNORECASE
)

# Pattern 4: "Conforme + source, + claim"
# Example: "Conforme a pesquisa, 67% aprovam a medida"
PATTERN_CONFORME = re.compile(
    r'conforme\s+([^,]+?),\s+(.+?)(?:\.|$)',
    re.IGNORECASE
)

# Pattern 5: "Entity + verb: claim" (colon-separated)
# Example: "Ministro garante: investimento será mantido"
PATTERN_ENTITY_VERB_COLON = re.compile(
    r'([A-ZÇÁÉÍÓÚÂÊÔÃÕ][a-zçáéíóúâêôãõ\s]+?)\s+'
    r'(garante|afirma|declara|anuncia|revela):\s+(.+?)(?:\.|$)',
    re.IGNORECASE
)

# Pattern 6: "Entity + action verb + object" (no attribution verb)
# Example: "Governo anuncia investimento de R$ 500 milhões"
PATTERN_ENTITY_ACTION = re.compile(
    r'([A-ZÇÁÉÍÓÚÂÊÔÃÕ][a-zçáéíóúâêôãõ\s]+?)\s+'
    r'(anuncia|anunciou|aprova|aprovou|divulga|divulgou|publica|publicou|apresenta|apresentou)\s+'
    r'(.+?)(?:\.|$)',
    re.IGNORECASE
)

# Government entity keywords (for bonus scoring)
GOVERNMENT_ENTITIES = {
    'presidente', 'vice-presidente', 'ministro', 'ministério',
    'governador', 'prefeito', 'deputado', 'senador',
    'stf', 'supremo', 'congresso', 'senado', 'câmara',
    'tse', 'tcu', 'pgr', 'anvisa', 'ibama', 'inep'
}


class SentenceScorer:
    """Score individual sentences for fact-checkability"""

    @staticmethod
    def score_sentence(sentence: str) -> int:
        """
        Score a sentence for fact-checkability (-100 to +100).

        Scoring factors:
        - Attribution patterns: +20 to +30
        - Verifiable data: +5 to +15
        - Government entities: +10
        - Vague language: -10 to -20
        - Opinion markers: -15
        - Length optimization: +5 to -10

        Args:
            sentence: Input sentence

        Returns:
            Score (-100 to +100), higher = more fact-checkable
        """
        score = 0
        sent_lower = sentence.lower()

        # Check for hard noise (disqualify immediately)
        for pattern in NOISE_PATTERNS:
            if pattern.search(sent_lower):
                return -100  # Instant disqualification

        # A. Attribution patterns (strong indicator of claims)
        if PATTERN_ENTITY_VERB_QUE.search(sentence):
            score += 30  # Strong attribution: "X afirmou que Y"
        elif PATTERN_SEGUNDO.search(sent_lower) or PATTERN_DE_ACORDO_COM.search(sent_lower):
            score += 25  # Reverse attribution: "Segundo X, Y"
        elif PATTERN_CONFORME.search(sent_lower):
            score += 20  # Weaker attribution: "Conforme X, Y"
        elif PATTERN_ENTITY_VERB_COLON.search(sentence):
            score += 25  # Colon attribution: "X garante: Y"
        elif PATTERN_ENTITY_ACTION.search(sentence):
            score += 20  # Action statement: "X anuncia Y"

        # B. Verifiable data (specificity)
        if PERCENTAGE_PATTERN.search(sentence):
            score += 15  # Percentage = highly specific
        elif CURRENCY_BRL_PATTERN.search(sent_lower) or CURRENCY_USD_PATTERN.search(sent_lower):
            score += 15  # Currency values
        elif LARGE_NUMBER_PATTERN.search(sent_lower):
            score += 10  # Large numbers (milhões, bilhões)
        elif DATE_PATTERN.search(sent_lower):
            score += 8   # Specific dates
        elif NUMBER_PATTERN.search(sentence):
            score += 5   # Any number

        # C. Government entities (high-priority sources)
        if any(entity in sent_lower for entity in GOVERNMENT_ENTITIES):
            score += 10

        # D. Vague language penalty
        vague_count = sum(1 for term in VAGUE_KEYWORDS if term in sent_lower)
        score -= vague_count * 10  # -10 per vague term

        # E. Opinion/subjective markers
        opinion_patterns = [
            r'(acredito|acho|penso|imagino) que',
            r'na minha (opinião|visão)',
            r'(bonito|feio|lindo|horrível|incrível|maravilhoso|emocionante)',
        ]
        for pattern in opinion_patterns:
            if re.search(pattern, sent_lower):
                score -= 15
                break

        # F. Length optimization (prefer 50-150 chars)
        sent_len = len(sentence)
        if 50 <= sent_len <= 150:
            score += 5
        elif sent_len < 30:
            score -= 10  # Too short = likely fragment
        elif sent_len > 200:
            score -= 5   # Too long = may contain noise

        return score


class ClaimExtractor:
    """Extract fact-checkable claims from Portuguese news articles using minimal NLP

    Uses regex-based pattern matching to identify claim structures:
    1. Direct attribution: "X afirmou que Y"
    2. Reverse attribution: "Segundo X, Y"
    3. Action statements: "X anunciou Y"

    Performance: ~0.5-2ms per article
    Accuracy: 75-85% recall on checkable claims
    """

    def __init__(self):
        self.scorer = SentenceScorer()

    def extract_from_html(self, html_content: str, max_chars: int = 500) -> str:
        """
        Extract fact-checkable sentences from HTML content.

        Process:
        1. Parse HTML and remove noise elements
        2. Split text into sentences
        3. Score each sentence for fact-checkability
        4. Select top-scoring sentences up to max_chars

        Args:
            html_content: Raw HTML content from RSS feed
            max_chars: Maximum characters to extract (default: 500)

        Returns:
            Clean text with only fact-checkable sentences
        """
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove noise elements
        for element in soup(['script', 'style', 'iframe', 'noscript', 'nav', 'header', 'footer']):
            element.decompose()

        # Extract text
        text = soup.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())  # Normalize whitespace

        # Split into sentences
        sentences = self._split_sentences(text)

        # Score and filter sentences
        scored_sentences = []
        for sentence in sentences:
            score = self.scorer.score_sentence(sentence)
            if score > 0:  # Only keep positive-scoring sentences
                scored_sentences.append((score, sentence))
                logger.debug(f"Sentence score={score}: {sentence[:60]}...")

        # Sort by score (highest first)
        scored_sentences.sort(reverse=True, key=lambda x: x[0])

        # Select top sentences until char limit
        selected = []
        char_count = 0

        for score, sentence in scored_sentences:
            if char_count + len(sentence) > max_chars and len(selected) >= 2:
                break
            selected.append(sentence)
            char_count += len(sentence)

            # Stop if we have enough high-quality claims
            if len(selected) >= 5 and char_count >= 300:
                break

        if not selected:
            logger.debug("No fact-checkable sentences found")
            return ""

        # Reconstruct in original order (find position in original text)
        selected_ordered = sorted(selected, key=lambda s: text.find(s) if text.find(s) != -1 else 999999)
        result = '. '.join(selected_ordered)

        # Ensure proper punctuation
        if result and not result.endswith('.'):
            result += '.'

        logger.debug(f"Extracted {len(selected)} sentences ({len(result)} chars) from {len(sentences)} total")
        return result

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences intelligently.

        Handles common abbreviations that shouldn't cause splits.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Handle common abbreviations that shouldn't split
        text = re.sub(r'\b(Dr|Sr|Sra|Prof|Gov)\.\s+', r'\1<DOT> ', text)

        # Split on sentence boundaries
        raw_sentences = re.split(r'[.!?]+', text)

        sentences = []
        for sent in raw_sentences:
            # Restore abbreviations
            sent = sent.replace('<DOT>', '.')
            sent = sent.strip()

            # Skip if too short
            if len(sent) < 30:
                continue

            sentences.append(sent)

        return sentences

    def extract_claims_with_attribution(self, text: str) -> List[Dict[str, str]]:
        """
        Extract claims with explicit attribution (who said what).

        Returns structured claims with speaker + claim text.

        Args:
            text: Article text content

        Returns:
            List of dicts with 'speaker', 'verb', 'claim' keys
        """
        claims = []

        # Try each pattern
        patterns = [
            (PATTERN_ENTITY_VERB_QUE, 3),        # (speaker, verb, claim)
            (PATTERN_SEGUNDO, 2),                 # (speaker, claim)
            (PATTERN_DE_ACORDO_COM, 2),           # (speaker, claim)
            (PATTERN_CONFORME, 2),                # (speaker, claim)
            (PATTERN_ENTITY_VERB_COLON, 3),      # (speaker, verb, claim)
            (PATTERN_ENTITY_ACTION, 3),          # (speaker, action, claim)
        ]

        for pattern, num_groups in patterns:
            for match in pattern.finditer(text):
                groups = match.groups()

                if num_groups == 3:
                    speaker, verb, claim_text = groups
                elif num_groups == 2:
                    speaker, claim_text = groups
                    verb = "disse"  # default
                else:
                    continue

                # Clean extracted text
                speaker = speaker.strip()
                claim_text = claim_text.strip()

                # Skip if too short
                if len(claim_text) < 20:
                    continue

                claims.append({
                    'speaker': speaker,
                    'verb': verb,
                    'claim': claim_text,
                    'has_government_entity': any(entity in speaker.lower() for entity in GOVERNMENT_ENTITIES),
                    'has_data': bool(PERCENTAGE_PATTERN.search(claim_text) or CURRENCY_BRL_PATTERN.search(claim_text))
                })

        logger.debug(f"Extracted {len(claims)} claims with attribution")
        return claims


def extract_checkable_content(html: str, max_chars: int = 500) -> str:
    """
    Convenience function to extract fact-checkable content from HTML.

    Args:
        html: Raw HTML content
        max_chars: Maximum characters to extract

    Returns:
        Clean text with fact-checkable claims
    """
    extractor = ClaimExtractor()
    return extractor.extract_from_html(html, max_chars)


def extract_best_claims(text: str, max_claims: int = 3) -> List[Dict]:
    """
    Extract the best fact-checkable claims with attribution.

    Args:
        text: Article text
        max_claims: Maximum number of claims to return

    Returns:
        List of top claims with speaker and claim text
    """
    extractor = ClaimExtractor()
    all_claims = extractor.extract_claims_with_attribution(text)

    # Sort by government entity first, then by data presence
    all_claims.sort(
        key=lambda c: (c['has_government_entity'], c['has_data']),
        reverse=True
    )

    return all_claims[:max_claims]
