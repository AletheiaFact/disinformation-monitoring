"""Pre-filtering scoring logic for extracted content

This module implements the scoring strategy defined in:
- docs/01_NOISE_VS_CHECKABLE_CONTENT.md
- docs/03_SCORING_AND_FILTERING_STRATEGY.md

Scoring Components (0-60 points):
- Content Quality: 0-20 points
- Fact-Checkable Indicators: 0-30 points
- Source Risk: 0-10 points (inverted: low credibility = high priority)
- Topic Penalty: -30 to 0 points

Thresholds:
- Minimum Save: 20 points (below this = don't save to DB)
- Submission: 35 points (above this = submit to AletheiaFact)
"""
import re
from urllib.parse import urlparse
from typing import Dict
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# GOVERNMENT & INSTITUTIONAL ENTITIES (High Priority)
# ============================================================================
GOVERNMENT_ENTITIES = {
    # Executive Branch
    'presidente', 'vice-presidente', 'ministro', 'ministério',
    'governo federal', 'palácio do planalto', 'casa civil',

    # Legislative Branch
    'congresso', 'congresso nacional', 'senado', 'senador',
    'câmara', 'câmara dos deputados', 'deputado federal', 'deputado',

    # Judiciary
    'stf', 'supremo tribunal federal', 'stj', 'superior tribunal',
    'trf', 'tribunal regional federal', 'justiça federal',

    # Regulatory Agencies
    'anvisa', 'anatel', 'aneel', 'ans', 'anac',
    'bacen', 'banco central', 'ibama', 'icmbio',
    'inep', 'inss', 'funai', 'ipea',

    # Oversight & Audit
    'tse', 'tribunal superior eleitoral', 'tcu', 'tribunal de contas',
    'cgu', 'controladoria', 'pgr', 'procuradoria-geral',
    'mpf', 'ministério público federal', 'polícia federal',

    # State Level
    'governador', 'vice-governador', 'secretário estadual',
    'assembleia legislativa', 'deputado estadual',

    # Municipal Level
    'prefeito', 'vice-prefeito', 'secretário municipal',
    'câmara municipal', 'vereador'
}

# ============================================================================
# POLITICAL & SOCIAL KEYWORDS (High Priority)
# ============================================================================
POLITICAL_KEYWORDS = {
    # Government Actions
    'governo', 'política', 'eleição', 'eleições', 'partido político', 'partido',
    'coligação', 'aliança', 'oposição', 'situação',

    # Legislation
    'lei', 'projeto de lei', 'pl', 'pec', 'proposta de emenda',
    'medida provisória', 'mp', 'decreto', 'portaria', 'resolução',
    'reforma', 'aprovado', 'vetado', 'sancionado', 'promulgado',

    # Investigations & Corruption
    'corrupção', 'desvio', 'propina', 'suborno', 'lavagem de dinheiro',
    'cpi', 'comissão parlamentar', 'investigação', 'inquérito',
    'operação', 'delação', 'delação premiada', 'denúncia',
    'indiciado', 'acusado', 'réu', 'condenado',

    # Judicial Process
    'justiça', 'tribunal', 'julgamento', 'sentença', 'processo',
    'ação', 'mandado', 'liminar', 'habeas corpus', 'impeachment'
}

SOCIAL_RELEVANCE_KEYWORDS = {
    # Human Rights & Violence
    'direitos humanos', 'violência', 'crime', 'homicídio', 'assassinato',
    'segurança pública', 'polícia', 'violência policial', 'chacina',

    # Public Services
    'educação pública', 'saúde pública', 'sus', 'sistema único de saúde',
    'hospital público', 'escola pública', 'universidade pública',

    # Social Issues
    'desigualdade', 'pobreza', 'fome', 'miséria', 'sem-teto', 'moradia',
    'desemprego', 'trabalhador', 'sindicato', 'greve', 'manifestação',

    # Environment
    'meio ambiente', 'desmatamento', 'queimada', 'clima', 'aquecimento global',
    'mudança climática', 'poluição', 'sustentabilidade',

    # Indigenous & Minorities
    'indígena', 'quilombola', 'comunidade tradicional', 'demarcação',
    'terra indígena', 'racismo', 'discriminação'
}

