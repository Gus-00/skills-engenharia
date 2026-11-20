"""Configuração da pesquisa: termos de busca, regras de classificação e caminhos."""
from pathlib import Path

AUTOR = "Gustavo"  # aparece nas propriedades da planilha gerada

RAIZ = Path(__file__).parent
DB_PATH = RAIZ / "dados" / "vagas.db"          # banco completo da coleta (local, fora do repositório)
PAINEL_DB_PATH = RAIZ / "dados" / "painel.db"  # versão enxuta para o painel publicado
DICIONARIO_PATH = RAIZ / "dicionario_skills.csv"
RESULTADOS_DIR = RAIZ / "resultados"
VALIDACAO_DIR = RAIZ / "validacao"

# ---------------------------------------------------------------------------
# Coleta (os coletores de cada fonte ficam em fontes/)
# ---------------------------------------------------------------------------
PAUSA_ENTRE_REQUISICOES = 1.0  # segundos entre requisições (coleta respeitosa)
USER_AGENT = "Mozilla/5.0 (pesquisa academica sobre competencias em engenharia)"

# Termos da Gupy. A API limita cada busca a ~500 resultados, por isso usamos
# vários termos e removemos duplicatas pelo id da vaga.
TERMOS_BUSCA = [
    "engenheiro", "engenheira", "engenharia",
    "engenheiro civil", "engenheiro de obras", "engenheiro de estruturas",
    "engenheiro mecânico", "engenheiro mecatrônico", "engenheiro de manutenção",
    "engenheiro eletricista", "engenheiro eletrônico", "engenheiro de automação",
    "engenheiro de produção", "engenheiro de processos", "engenheiro de qualidade",
    "engenheiro industrial", "engenheiro de planejamento", "engenheiro de projetos",
    "engenheiro químico", "engenheiro de alimentos", "engenheiro de materiais",
    "engenheiro ambiental", "engenheiro de segurança do trabalho",
    "engenheiro de software", "engenheiro de dados", "engenheiro de computação",
    "engenheiro de machine learning", "engenheiro de minas", "engenheiro agrônomo",
    "engenheiro de vendas", "engenheiro de aplicação", "engenheiro de campo",
    "estágio engenharia", "trainee engenharia",
]

# Só entram no banco vagas cujo TÍTULO (normalizado) casa com este padrão
# ("engenheiro/a", "engenharia"; exclui "engenho", ex.: bairro Engenho de Dentro).
FILTRO_TITULO = r"engenh(eir|ari)"

# ---------------------------------------------------------------------------
# População do estudo
# Ficam no banco todas as vagas coletadas, mas a análise considera só:
#   - cargos em CARGOS_POPULACAO (classificados pelo título, regras abaixo);
#   - tipos de vaga fora de TIPOS_EXCLUIDOS (banco de talentos não é vaga real);
#   - publicadas a partir de DATA_MINIMA (None = todas as vagas abertas).
# ---------------------------------------------------------------------------
CARGOS = [
    ("Técnico/Auxiliar/Assistente", r"tecnic[oa] (em|de) engenharia|^tecnic|pessoa tecnica|auxiliar|"
                                    r"assistente|aprendiz|atendente"),
    ("Estágio", r"estagi"),
    ("Trainee", r"trainee"),
    ("Engenheiro(a)", r"engenheir"),
    ("Analista/Especialista/Gestão", r"analista|especialista|coordenador|gerente|supervisor|lider|head"),
]
CARGO_PADRAO = "Outros"
CARGOS_POPULACAO = {"Engenheiro(a)", "Estágio", "Trainee"}
TIPOS_EXCLUIDOS = {"vacancy_type_talent_pool"}
TITULO_EXCLUIDO = r"banco de talentos|cadastro reserva"  # não são vagas reais
DATA_MINIMA = None  # ex.: "2026-01-01"

# Textos inválidos: curtos demais ou repetitivos (ex.: anúncios-modelo com
# "descrição da vaga descrição da vaga..."). Diversidade = palavras distintas / palavras.
TEXTO_MIN_CARACTERES = 150
DIVERSIDADE_MIN = 0.3
# Anúncios suspeitos (golpe/captação): pedem cadastro em site externo, cobram taxa etc.
TEXTO_SUSPEITO = (r"voce foi selecionad[oa] para a proxima fase|taxa de (inscricao|cadastro)|"
                  r"deposit[eo] (o valor|a taxa)|jobaqui")

