"""Gera a planilha Excel com os resultados, formatada para análise no Excel.

Usada por analise.py (resultados/planilha_skills.xlsx, todas as vagas) e pelo painel
(botão de download, só com as vagas do filtro atual).
"""
import io
import math
from datetime import date

import pandas as pd
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import config
from comum import normalizar

UF = {"acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM", "bahia": "BA", "ceara": "CE",
      "distrito federal": "DF", "espirito santo": "ES", "goias": "GO", "maranhao": "MA",
      "mato grosso": "MT", "mato grosso do sul": "MS", "minas gerais": "MG", "para": "PA",
      "paraiba": "PB", "parana": "PR", "pernambuco": "PE", "piaui": "PI", "rio de janeiro": "RJ",
      "rio grande do norte": "RN", "rio grande do sul": "RS", "rondonia": "RO", "roraima": "RR",
      "santa catarina": "SC", "sao paulo": "SP", "sergipe": "SE", "tocantins": "TO"}

MODALIDADES = {"on-site": "Presencial", "hybrid": "Híbrido", "remote": "Remoto"}


def traduzir_modalidade(serie):
    """on-site/hybrid/remote -> Presencial/Híbrido/Remoto; vazio -> Não informada."""
    return serie.map(lambda m: MODALIDADES.get(m, m) if isinstance(m, str) and m else "Não informada")


AZUL = "1F4E79"
AZUL_CLARO = "5B9BD5"
CABECALHO_FONTE = Font(bold=True, color="FFFFFF")
CABECALHO_FUNDO = PatternFill("solid", fgColor=AZUL)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margem = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centro - margem), min(1.0, centro + margem))


def tabela_ranking(vagas, skills):
    n = len(vagas)
    r = (skills.groupby(["skill", "tipo", "categoria"]).vaga_id.nunique()
         .reset_index(name="n_vagas").sort_values(["tipo", "n_vagas"], ascending=[True, False]))
    r["% vagas"] = r.n_vagas / n if n else 0.0
    ic = r.n_vagas.apply(lambda k: wilson(k, n))
    r["IC95% inferior"] = [a for a, _ in ic]
    r["IC95% superior"] = [b for _, b in ic]
    r.insert(0, "posição", r.groupby("tipo").cumcount() + 1)
    return r.rename(columns={"skill": "Skill", "tipo": "Tipo", "categoria": "Categoria",
                             "n_vagas": "Nº de vagas"})


def tabela_por_grupo(vagas, skills, coluna):
    """% de vagas de cada grupo (subárea, senioridade, fonte...) que pedem cada skill."""
    totais = vagas.groupby(coluna).id.nunique()
    base = skills.merge(vagas[["id", coluna]], left_on="vaga_id", right_on="id")
    t = base.groupby(["skill", "tipo", "categoria", coluna]).vaga_id.nunique().unstack(coluna, fill_value=0)
    t = (t / totais).fillna(0.0)
    t["geral"] = skills.groupby(["skill", "tipo", "categoria"]).vaga_id.nunique() / max(len(vagas), 1)
    t = t.reset_index().sort_values(["tipo", "geral"], ascending=[True, False])
    n_linha = {"skill": "(nº de vagas)", "tipo": "", "categoria": "", "geral": len(vagas), **totais.to_dict()}
    t = pd.concat([pd.DataFrame([n_linha]), t], ignore_index=True)
    return t.rename(columns={"skill": "Skill", "tipo": "Tipo", "categoria": "Categoria", "geral": "Geral"})


def tabela_vagas(vagas, skills):
    def juntar(tipo):
        s = skills[skills.tipo == tipo].groupby("vaga_id").skill.apply(lambda x: "; ".join(sorted(x)))
        return vagas.id.map(s).fillna("")

    def contar(tipo):
        return vagas.id.map(skills[skills.tipo == tipo].groupby("vaga_id").size()).fillna(0).astype(int)

    colunas = ["fonte", "titulo", "empresa", "cidade", "estado", "modalidade", "cargo",
               "subarea", "senioridade", "publicada_em"]
    t = vagas[[c for c in colunas if c in vagas.columns]].copy()
    if "modalidade" in t.columns:
        t["modalidade"] = traduzir_modalidade(t.modalidade)
    if "estado" in t.columns:
        t["estado"] = t.estado.map(lambda e: UF.get(normalizar(e), e) if isinstance(e, str) else e)
    t["publicada_em"] = pd.to_datetime(t.publicada_em, errors="coerce", utc=True).dt.tz_localize(None).dt.date
    t["nº hard"], t["nº soft"] = contar("hard"), contar("soft")
    t["hard skills"], t["soft skills"], t["requisitos"] = juntar("hard"), juntar("soft"), juntar("requisito")
    if "url" in vagas.columns:
        t["link"] = vagas.url
    return t.rename(columns={"fonte": "Fonte", "titulo": "Título", "empresa": "Empresa", "cidade": "Cidade",
                             "estado": "UF", "modalidade": "Modalidade", "cargo": "Cargo", "subarea": "Subárea",
                             "senioridade": "Senioridade", "publicada_em": "Publicada em"})


def tabela_coocorrencia(skills, top=50):
    linhas = []
    for tipo in ("hard", "soft"):
        s = skills[skills.tipo == tipo][["vaga_id", "skill"]]
        pares = s.merge(s, on="vaga_id")
        pares = pares[pares.skill_x < pares.skill_y]
        c = pares.groupby(["skill_x", "skill_y"]).size().nlargest(top).reset_index(name="Nº de vagas")
        c.insert(0, "Tipo", tipo)
        linhas.append(c)
    return pd.concat(linhas).rename(columns={"skill_x": "Skill A", "skill_y": "Skill B"})


