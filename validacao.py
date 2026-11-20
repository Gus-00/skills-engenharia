"""Validação manual do extrator (precisão e revocação) — recomendado para o artigo.

Passo 1 — gerar a amostra:
    python validacao.py amostra --n 60
  Cria validacao/deteccoes.csv  (uma linha por skill detectada, com o trecho)
       validacao/vagas.csv      (uma linha por vaga, com o texto analisado)

Passo 2 — anotar (Excel/LibreOffice):
  - deteccoes.csv: coluna "correto" = 1 se a skill realmente é pedida no trecho, 0 se não.
  - vagas.csv: coluna "faltou" = skills do dicionário que a vaga pede e NÃO foram
    detectadas, separadas por "|" (use os nomes exatos da coluna skill do dicionário).

Passo 3 — calcular as métricas:
    python validacao.py metricas
  Precisão = detecções corretas / detecções
  Revocação = detecções corretas / (detecções corretas + faltantes)
"""
import argparse

import pandas as pd

import config
from comum import conectar, normalizar
from extrai import recortar_escopo

DET = config.VALIDACAO_DIR / "deteccoes.csv"
VAG = config.VALIDACAO_DIR / "vagas.csv"


def gerar_amostra(n, semente):
    config.VALIDACAO_DIR.mkdir(exist_ok=True)
    if DET.exists():
        raise SystemExit(f"{DET} já existe. Apague-o para gerar outra amostra (cuidado: perde anotações).")
    con = conectar()
    vagas = pd.read_sql(
        """SELECT v.id AS vaga_id, v.fonte, v.titulo, v.descricao, i.subarea FROM vagas v
           JOIN vaga_info i ON i.vaga_id = v.id WHERE i.na_populacao = 1""", con)
    amostra = vagas.sample(n=min(n, len(vagas)), random_state=semente)
    amostra["texto_analisado"] = amostra.descricao.map(lambda d: recortar_escopo(normalizar(d))[0])
    amostra["faltou"] = ""
    amostra[["vaga_id", "fonte", "titulo", "subarea", "texto_analisado", "faltou"]].to_csv(
        VAG, index=False, sep=";", encoding="utf-8-sig")

    marcas = ",".join("?" * len(amostra))
    det = pd.read_sql(f"SELECT vaga_id, skill, tipo, trecho FROM vaga_skill WHERE vaga_id IN ({marcas})",
                      con, params=list(amostra.vaga_id))
    det["correto"] = ""
    det.sort_values(["vaga_id", "tipo", "skill"]).to_csv(DET, index=False, sep=";", encoding="utf-8-sig")
    print(f"{len(amostra)} vagas e {len(det)} detecções para anotar em {config.VALIDACAO_DIR}")


def metricas():
    det = pd.read_csv(DET, sep=";", encoding="utf-8-sig")
    vag = pd.read_csv(VAG, sep=";", encoding="utf-8-sig").fillna({"faltou": ""})
    det = det[det.correto.astype(str).str.strip().isin(["0", "1"])]
    det["correto"] = det.correto.astype(int)
    if det.empty:
        raise SystemExit("Nenhuma detecção anotada ainda (coluna 'correto').")

    dic = pd.read_csv(config.DICIONARIO_PATH, sep=";", encoding="utf-8")
    tipo_de = dict(zip(dic.skill, dic.tipo))
    faltas = [(s.strip(), tipo_de.get(s.strip(), "?")) for f in vag.faltou for s in str(f).split("|") if s.strip()]
    faltas = pd.DataFrame(faltas, columns=["skill", "tipo"])
    desconhecidas = faltas[faltas.tipo == "?"].skill.unique()
    if len(desconhecidas):
        print("Aviso: nomes fora do dicionário em 'faltou':", ", ".join(desconhecidas))

    linhas = []
    for tipo in ["hard", "soft", "requisito", "TOTAL"]:
        d = det if tipo == "TOTAL" else det[det.tipo == tipo]
        fn = len(faltas) if tipo == "TOTAL" else (faltas.tipo == tipo).sum()
        vp = d.correto.sum()
        prec = vp / len(d) if len(d) else float("nan")
        rev = vp / (vp + fn) if (vp + fn) else float("nan")
        f1 = 2 * prec * rev / (prec + rev) if prec + rev else float("nan")
        linhas.append({"tipo": tipo, "deteccoes": len(d), "corretas": vp, "faltantes": fn,
                       "precisao": round(prec, 3), "revocacao": round(rev, 3), "f1": round(f1, 3)})
    res = pd.DataFrame(linhas)
    print(res.to_string(index=False))

    por_skill = (det.groupby("skill").correto.agg(["count", "mean"])
                 .rename(columns={"count": "deteccoes", "mean": "precisao"})
                 .sort_values("precisao"))
    print("\nSkills com pior precisão (revise os padrões no dicionário):")
    print(por_skill[por_skill.precisao < 0.8].round(2).to_string())
    res.to_csv(config.VALIDACAO_DIR / "metricas.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
    por_skill.round(3).to_csv(config.VALIDACAO_DIR / "precisao_por_skill.csv", sep=";", decimal=",",
                              encoding="utf-8-sig")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("amostra")
    a.add_argument("--n", type=int, default=60)
    a.add_argument("--semente", type=int, default=42)
    sub.add_parser("metricas")
    args = ap.parse_args()
    gerar_amostra(args.n, args.semente) if args.cmd == "amostra" else metricas()
