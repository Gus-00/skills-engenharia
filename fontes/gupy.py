"""Portal Gupy — API JSON de busca usada pelo próprio site (portal.gupy.io)."""
import config

NOME = "gupy"
URL = "https://portal.gupy.io/api/job-search/jobs"
POR_PAGINA = 100
MAX_OFFSET = 500  # a API não devolve resultados além de offset 400


def coletar(cliente, ja_tem):
    for termo in config.TERMOS_BUSCA:
        n = 0
        for offset in range(0, MAX_OFFSET, POR_PAGINA):
            r = cliente.get(URL, params={"jobName": termo, "limit": POR_PAGINA, "offset": offset})
            dados = (r.json().get("data") or []) if r is not None else []
            for v in dados:
                n += 1
                yield {
                    "id_original": v["id"], "titulo": v.get("name"), "empresa": v.get("careerPageName"),
                    "descricao": v.get("description"), "publicada_em": v.get("publishedDate"),
                    "prazo": v.get("applicationDeadline"), "cidade": v.get("city"), "estado": v.get("state"),
                    "modalidade": v.get("workplaceType"), "tipo": v.get("type"), "url": v.get("jobUrl"),
                    "termo_busca": termo,
                }
            if len(dados) < POR_PAGINA:
                break
        print(f"  [gupy] {termo!r}: {n} vagas lidas")