HEALTH_KEYWORDS = {
    'vacina', 'vacinação', 'imunização', 'dose', 'campanha de vacinação',
    'covid', 'covid-19', 'coronavirus', 'pandemia', 'epidemia', 'surto',
    'vírus', 'doença', 'enfermidade', 'síndrome',
    'saúde', 'hospital', 'uti', 'leito', 'médico', 'enfermeiro',
    'tratamento', 'medicamento', 'remédio', 'farmácia',
    'ministério da saúde', 'anvisa', 'vigilância sanitária',
    'sus', 'sistema único de saúde'
}

SCIENCE_KEYWORDS = {
    'cientista', 'pesquisador', 'pesquisa científica', 'pesquisa',
    'estudo', 'estudo científico', 'descoberta', 'experimento',
    'universidade', 'faculdade', 'instituto de pesquisa',
    'ciência', 'científico', 'tecnologia', 'inovação',
    'publicação', 'artigo científico', 'revista científica',
    'peer review', 'nasa', 'fapesp', 'cnpq', 'capes'
}

# ============================================================================
# ATTRIBUTION KEYWORDS (Claim Indicators)
# ============================================================================
ATTRIBUTION_KEYWORDS = {
    # Strong Attribution Verbs
    'afirmou', 'afirma', 'declarou', 'declara', 'confirmou', 'confirma',
    'anunciou', 'anuncia', 'revelou', 'revela', 'garantiu', 'garante',

    # Medium Attribution
    'disse', 'diz', 'alegou', 'alega', 'defendeu', 'defende',
    'criticou', 'critica', 'acusou', 'acusa', 'negou', 'nega',

    # Reverse Attribution
    'segundo', 'de acordo com', 'conforme', 'para',

    # Evidence/Proof
    'comprovou', 'comprova', 'demonstrou', 'demonstra',
    'provou', 'prova', 'evidenciou', 'evidencia',
    'denunciou', 'denuncia', 'apontou', 'aponta'
}

# ============================================================================
# ENTERTAINMENT KEYWORDS (Low Priority - Penalty)
# ============================================================================
ENTERTAINMENT_KEYWORDS = {
    # Reality TV (heaviest penalty)
    'bbb', 'big brother', 'big brother brasil', 'a fazenda', 'fazenda',
    'no limite', 'reality show', 'reality', 'eliminação', 'paredão',

    # Celebrity/Gossip
    'celebridade', 'famoso', 'famosa', 'artista', 'ator', 'atriz',
    'cantor', 'cantora', 'modelo', 'influencer', 'influenciador',
    'affair', 'romance', 'namoro', 'casamento', 'separação', 'divórcio',
    'festa', 'balada', 'look', 'desfile', 'red carpet', 'tapete vermelho',

    # TV/Movies
    'novela', 'série', 'seriado', 'filme', 'cinema',
    'estreia', 'lançamento', 'trailer', 'teaser',
    'capítulo', 'episódio', 'temporada', 'final', 'personagem',

    # Music
    'álbum', 'disco', 'música', 'canção', 'clipe', 'videoclipe',
    'show', 'turnê', 'tour', 'palco', 'feat', 'featuring',
    'hit', 'sucesso musical', 'top 10', 'chart',

    # Internet Culture
    'memes', 'meme', 'viral', 'viralizou', 'trending', 'trend',
    'tiktoker', 'youtuber', 'streamer', 'lives', 'live'
}

SPORTS_KEYWORDS = {
    # Match Results
    'gol', 'gols', 'placar', 'resultado', 'vitória', 'derrota', 'empate',
    'venceu', 'perdeu', 'empatou', 'marcou', 'time', 'equipe',

    # Game Elements
    'jogo', 'partida', 'rodada', 'confronto', 'clássico',
    'primeiro tempo', 'segundo tempo', 'prorrogação', 'pênalti', 'pênaltis',

    # Competitions
    'campeonato', 'torneio', 'copa', 'taça', 'troféu',
    'libertadores', 'sul-americana', 'brasileirão', 'série a', 'série b',
    'champions league', 'mundial', 'olimpíadas',

    # People/Places
    'jogador', 'atleta', 'técnico', 'treinador', 'árbitro', 'juiz',
    'torcida', 'torcedor', 'estádio', 'arena', 'ginásio'
}

# Controversy keywords that override sports penalty
CONTROVERSY_KEYWORDS = {
    'corrupção', 'investigação', 'investigado', 'denúncia', 'denunciado',
    'escândalo', 'fraude', 'manipulação', 'doping', 'suborno',
    'propina', 'desvio', 'irregularidade', 'ilegal'
}

