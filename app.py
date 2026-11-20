"""Painel interativo dos resultados.  Rodar com:  python -m streamlit run app.py --server.port 8510"""
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st

import planilha
from comum import conectar_leitura
from config import DB_PATH, PAINEL_DB_PATH, RESULTADOS_DIR
from planilha import wilson

st.set_page_config(page_title="Skills em Engenharia", page_icon="📊", layout="wide")

# ---- visual: fundo branco com detalhes azuis (o tema base fica em .streamlit/config.toml) ----
AZUL = "#1565C0"
PALETA = ["#0D47A1", "#1E88E5", "#64B5F6", "#1565C0", "#42A5F5", "#0B3C6E", "#90CAF9", "#2F6DB5",
          "#5C9BD6", "#BBDEFB"]
pio.templates.default = "plotly_white"
px.defaults.color_discrete_sequence = PALETA
st.markdown(f"""
<style>
  h1, h2, h3 {{ color: #0D3B66; }}
  [data-testid="stMetric"] {{
      background: #F3F8FD; border: 1px solid #D6E6F7; border-left: 5px solid {AZUL};
      border-radius: 8px; padding: 10px 14px; }}
  [data-testid="stMetricValue"] {{ color: {AZUL}; }}
  [data-testid="stSidebar"] {{ border-right: 1px solid #D6E6F7; }}
  .stDownloadButton [data-testid="stBaseButton-secondary"] {{ border: 1px solid {AZUL}; color: {AZUL}; }}
  .stDownloadButton [data-testid="stBaseButton-secondary"]:hover {{ background: {AZUL}; color: white; }}
</style>""", unsafe_allow_html=True)


@st.cache_data
def carregar(versao_db: float):  # muda quando o banco é atualizado, invalidando o cache
    con = conectar_leitura(BANCO)
    vagas = pd.read_sql(
        """SELECT v.id, v.fonte, v.titulo, v.empresa, v.publicada_em, v.cidade, v.estado, v.modalidade,
                  v.url, i.cargo, i.subarea, i.senioridade
           FROM vagas v JOIN vaga_info i ON i.vaga_id = v.id WHERE i.na_populacao = 1""", con)
    skills = pd.read_sql("SELECT vaga_id, skill, tipo, categoria, trecho FROM vaga_skill", con)
    vagas["modalidade"] = planilha.traduzir_modalidade(vagas.modalidade)
    return vagas, skills[skills.vaga_id.isin(vagas.id)]


@st.cache_data(show_spinner=False)
def gerar_planilha(versao_db: float, filtros: tuple, _vagas, _skills, descricao):
    # `filtros` e `versao_db` identificam o conteúdo no cache; os DataFrames (_) não entram no hash
    pronta = RESULTADOS_DIR / "planilha_skills.xlsx"
    sem_filtro = not any(sel for _, sel in filtros)
    if sem_filtro and pronta.exists() and pronta.stat().st_mtime >= versao_db:
        return pronta.read_bytes()  # gerada por analise.py com os mesmos dados
    return planilha.gerar(_vagas, _skills, descricao)


# Painel publicado usa o banco enxuto (dados/painel.db, gerado por analise.py);
# localmente, sem ele, usa o banco completo.
BANCO = PAINEL_DB_PATH if PAINEL_DB_PATH.exists() else DB_PATH
# data da última escrita no banco (com WAL, as escritas recentes ficam no arquivo -wal)
versao = max((p.stat().st_mtime for p in (BANCO, BANCO.with_name(BANCO.name + "-wal")) if p.exists()),
             default=0.0)
vagas, skills = carregar(versao)
if vagas.empty:
    st.warning("Sem dados. Rode `python coleta.py`, `python extrai.py` e `python analise.py` primeiro.")
    st.stop()

# ---- filtros ----
st.sidebar.header("Filtros")
FILTROS = [("Fonte", "fonte"), ("Subárea", "subarea"), ("Cargo", "cargo"),
           ("Senioridade", "senioridade"), ("Modalidade", "modalidade")]
selecao = {}
for rotulo, coluna in FILTROS:
    opcoes = sorted(vagas[coluna].dropna().unique())
    selecao[coluna] = st.sidebar.multiselect(rotulo, opcoes, placeholder="Todas")
top_n = st.sidebar.slider("Top N", 5, 40, 20)

v = vagas
for coluna, sel in selecao.items():
    if sel:
        v = v[v[coluna].isin(sel)]
s = skills[skills.vaga_id.isin(v.id)]
n = len(v)
descricao_filtro = "; ".join(f"{r}: {', '.join(selecao[c])}" for r, c in FILTROS if selecao[c]) or "todas as vagas"

# ---- cabeçalho ----
st.title("Skills mais pedidas em vagas de engenharia")
st.caption(f"Fontes: {', '.join(sorted(vagas.fonte.unique()))} (vagas deduplicadas). "
           "Métrica: % das vagas filtradas que mencionam a skill ao menos uma vez "
           "(barra de erro = IC 95% de Wilson).")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vagas", f"{n:,}".replace(",", "."))
