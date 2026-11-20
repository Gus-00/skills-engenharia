"""Sólides Vagas — API JSON usada pelo próprio site (vagas.solides.com.br).

A busca por título é aproximada (devolve também vagas parecidas); o filtro por
título em coleta.py descarta o que não é de engenharia.
"""
NOME = "solides"
URL = "https://vagas.solides.com.br/api/vacancies"
POR_PAGINA = 20  # máximo aceito pela API
TERMOS = ["engenheiro", "engenheira", "engenharia", "estagio engenharia"]
MAX_PAGINAS = 150

MODALIDADE = {"presencial": "on-site", "remoto": "remote", "hibrido": "hybrid"}


def _nomes(lista):
    return ", ".join(x.get("name", "") for x in (lista or []))


def coletar(cliente, ja_tem):
    for termo in TERMOS:
        n = 0
        for pagina in range(1, MAX_PAGINAS + 1):
            r = cliente.get(URL, params={"page": pagina, "take": POR_PAGINA, "title": termo, "locations": ""})
            corpo = r.json() if r is not None else {}
            dados = corpo.get("data") or []
            for v in dados:
                n += 1
                yield {
                    "id_original": v["id"], "titulo": v.get("title"), "empresa": v.get("companyName"),
                    "descricao": v.get("description"), "publicada_em": v.get("createdAt"),
                    "prazo": (v.get("date") or {}).get("due"),
                    "cidade": (v.get("city") or {}).get("name"), "estado": (v.get("state") or {}).get("code"),
                    "modalidade": MODALIDADE.get(v.get("jobType"), v.get("jobType")),
                    "tipo": _nomes(v.get("recruitmentContractType")),
                    "url": f"https://vagas.solides.com.br/vaga/{v['id']}",
                    "termo_busca": termo,
                }
            if not dados or pagina >= corpo.get("totalPages", 0):
                break
        print(f"  [solides] {termo!r}: {n} vagas lidas")
