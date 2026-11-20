"""Coleta vagas de engenharia de várias fontes e grava em dados/vagas.db.

Uso:
    python coleta.py                      # fontes padrão: gupy, solides, infojobs
    python coleta.py gupy solides         # só as fontes indicadas
Fontes: gupy, solides, infojobs, vagas_com (fora do padrão: o site bloqueia coleta automatizada)

Rodar várias vezes (ex.: diariamente) acumula vagas novas sem duplicar:
a chave é '<fonte>:<id da vaga na fonte>'. Duplicatas ENTRE fontes (a mesma vaga
anunciada em dois sites) são tratadas depois, em extrai.py.
"""
import re
import sys
from datetime import datetime, timezone

import config
from comum import Cliente, conectar, normalizar
from fontes import FONTES, PADRAO

COLUNAS = ["titulo", "empresa", "descricao", "publicada_em", "prazo", "cidade", "estado",
           "modalidade", "tipo", "url", "termo_busca"]


def coletar_fonte(con, modulo, agora):
    filtro = re.compile(config.FILTRO_TITULO)
    existentes = {r[0] for r in con.execute("SELECT id FROM vagas WHERE fonte = ?", (modulo.NOME,))}
    vistos, novas = set(), 0

    def ja_tem(id_original):
        return f"{modulo.NOME}:{id_original}" in existentes

    for v in modulo.coletar(Cliente(getattr(modulo, "PAUSA", None)), ja_tem):
        vid = f"{modulo.NOME}:{v['id_original']}"
        if vid in vistos:
            continue
        vistos.add(vid)
        if v.get("ja_coletada"):
            con.execute("UPDATE vagas SET ultima_coleta = ? WHERE id = ?", (agora, vid))
            continue
        if not filtro.search(normalizar(v.get("titulo") or "")) or not v.get("descricao"):
            continue
        novas += vid not in existentes
        con.execute(
            f"""INSERT INTO vagas (id, fonte, {', '.join(COLUNAS)}, primeira_coleta, ultima_coleta)
                VALUES (?, ?, {', '.join('?' * len(COLUNAS))}, ?, ?)
                ON CONFLICT(id) DO UPDATE SET ultima_coleta = excluded.ultima_coleta,
                                              descricao = excluded.descricao""",
            (vid, modulo.NOME, *[None if v.get(c) is None else str(v.get(c)) for c in COLUNAS], agora, agora),
        )
        if len(vistos) % 20 == 0:
            con.commit()
        if len(vistos) % 200 == 0:
            print(f"  [{modulo.NOME}] {len(vistos)} vagas processadas, {novas} novas", flush=True)
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM vagas WHERE fonte = ?", (modulo.NOME,)).fetchone()[0]
    print(f"[{modulo.NOME}] {novas} vagas novas; {total} no banco\n")


def main(nomes):
    desconhecidas = set(nomes) - set(FONTES)
    if desconhecidas:
        raise SystemExit(f"Fonte(s) desconhecida(s): {', '.join(desconhecidas)}. Opções: {', '.join(FONTES)}")
    con = conectar()
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for nome in nomes or PADRAO:
        print(f"== {nome}")
        try:
            coletar_fonte(con, FONTES[nome], agora)
        except Exception as erro:  # uma fonte fora do ar não deve parar as outras
            con.commit()  # guarda o que já foi coletado antes da falha
            print(f"[{nome}] FALHOU: {erro!r}\n")
    for fonte, n in con.execute("SELECT fonte, COUNT(*) FROM vagas GROUP BY fonte"):
        print(f"{fonte:10s} {n}")


if __name__ == "__main__":
    main(sys.argv[1:])