# Duplicatas entre fontes: mesma vaga anunciada em mais de um site. Duas vagas de
# fontes diferentes são a mesma quando têm título normalizado igual e descrições com
# similaridade de Jaccard (conjuntos de 5 palavras seguidas) >= DEDUP_JACCARD.
# Fica a versão da fonte que aparece primeiro em PRIORIDADE_FONTES.
DEDUP_JACCARD = 0.5
PRIORIDADE_FONTES = ["gupy", "solides", "vagas_com", "infojobs"]

# ---------------------------------------------------------------------------
# Classificação por título (texto normalizado: minúsculo, sem acento)
# A ordem importa: a primeira regra que casar define a subárea.
# ---------------------------------------------------------------------------
SUBAREAS = [
    ("Segurança do Trabalho", r"seguranca do trabalho|\bsst\b|\bhse\b|\bsms\b"),
    ("Software/Dados/Computação", r"software|dados|\bdata\b|machine learning|\bml\b|devops|\bsre\b|computacao|"
                                   r"sistemas|plataforma|cloud|nuvem|back.?end|front.?end|full.?stack|\bqa\b|"
                                   r"testes|\bia\b|inteligencia artificial|ciberseguranca|seguranca da informacao|redes"),
    ("Biomédica/Clínica", r"clinic|biomedic|hospitalar"),
    ("Civil", r"civil|estrutur|obras|geotecn|edificac|infraestrutura|orcament|pavimenta|drenagem|"
              r"instalacoes|custos|incorporac|residencial"),
    ("Elétrica/Eletrônica/Automação", r"eletric|eletron|eletrotec|automacao|controle e automacao|instrumenta|"
                                      r"energia|potencia|subestac|telecom|aerogerador|\bwtg\b|eolic|solar"),
    ("Mecânica/Mecatrônica", r"mecanic|mecatron|manutencao|confiabilidade|hvac|climatizacao|produto|"
                             r"powertrain|\bnvh\b|\bcae\b|turbomaquin|motores|aeronaut|automotiv"),
    ("Produção/Processos/Qualidade", r"producao|processo|qualidade|industrial|manufatura|melhoria continua|"
                                     r"planejamento|pcp|logistic|supply"),
    ("Química/Alimentos/Materiais", r"quimic|alimentos|materiais|metalurg|bioprocess|petroleo|minas|mineracao"),
    ("Ambiental/Sanitária", r"ambiental|sanitar|saneamento|hidric"),
    ("Agronômica/Florestal", r"agronom|agricola|florestal"),
    ("Comercial/Aplicação", r"vendas|comercial|aplicacao|pre.?venda|key account"),
]
SUBAREA_PADRAO = "Engenharia (geral/outras)"

SENIORIDADES = [
    ("Estágio", r"estagi"),
    ("Trainee", r"trainee"),
    ("Liderança/Especialista", r"especialista|coordenador|coordenadora|gerente|lider|head|supervisor|principal|staff"),
    ("Sênior", r"senior|\bsr\b|\biii\b"),
    ("Pleno", r"pleno|\bpl\b|\bii\b"),
    ("Júnior", r"junior|\bjr\b|\bi\b"),
]
SENIORIDADE_PADRAO = "Não informada"

# Recorte do texto analisado: do primeiro cabeçalho de atividades/requisitos até o
# primeiro cabeçalho de benefícios depois dele. Assim o texto institucional da empresa
# e a lista de benefícios não contam como exigência da vaga.
# As duas primeiras são as seções padrão da Gupy; as demais, cabeçalhos comuns nos outros sites.
INICIO_ESCOPO = [
    r"responsabilidades e atribuicoes", r"requisitos e qualificacoes",
    r"(principais |suas )?(responsabilidades|atribuicoes|atividades)( e (atribuicoes|responsabilidades))?"
    r"( da vaga| do cargo| a serem desempenhadas| serao)? ?[:.]",
    r"(o que voce (vai|ira) (fazer|construir)|o que esperamos|o que buscamos|o que procuramos|seus desafios|"
    r"desafios do cargo|sua missao|missao do cargo|para esta posicao esperamos|o que e importante para)",
    r"(requisitos|qualificacoes|pre.?requisitos|exigencias|formacao|competencias( comportamentais| tecnicas)?)"
    r"( obrigatorios| necessarios| tecnicos| e qualificacoes| desejaveis)? ?[:.]",
    r"(descricao (da vaga|das atividades|da funcao)|sobre a (vaga|oportunidade)) ?[:.]",
]
FIM_ESCOPO = [
    r"informacoes adicionais",
    r"(nossos |pacote de )?beneficios( oferecidos)? ?[:.]",
    r"o que (nos )?oferecemos", r"remuneracao( e beneficios)? ?[:.]",
    r"(quem somos|sobre (a empresa|nos)) ?[:.]",
]
