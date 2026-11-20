"""Gera as tabelas de resultado (CSV) e um resumo em Markdown em resultados/.

Métrica principal: % de vagas que mencionam a skill (presença por vaga),
com intervalo de confiança de 95% de Wilson.
"""
from datetime import date
from itertools import combinations

import pandas as pd

import config
import planilha
from planilha import wilson
from comum import conectar


def carregar():
    con = conectar()
    vagas = pd.read_sql(
        """SELECT v.id, v.fonte, v.titulo, v.empresa, v.publicada_em, v.cidade, v.estado, v.modalidade, v.url,
                  i.cargo, i.subarea, i.senioridade, i.escopo
           FROM vagas v JOIN vaga_info i ON i.vaga_id = v.id
           WHERE i.na_populacao = 1""", con)
    skills = pd.read_sql(
        """SELECT s.vaga_id, s.skill, s.tipo, s.categoria FROM vaga_skill s
           JOIN vaga_info i ON i.vaga_id = s.vaga_id WHERE i.na_populacao = 1""", con)
    excluidas = pd.read_sql(
        """SELECT v.fonte, i.exclusao FROM vaga_info i JOIN vagas v ON v.id = i.vaga_id
           WHERE i.na_populacao = 0""", con)
    return vagas, skills, excluidas


def ranking(skills, n_vagas):
    r = (skills.groupby(["skill", "tipo", "categoria"]).vaga_id.nunique()
         .reset_index(name="n_vagas").sort_values("n_vagas", ascending=False))
    r["pct_vagas"] = 100 * r.n_vagas / n_vagas
    ic = r.n_vagas.apply(lambda k: wilson(k, n_vagas))
    r["ic95_inf"] = [100 * a for a, _ in ic]
    r["ic95_sup"] = [100 * b for _, b in ic]
    return r.round(2)


def por_grupo(vagas, skills, coluna, tipo):
    base = skills[skills.tipo == tipo].merge(vagas[["id", coluna]], left_on="vaga_id", right_on="id")
    totais = vagas.groupby(coluna).id.nunique()
    t = base.groupby([coluna, "skill"]).vaga_id.nunique().unstack(0).fillna(0)
    t = (100 * t / totais).round(1)
    t.loc["(n vagas)"] = totais
    ordem = t.drop(index="(n vagas)").max(axis=1).sort_values(ascending=False).index
    return t.loc[list(ordem) + ["(n vagas)"]]


def coocorrencia(skills, tipo, top=25):
    s = skills[skills.tipo == tipo]
    pares = {}
    for _, grupo in s.groupby("vaga_id"):
        for a, b in combinations(sorted(grupo.skill), 2):
            pares[(a, b)] = pares.get((a, b), 0) + 1
    df = pd.DataFrame([(a, b, n) for (a, b), n in pares.items()], columns=["skill_a", "skill_b", "n_vagas"])
    return df.sort_values("n_vagas", ascending=False).head(top)


def consistencia(vagas, skills, minimo=50):
    tot = vagas.fonte.value_counts()
    fontes = list(tot[tot >= minimo].index)
    if len(fontes) < 2:
        return "_Menos de duas fontes com vagas suficientes._"
    base = skills.merge(vagas[["id", "fonte"]], left_on="vaga_id", right_on="id")
    pct = base.groupby(["skill", "fonte"]).vaga_id.nunique().unstack(fill_value=0)
    pct = (pct.reindex(columns=fontes, fill_value=0) / tot[fontes])
    return pct.corr(method="spearman").round(2).to_markdown()


def exportar_painel():
    """Cria dados/painel.db: só as vagas da população, sem a descrição completa dos anúncios.

    É o banco usado pelo painel publicado. O texto integral das vagas (conteúdo das
    empresas/plataformas) fica apenas no banco completo, no computador de quem coleta.
    """
    destino = config.PAINEL_DB_PATH
    destino.unlink(missing_ok=True)
    con = conectar()
    con.execute("ATTACH DATABASE ? AS p", (str(destino),))
    con.executescript("""
        CREATE TABLE p.vaga_info AS SELECT * FROM vaga_info WHERE na_populacao = 1;
        CREATE TABLE p.vagas AS
            SELECT id, fonte, titulo, empresa, publicada_em, cidade, estado, modalidade, url
            FROM vagas WHERE id IN (SELECT vaga_id FROM p.vaga_info);
        CREATE TABLE p.vaga_skill AS
            SELECT * FROM vaga_skill WHERE vaga_id IN (SELECT vaga_id FROM p.vaga_info);
        CREATE INDEX p.ix_skill_vaga ON vaga_skill (vaga_id);
    """)
    con.commit()
    con.execute("DETACH DATABASE p")
    con.close()


