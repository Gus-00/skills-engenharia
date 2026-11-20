"""InfoJobs Brasil — páginas de listagem + JobPosting de cada vaga.

Respeita o robots.txt do site (listagens e páginas de vaga não são bloqueadas).
"""
import re

from .jsonld import job_posting, para_vaga

NOME = "infojobs"
BASE = "https://www.infojobs.com.br"
TERMOS = ["engenheiro", "engenheira", "engenharia", "estagio-engenharia"]
MAX_PAGINAS = 60
PAUSA = 3.0  # segundos; site HTML com limite de taxa
LINK = re.compile(r'href="(/vaga-de-[^"]+__(\d+)\.aspx)"')


def coletar(cliente, ja_tem):
    for termo in TERMOS:
        links = {}
        for pagina in range(1, MAX_PAGINAS + 1):
            html = cliente.texto(f"{BASE}/vagas-de-emprego-{termo}.aspx", params={"Page": pagina})
            novos = {i: p for p, i in LINK.findall(html or "") if i not in links}
            if not novos:
                break
            links.update(novos)
        n_novas = 0
        for id_original, caminho in links.items():
            if ja_tem(id_original):
                yield {"id_original": id_original, "ja_coletada": True}
                continue
            jp = job_posting(cliente.texto(BASE + caminho))
            if jp:
                n_novas += 1
                yield para_vaga(jp, id_original, BASE + caminho, termo)
        print(f"  [infojobs] {termo!r}: {len(links)} vagas listadas, {n_novas} páginas novas lidas")