# ============================================================================
# SOURCE CREDIBILITY (Domain Lists)
# ============================================================================
HIGH_CREDIBILITY_SOURCES = {
    'g1.globo.com', 'folha.uol.com.br', 'gazetadopovo.com.br',
    'estadao.com.br', 'uol.com.br', 'bbc.com', 'bbc.com/portuguese',
    'cnnbrasil.com.br', 'band.com.br', 'r7.com',
    'noticias.uol.com.br', 'valor.globo.com', 'exame.com'
}

MEDIUM_CREDIBILITY_SOURCES = {
    'cartacapital.com.br', 'poder360.com.br', 'metropoles.com',
    'correiobraziliense.com.br', 'gazetadopovo.com.br',
    'istoedinheiro.com.br', 'veja.abril.com.br'
}

# ============================================================================
# COMPILED REGEX PATTERNS (Performance Optimization)
# ============================================================================
PERCENTAGE_PATTERN = re.compile(r'\d+([,\.]\d+)?%')
CURRENCY_BRL_PATTERN = re.compile(r'r\$\s*[\d\.,]+\s*(mil|milhões|bilhões|milhão|bilhão)?', re.IGNORECASE)
CURRENCY_USD_PATTERN = re.compile(r'us\$\s*[\d\.,]+\s*(mil|milhões|bilhões|milhão|bilhão)?', re.IGNORECASE)
LARGE_NUMBER_PATTERN = re.compile(r'\d+\s*(mil|milhões|bilhões|milhão|bilhão)', re.IGNORECASE)
DATE_PATTERN = re.compile(r'\d{1,2}\s+de\s+(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)', re.IGNORECASE)
YEAR_PATTERN = re.compile(r'\b(19|20)\d{2}\b')
NUMBER_PATTERN = re.compile(r'\d+')
SENTENCE_DELIMITER_PATTERN = re.compile(r'[.!?]')


