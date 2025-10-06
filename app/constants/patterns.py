"""Compiled regex patterns for content extraction and scoring

This module contains all regex patterns used by:
- PreFilter (app/filters/pre_filter.py) - Article-level data detection
- ClaimExtractor (app/nlp/claim_extractor.py) - Sentence-level claim extraction
"""
import re

# ============================================================================
# DATA DETECTION PATTERNS
# ============================================================================
PERCENTAGE_PATTERN = re.compile(r'\d+([,\.]\d+)?%')
CURRENCY_BRL_PATTERN = re.compile(r'r\$\s*[\d\.,]+\s*(mil|milhões|bilhões|milhão|bilhão)?', re.IGNORECASE)
CURRENCY_USD_PATTERN = re.compile(r'us\$\s*[\d\.,]+\s*(mil|milhões|bilhões|milhão|bilhão)?', re.IGNORECASE)
LARGE_NUMBER_PATTERN = re.compile(r'\d+\s*(mil|milhões|bilhões|milhão|bilhão)', re.IGNORECASE)
DATE_PATTERN = re.compile(r'\d{1,2}\s+de\s+(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)', re.IGNORECASE)
YEAR_PATTERN = re.compile(r'\b(19|20)\d{2}\b')
NUMBER_PATTERN = re.compile(r'\d+')
SENTENCE_DELIMITER_PATTERN = re.compile(r'[.!?]')

# ============================================================================
# CONDITIONAL/SPECULATION PATTERNS
# ============================================================================
# Conditional/future statements (not fact-checkable)
CONDITIONAL_PATTERN = re.compile(
    r'\b(se acontecer|caso ocorra|haveremos de|iremos|vamos fazer|poderá|'
    r'poderia|teria|seria|faria|quando houver)\b',
    re.IGNORECASE
)

# ============================================================================
# NOISE PATTERNS (to skip sentences entirely)
# ============================================================================
NOISE_PATTERNS = [
    re.compile(r'clique (aqui|para)|saiba mais|leia (também|mais)', re.IGNORECASE),
    re.compile(r'veja (também|mais|galeria|vídeo)|confira|assista', re.IGNORECASE),
    re.compile(r'(whatsapp|facebook|instagram|twitter|telegram)', re.IGNORECASE),
    re.compile(r'compartilhe|curta|inscreva-se|siga (o|a|nosso)', re.IGNORECASE),
    re.compile(r'foto:|imagem:|crédito:|reprodução|divulgação', re.IGNORECASE),
    re.compile(r'baixe o app|download|📱|aplicativo g1', re.IGNORECASE),  # App CTAs
]

# ============================================================================
# CLAIM ATTRIBUTION PATTERNS (Portuguese)
# ============================================================================

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

# Pattern 7: Direct quotes with context
# Example: "O ministro disse: 'Vamos investir R$ 100 milhões'"
PATTERN_DIRECT_QUOTE = re.compile(
    r'["""\']\s*([^"""\']{20,})\s*["""\']',
    re.IGNORECASE
)

# Pattern 8: Verifiable affirmations (statements with data but no direct attribution)
# Example: "A inflação atingiu 10% em dezembro"
# Must have: subject + verb + verifiable data (number/percentage/currency)
PATTERN_DATA_AFFIRMATION = re.compile(
    r'\b(atingiu|alcançou|registrou|chegou|caiu|subiu|aumentou|diminuiu|cresceu|reduziu)\b',
    re.IGNORECASE
)