c2.metric("Empresas", f"{v.empresa.nunique():,}".replace(",", "."))
por_vaga = s.groupby(["vaga_id", "tipo"]).size().unstack(fill_value=0).reindex(v.id, fill_value=0)
c3.metric("Hard skills / vaga", f"{por_vaga.get('hard', pd.Series([0])).mean():.1f}".replace(".", ","))
c4.metric("Soft skills / vaga", f"{por_vaga.get('soft', pd.Series([0])).mean():.1f}".replace(".", ","))

if n == 0:
    st.info("Nenhuma vaga com esses filtros.")
    st.stop()

# ---- downloads ----
with st.container(border=True):
    st.markdown(f"**Baixar dados** — {descricao_filtro} ({n} vagas)")
    d1, d2, d3 = st.columns(3)
    hoje = date.today().strftime("%Y-%m-%d")
    chave = tuple((c, tuple(sel)) for c, sel in selecao.items())
    d1.download_button(
        "📊 Planilha Excel completa", type="primary", use_container_width=True,
        # função: a planilha só é montada quando o botão é clicado (não trava a página)
        data=lambda: gerar_planilha(versao, chave, v, s, descricao_filtro),
        file_name=f"skills_engenharia_{hoje}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Ranking, tabelas por subárea/senioridade/fonte/cargo, lista de vagas, "
             "matriz vaga x skill e dicionário, já formatados.")
    d2.download_button(
        "Ranking de skills (CSV)", use_container_width=True,
        data=planilha.tabela_ranking(v, s).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name=f"ranking_skills_{hoje}.csv", mime="text/csv")
    d3.download_button(
        "Lista de vagas (CSV)", use_container_width=True,
        data=planilha.tabela_vagas(v, s).to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"vagas_{hoje}.csv", mime="text/csv")


def ranking(tipo):
    r = (s[s.tipo == tipo].groupby(["skill", "categoria"]).vaga_id.nunique()
         .reset_index(name="vagas").sort_values("vagas", ascending=False).head(top_n))
    r["pct"] = 100 * r.vagas / n
    ic = r.vagas.apply(lambda k: wilson(k, n))
    r["erro_sup"] = [100 * b for _, b in ic] - r.pct
    r["erro_inf"] = r.pct - [100 * a for a, _ in ic]
    return r


def grafico(tipo, titulo):
    r = ranking(tipo)
    if r.empty:
        st.info("Nenhuma ocorrência.")
        return
    fig = px.bar(r.iloc[::-1], x="pct", y="skill", color="categoria", orientation="h",
                 error_x="erro_sup", error_x_minus="erro_inf",
                 labels={"pct": "% das vagas", "skill": "", "categoria": "Categoria"},
                 hover_data={"vagas": True}, title=titulo)
    fig.update_traces(error_x_color="#5F7A99")
    fig.update_layout(height=max(420, 32 * len(r)), yaxis={"dtick": 1, "categoryorder": "array",
                      "categoryarray": list(r.skill[::-1])}, legend={"orientation": "h", "y": -0.15},
                      title_font_color="#0D3B66")
    st.plotly_chart(fig, use_container_width=True)


aba_hard, aba_soft, aba_req, aba_cmp, aba_busca = st.tabs(
    ["Hard skills", "Soft skills", "Requisitos", "Comparar subáreas", "Buscar skill"])
with aba_hard:
    grafico("hard", f"Top {top_n} hard skills")
with aba_soft:
    grafico("soft", f"Top {top_n} soft skills")
with aba_req:
    grafico("requisito", "Requisitos (não são skills)")

with aba_cmp:
    tipo = st.radio("Tipo", ["hard", "soft"], horizontal=True)
    base = s[s.tipo == tipo].merge(v[["id", "subarea"]], left_on="vaga_id", right_on="id")
    tot = v.subarea.value_counts()
    tot = tot[tot >= 10]  # subáreas com poucas vagas geram % instáveis
    t = base[base.subarea.isin(tot.index)].groupby(["skill", "subarea"]).vaga_id.nunique().unstack(fill_value=0)
    if t.empty:
        st.info("Nenhuma subárea com 10 ou mais vagas no filtro atual.")
    else:
        t = 100 * t / tot[t.columns]
        t = t.loc[t.max(axis=1).sort_values(ascending=False).index[:top_n]]
        t.columns = [f"{c} (n={tot[c]})" for c in t.columns]
        fig = px.imshow(t.round(0), text_auto=True, aspect="auto", color_continuous_scale="Blues",
                        labels={"color": "% vagas"})
        fig.update_layout(height=max(400, 28 * len(t)))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Só subáreas com 10 ou mais vagas no filtro atual.")

with aba_busca:
    escolha = st.selectbox("Skill", sorted(s.skill.unique()))
    sel = s[s.skill == escolha].merge(v, left_on="vaga_id", right_on="id")
    st.write(f"**{len(sel)}** vagas ({100 * len(sel) / n:.1f}%) mencionam **{escolha}**.")
    st.dataframe(sel[["fonte", "titulo", "empresa", "subarea", "senioridade", "trecho", "url"]],
                 column_config={"url": st.column_config.LinkColumn("vaga")},
                 hide_index=True, use_container_width=True)