def _formatar(ws, pct_cols=(), larguras=None, barras=(), linha_n=False):
    ws.freeze_panes = "B2" if ws.max_column > 6 else "A2"
    ws.auto_filter.ref = ws.dimensions
    for c in ws[1]:
        c.font, c.fill = CABECALHO_FONTE, CABECALHO_FUNDO
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 32
    for i, coluna in enumerate(ws.iter_cols(min_row=1, max_row=min(ws.max_row, 200)), 1):
        letra = get_column_letter(i)
        if larguras and letra in larguras:
            largura = larguras[letra]
        else:
            largura = min(45, max(10, max(len(str(c.value or "")) for c in coluna) + 2))
        ws.column_dimensions[letra].width = largura
    inicio = 3 if linha_n else 2
    for letra in pct_cols:
        for c in ws[letra][inicio - 1:]:
            c.number_format = "0.0%"
    for letra in barras:
        ws.conditional_formatting.add(f"{letra}{inicio}:{letra}{ws.max_row}",
                                      DataBarRule(start_type="num", start_value=0, end_type="max",
                                                  color=AZUL_CLARO))
    if linha_n:
        for c in ws[2]:
            c.font = Font(italic=True, color="595959")


def gerar(vagas, skills, filtro_descricao="todas as vagas da população do estudo"):
    """Devolve os bytes de um .xlsx com os resultados para as vagas informadas."""
    skills = skills[skills.vaga_id.isin(vagas.id)]
    ranking = tabela_ranking(vagas, skills)
    datas = pd.to_datetime(vagas.publicada_em, errors="coerce", utc=True)

    read_me = pd.DataFrame({"Item": [
        "Pesquisa", "Gerada em", "Vagas incluídas", "Nº de vagas", "Nº de empresas", "Fontes",
        "Publicação das vagas", "", "Abas",
        "Ranking", "Por subárea / senioridade / fonte / cargo", "Vagas",
        "Coocorrência", "Dicionário", "", "Métrica",
    ], "Descrição": [
        "Hard skills, soft skills e requisitos pedidos em vagas de engenharia no Brasil",
        date.today().strftime("%d/%m/%Y"), filtro_descricao, len(vagas), vagas.empresa.nunique(),
        ", ".join(sorted(vagas.fonte.unique())),
        f"{datas.min():%d/%m/%Y} a {datas.max():%d/%m/%Y}" if datas.notna().any() else "-", "", "",
        "Todas as skills, com % de vagas que as pedem e intervalo de confiança de 95% (Wilson)",
        "% das vagas de cada grupo que pedem a skill; a 1ª linha traz o nº de vagas do grupo",
        "Uma linha por vaga, com as skills detectadas e o link do anúncio",
        "Pares de skills que mais aparecem juntos na mesma vaga",
        "Skills do dicionário e os padrões de texto usados para detectá-las", "",
        "% de vagas = vagas que mencionam a skill ao menos uma vez / total de vagas",
    ]})

    abas = [
        ("Read-me", read_me, {}, ),
        ("Ranking", ranking, dict(pct_cols="FGH", barras="F")),
        ("Por subárea", tabela_por_grupo(vagas, skills, "subarea"), {}),
        ("Por senioridade", tabela_por_grupo(vagas, skills, "senioridade"), {}),
        ("Por fonte", tabela_por_grupo(vagas, skills, "fonte"), {}),
        ("Por cargo", tabela_por_grupo(vagas, skills, "cargo"), {}),
        ("Vagas", tabela_vagas(vagas, skills), {}),
        ("Coocorrência", tabela_coocorrencia(skills), dict(barras="D")),
    ]
    dic = pd.read_csv(config.DICIONARIO_PATH, sep=";", encoding="utf-8").fillna("")
    abas.append(("Dicionário", dic.rename(columns={"skill": "Skill", "tipo": "Tipo", "categoria": "Categoria",
                                                   "padroes": "Padrões (regex)", "excluir": "Exclusões (regex)"}),
                 {}))

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as w:
        w.book.properties.creator = config.AUTOR
        w.book.properties.lastModifiedBy = config.AUTOR
        w.book.properties.title = "Skills em vagas de engenharia"
        for nome, df, fmt in abas:
            df.to_excel(w, sheet_name=nome, index=False)
            ws = w.sheets[nome]
            if nome.startswith("Por "):
                cols = [get_column_letter(i) for i in range(4, ws.max_column + 1)]
                _formatar(ws, pct_cols=cols, barras=["D"], linha_n=True)
            elif nome == "Read-me":
                _formatar(ws, larguras={"A": 40, "B": 100})
                for c in ws["A"][1:]:
                    c.font = Font(bold=True, color=AZUL)
            elif nome == "Vagas":
                letra = {c.value: c.column_letter for c in ws[1]}
                largura = {"Título": 45, "Empresa": 30, "hard skills": 60, "soft skills": 45,
                           "requisitos": 30, "link": 40}
                _formatar(ws, larguras={letra[k]: v for k, v in largura.items() if k in letra})
                if "link" in letra:
                    for c in ws[letra["link"]][1:]:
                        if c.value:
                            c.hyperlink, c.style = c.value, "Hyperlink"
            else:
                _formatar(ws, **fmt)
    return buffer.getvalue()
