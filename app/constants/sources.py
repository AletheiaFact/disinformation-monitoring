"""Source credibility domain lists

This module contains domain lists for source credibility scoring.
Used by PreFilter (app/filters/pre_filter.py).
"""

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
