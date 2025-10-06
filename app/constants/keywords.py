"""Keyword sets for content classification and scoring

This module contains all keyword lists used by:
- PreFilter (app/filters/pre_filter.py) - Article-level scoring
- ClaimExtractor (app/nlp/claim_extractor.py) - Sentence-level extraction
"""

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
# VAGUE LANGUAGE & OFFICIAL GUIDANCE (Scoring Modifiers)
# ============================================================================

# Speculation patterns (heavy penalty - non-checkable speculation)
SPECULATION_KEYWORDS = {
    'pode ser que', 'é possível que', 'provavelmente', 'possivelmente',
    'talvez', 'há rumores', 'dizem que', 'fontes não identificadas',
    'acredita-se', 'aparentemente', 'supostamente', 'presumivelmente'
}

# Vague quantifiers (mild penalty)
VAGUE_QUANTIFIERS = {
    'alguns', 'diversos', 'vários', 'muitos', 'poucos',
    'em breve', 'logo', 'futuramente', 'em algum momento'
}

# Official guidance patterns (should NOT be penalized - these are fact-checkable directives)
OFFICIAL_GUIDANCE_KEYWORDS = {
    'é recomendado', 'é recomendável', 'orienta-se', 'deve-se',
    'é obrigatório', 'é necessário', 'é exigido', 'determina que',
    'conforme determina', 'segundo a lei', 'nos termos da', 'exige',
    'registro de', 'deve conter', 'é obrigatória'
}

# Health/Safety advisory keywords (high priority for fact-checking)
HEALTH_SAFETY_ADVISORY = {
    'vigilância sanitária', 'anvisa', 'ministério da saúde',
    'alerta sanitário', 'notificação', 'orientação sanitária',
    'risco à saúde', 'intoxicação', 'contaminação', 'surto',
    'apevisa', 'visa', 'agência sanitária', 'sesab', 'secretaria de saúde'
}

# ============================================================================
# NOISE DETECTION
# ============================================================================

# Vague language indicators (used by claim_extractor - negative scoring)
VAGUE_KEYWORDS = {
    'alguns', 'diversos', 'vários', 'muitos', 'poucos',
    'em breve', 'logo', 'futuramente', 'em algum momento',
    'provavelmente', 'possivelmente', 'talvez', 'pode ser',
    'há rumores', 'dizem que', 'fontes não identificadas'
}

# Pure noise terms (navigation, CTAs, metadata)
NOISE_TERMS = [
    'clique aqui', 'clique para', 'veja mais', 'saiba mais',
    'leia mais', 'acesse', 'confira', 'veja também',
    'notícias do dia', 'últimas notícias'
]