def main():
    config.RESULTADOS_DIR.mkdir(exist_ok=True)
    vagas, skills, excluidas = carregar()
    n = len(vagas)
    out = config.RESULTADOS_DIR

    rk = ranking(skills, n)
    rk.to_csv(out / "ranking_geral.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
    for tipo in ("hard", "soft", "requisito"):
        rk[rk.tipo == tipo].to_csv(out / f"ranking_{tipo}.csv", index=False, sep=";", decimal=",",
                                   encoding="utf-8-sig")
        for col in ("subarea", "senioridade", "fonte"):
            por_grupo(vagas, skills, col, tipo).to_csv(out / f"{tipo}_por_{col}.csv", sep=";", decimal=",",
                                                        encoding="utf-8-sig")
        if tipo != "requisito":
            coocorrencia(skills, tipo).to_csv(out / f"coocorrencia_{tipo}.csv", index=False, sep=";",
                                              encoding="utf-8-sig")

    cat = (skills.groupby(["tipo", "categoria"]).vaga_id.nunique().reset_index(name="n_vagas"))
    cat["pct_vagas"] = (100 * cat.n_vagas / n).round(1)
    cat.sort_values(["tipo", "n_vagas"], ascending=[True, False]).to_csv(
        out / "categorias.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")

    pd.crosstab(excluidas.exclusao, excluidas.fonte, margins=True, margins_name="Total").to_csv(
        out / "exclusoes_por_fonte.csv", sep=";", encoding="utf-8-sig")
    vagas.fonte.value_counts().to_csv(out / "amostra_fontes.csv", sep=";", encoding="utf-8-sig")
    vagas.subarea.value_counts().to_csv(out / "amostra_subareas.csv", sep=";", encoding="utf-8-sig")
    vagas.senioridade.value_counts().to_csv(out / "amostra_senioridade.csv", sep=";", encoding="utf-8-sig")

    # ---- resumo em Markdown ----
    datas = pd.to_datetime(vagas.publicada_em, errors="coerce", utc=True)
    por_vaga = skills.groupby(["vaga_id", "tipo"]).size().unstack(fill_value=0).reindex(vagas.id, fill_value=0)

    def tabela(df, k=15):
        linhas = ["| # | Skill | Categoria | % vagas | IC 95% |", "|---|---|---|---|---|"]
        for i, r in enumerate(df.head(k).itertuples(), 1):
            linhas.append(f"| {i} | {r.skill} | {r.categoria} | {r.pct_vagas:.1f} | "
                          f"{r.ic95_inf:.1f}–{r.ic95_sup:.1f} |")
        return "\n".join(linhas)

    md = f"""# Resumo da pesquisa — skills em vagas de engenharia

Gerado em {date.today():%d/%m/%Y} por `analise.py`.

## Amostra
- **{n} vagas únicas** na população do estudo (cargos {', '.join(sorted(config.CARGOS_POPULACAO))}),
  de {vagas.empresa.nunique()} empresas, vindas de {vagas.fonte.nunique()} fontes
- {n + len(excluidas)} anúncios coletados; {len(excluidas)} excluídos (motivos abaixo)

### Vagas por fonte
{vagas.fonte.value_counts().to_markdown()}

### Exclusões
{excluidas.exclusao.value_counts().to_markdown()}

- Publicação entre **{datas.min():%d/%m/%Y}** e **{datas.max():%d/%m/%Y}**
- Escopo da extração: {(vagas.escopo == 'secoes').mean():.1%} das vagas pelas seções
  Responsabilidades/Requisitos; o restante pelo texto completo
- Média por vaga: {por_vaga.get('hard', pd.Series([0])).mean():.1f} hard skills,
  {por_vaga.get('soft', pd.Series([0])).mean():.1f} soft skills
- Vagas sem nenhuma soft skill detectada: {(por_vaga.get('soft', 0) == 0).mean():.1%}

### Vagas por subárea
{vagas.subarea.value_counts().to_markdown()}

### Vagas por cargo
{vagas.cargo.value_counts().to_markdown()}

### Vagas por senioridade
{vagas.senioridade.value_counts().to_markdown()}

## Consistência entre fontes
Correlação de Spearman entre os rankings de cada par de fontes (todas as skills,
fontes com 50 ou mais vagas). Valores altos indicam que o resultado não depende da fonte.

{consistencia(vagas, skills)}

## Top 15 hard skills
{tabela(rk[rk.tipo == 'hard'])}

## Top 15 soft skills
{tabela(rk[rk.tipo == 'soft'])}

## Requisitos não-skill
{tabela(rk[rk.tipo == 'requisito'], 10)}

> % vagas = proporção de vagas que mencionam a skill ao menos uma vez.
> IC 95% = intervalo de confiança de Wilson para a proporção.
"""
    (out / "resumo.md").write_text(md, encoding="utf-8")
    exportar_painel()  # antes da planilha: o painel usa a planilha pronta se ela for mais nova que o banco
    (out / "planilha_skills.xlsx").write_bytes(planilha.gerar(vagas, skills))
    print(f"Resultados gravados em {out}")
    print(md[:1500])


if __name__ == "__main__":
    main()
