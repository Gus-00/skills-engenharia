"""Coletores, um por fonte. Cada um expõe:

    NOME: str                       # prefixo do id no banco
    coletar(cliente, ja_tem) -> iterador de dicts com as colunas da tabela `vagas`
                                    # (id_original no lugar de id; sem fonte/datas de coleta)

`ja_tem(id_original)` diz se a vaga já está no banco: as fontes que precisam abrir
uma página por vaga usam isso para não baixar de novo o que já foi coletado.
"""
from . import gupy, infojobs, solides, vagas_com

FONTES = {m.NOME: m for m in (gupy, solides, vagas_com, infojobs)}

# Rodadas por padrão (`python coleta.py` sem argumentos). O VAGAS.com fica de fora:
# o site responde HTTP 429 com Retry-After de 24 h mesmo em ritmo lento, ou seja,
# não aceita coleta automatizada. Ainda dá para chamá-lo pelo nome: python coleta.py vagas_com
PADRAO = ["gupy", "solides", "infojobs"]