class PreFilter:
    """Pre-filtering scoring system to prioritize content for fact-checking

    Implements scoring strategy from docs/03_SCORING_AND_FILTERING_STRATEGY.md
    """

    @staticmethod
    def calculate_score(content: str, title: str, source_url: str, credibility_level: str) -> Dict[str, int]:
        """
        Calculate pre-filter score for content (0-60 points).

        Scoring breakdown:
        - Content Quality: 0-20 points (length + sentence completeness)
        - Fact-Checkable Indicators: 0-30 points (government, political, data, attribution)
        - Source Risk: 0-10 points (inverted: low credibility = high priority)
        - Topic Penalty: -30 to 0 points (entertainment/sports penalty)

        Args:
            content: Main text content
            title: Article title
            source_url: Source URL
            credibility_level: Source credibility ('high', 'medium', 'low')

        Returns:
            Dictionary with total score and breakdown by category
        """
        scores = {
            "content_quality": 0,
            "fact_checkable": 0,
            "source_risk": 0,
            "topic_penalty": 0,
            "total": 0
        }

        # Combine title and content for analysis (case-insensitive)
        full_text = f"{title} {content}".lower()

        # 1. Content Quality (20 points max)
        scores["content_quality"] = PreFilter._score_content_quality(content)

        # 2. Fact-Checkable Indicators (30 points max)
        scores["fact_checkable"] = PreFilter._score_fact_checkable(full_text)

        # 3. Source Risk (10 points max) - LOW credibility gets HIGHEST score
        scores["source_risk"] = PreFilter._score_source_risk(source_url, credibility_level)

        # 4. Topic Penalty (-30 to 0 points for entertainment/sports)
        scores["topic_penalty"] = PreFilter._calculate_topic_penalty(full_text)

        # Calculate total (clamped to minimum 0)
        scores["total"] = max(0, sum([
            scores["content_quality"],
            scores["fact_checkable"],
            scores["source_risk"],
            scores["topic_penalty"]  # Negative value
        ]))

        logger.debug(
            f"Score breakdown: total={scores['total']}, "
            f"quality={scores['content_quality']}, "
            f"checkable={scores['fact_checkable']}, "
            f"source={scores['source_risk']}, "
            f"penalty={scores['topic_penalty']}"
        )

        return scores

    @staticmethod
    def _score_content_quality(content: str) -> int:
        """
        Score content quality (20 points max).

        Length scoring:
        - ≥ 300 chars: 10 points (ideal)
        - ≥ 150 chars: 7 points (acceptable)
        - ≥ 100 chars: 5 points (minimal)
        - < 100 chars: 0 points (insufficient)

        Sentence completeness:
        - ≥ 3 sentences: 10 points (complete context)
        - 2 sentences: 7 points (acceptable)
        - 1 sentence: 3 points (minimal)
        - 0 sentences: 0 points (fragment)
        """
        score = 0

        # Length scoring (0-10 points)
        content_length = len(content)
        if content_length >= 300:
            score += 10
        elif content_length >= 150:
            score += 7
        elif content_length >= 100:
            score += 5
        # else: 0 points

        # Sentence completeness (0-10 points)
        sentence_count = len(SENTENCE_DELIMITER_PATTERN.findall(content))
        if sentence_count >= 3:
            score += 10
        elif sentence_count == 2:
            score += 7
        elif sentence_count == 1:
            score += 3
        # else: 0 points

        return score

    @staticmethod
    def _score_fact_checkable(text: str) -> int:
        """
        Score fact-checkable indicators (30 points max).

        Priority scoring (additive, capped at 30):
        - Government entities: 18 points (HIGHEST - público interest + verifiable)
        - Political keywords: 15 points (corruption, legislation, investigations)
        - Social relevance: 12 points (human rights, public services, environment)
        - Health/Science: 10 points (health misinformation risk, scientific claims)
        - Attribution keywords: 8 points (afirmou, segundo, etc. - claim indicators)
        - Verifiable data: 6 points (percentages, currency, specific numbers)

        Args:
            text: Lowercased full text (title + content)

        Returns:
            Score from 0-30 (capped)
        """
        score = 0

        # A. Government/Institutional Entities (18 points) - HIGHEST PRIORITY
        # O(n) check but n is small and uses set intersection
        if any(entity in text for entity in GOVERNMENT_ENTITIES):
            score += 18

        # B. Political Keywords (15 points)
        # Covers corruption, investigations, legislation, judicial processes
        if any(kw in text for kw in POLITICAL_KEYWORDS):
            score += 15

        # C. Social Relevance Keywords (12 points)
        # Human rights, public services, social issues
        if any(kw in text for kw in SOCIAL_RELEVANCE_KEYWORDS):
            score += 12

        # D. Health/Science Keywords (10 points)
        # Health misinformation, scientific claims
        has_health = any(kw in text for kw in HEALTH_KEYWORDS)
        has_science = any(kw in text for kw in SCIENCE_KEYWORDS)
        if has_health or has_science:
            score += 10

        # E. Attribution Keywords (8 points)
        # Indicates someone made a claim (afirmou, declarou, segundo, etc.)
        if any(kw in text for kw in ATTRIBUTION_KEYWORDS):
            score += 8

        # F. Verifiable Data (6 points) - Use compiled patterns for performance
        # Priority: Percentage > Currency > Large numbers > Dates > Generic numbers
        if PERCENTAGE_PATTERN.search(text):
            score += 6
        elif CURRENCY_BRL_PATTERN.search(text) or CURRENCY_USD_PATTERN.search(text):
            score += 6
        elif LARGE_NUMBER_PATTERN.search(text):
            score += 5
        elif DATE_PATTERN.search(text):
            score += 4
        elif NUMBER_PATTERN.search(text):
            score += 3

        # G. Vague Language Penalty (subtract points for non-specific language)
        vague_terms = ['alguns', 'diversos', 'vários', 'muitos', 'poucos',
                       'em breve', 'logo', 'pode', 'podem', 'provavelmente', 'possivelmente',
                       'há rumores', 'fontes próximas', 'fontes não identificadas',
                       'pesquisa mostra', 'aponta estudo', 'recomendam', 'recomenda',
                       'especialistas dizem', 'acredita-se', 'é possível', 'possíveis']
        vague_count = sum(1 for term in vague_terms if term in text)
        score -= (vague_count * 8)  # -8 points per vague term (increased from -5)

        # H. Pure Noise Detection (navigation, CTAs, metadata)
        noise_terms = ['clique aqui', 'clique para', 'veja mais', 'saiba mais',
                       'leia mais', 'acesse', 'confira', 'veja também',
                       'notícias do dia', 'últimas notícias']
        noise_count = sum(1 for term in noise_terms if term in text)
        if noise_count >= 1:
            score -= 30  # Heavy penalty for pure noise content

        # Cap at 30 points maximum (after penalties)
        return max(0, min(score, 30))

    @staticmethod
    def _calculate_topic_penalty(text: str) -> int:
        """
        Apply penalty for entertainment/sports content (-30 to 0 points).

        Entertainment penalties:
        - ≥ 3 matches: -25 points (heavy entertainment: reality TV, celebrity gossip)
        - 2 matches: -20 points (medium entertainment)
        - 1 match: -15 points (light entertainment)

        Sports penalties (unless controversy):
        - ≥ 3 matches: -15 points (pure sports content)
        - 2 matches: -10 points (sports-related)

        Controversy override: Sports + controversy keywords = no penalty
        (e.g., "CBF investigada por corrupção" is fact-checkable)

        Args:
            text: Lowercased full text (title + content)

        Returns:
            Negative value (-30 to 0) to be added to total score
        """
        penalty = 0

        # Entertainment Check
        # Count how many entertainment keywords appear
        # Special handling for ambiguous words that need word boundaries
        ambiguous_celebrity_words = ['ator', 'atriz']  # Can match in 'relator', 'matriz', etc.

        entertainment_matches = 0
        for kw in ENTERTAINMENT_KEYWORDS:
            if kw in ambiguous_celebrity_words:
                # Use word boundaries for these terms
                import re
                if re.search(rf'\b{kw}\b', text):
                    entertainment_matches += 1
            else:
                if kw in text:
                    entertainment_matches += 1

        # Check for government money/investment context (overrides entertainment penalty)
        has_gov_money = any(term in text for term in ['governo', 'ministério', 'federal', 'investiu', 'investimento'])
        has_currency = CURRENCY_BRL_PATTERN.search(text) is not None

        # Only apply entertainment penalty if NOT government funding context
        if not (has_gov_money and has_currency and entertainment_matches <= 2):
            if entertainment_matches >= 3:
                penalty -= 35  # Heavy entertainment (reality TV, celebrity, gossip)
            elif entertainment_matches >= 2:
                penalty -= 30  # Medium entertainment
            elif entertainment_matches >= 1:
                penalty -= 25  # Light entertainment

        # Sports Check (with controversy override)
        sports_matches = sum(1 for kw in SPORTS_KEYWORDS if kw in text)

        # Check if sports content involves corruption/scandal (then it's checkable)
        has_controversy = any(kw in text for kw in CONTROVERSY_KEYWORDS)

        # Only penalize pure sports (match results, scores)
        if not has_controversy:
            if sports_matches >= 3:
                penalty -= 25  # Heavy sports content
            elif sports_matches >= 2:
                penalty -= 15  # Medium sports content

        # Cap maximum penalty at -40 (increased from -30)
        return max(penalty, -40)

    @staticmethod
    def _score_source_risk(source_url: str, credibility_level: str) -> int:
        """
        Score source risk (0-10 points).

        INVERTED SCORING: Low credibility sources get HIGHEST priority.
        Rationale: Proactive misinformation monitoring requires prioritizing
        unreliable sources where false claims are more likely to originate.

        Scoring:
        - Low credibility: 10 points (HIGHEST PRIORITY - likely misinformation)
        - Medium credibility: 5 points (moderate priority)
        - High credibility: 3 points (still monitor, lower urgency)
        - Unknown: 10 points (treat cautiously as potential misinformation)

        Args:
            source_url: Article source URL
            credibility_level: Configured credibility ('high', 'medium', 'low')

        Returns:
            Score from 3-10 points
        """
        # Extract domain from URL for known source matching
        try:
            domain = urlparse(source_url).netloc.lower()
            # Remove 'www.' prefix for consistency
            domain = domain.replace('www.', '')
        except Exception:
            domain = ""

        # Check against known domain lists first (overrides config)
        if domain in HIGH_CREDIBILITY_SOURCES:
            return 3
        elif domain in MEDIUM_CREDIBILITY_SOURCES:
            return 5

        # Fall back to configured credibility level
        if credibility_level == "low":
            return 10  # HIGHEST priority - likely misinformation source
        elif credibility_level == "medium":
            return 5
        elif credibility_level == "high":
            return 3
        else:
            # Unknown/unconfigured sources treated as low credibility
            # Better to over-monitor than under-monitor
            return 10

    @staticmethod
    def should_submit(score: int, threshold: int = 35) -> bool:
        """
        Determine if content should be submitted based on score.

        Default threshold: 35 points (configurable via settings)

        Args:
            score: Total pre-filter score (0-60)
            threshold: Minimum score for submission (default: 35)

        Returns:
            True if content should be submitted to AletheiaFact
        """
        return score >= threshold
