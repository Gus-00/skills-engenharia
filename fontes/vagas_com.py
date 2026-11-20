"""VAGAS.com — páginas de listagem (/vagas-de-<termo>) + JobPosting de cada vaga.

Respeita o robots.txt do site (a listagem /vagas-de-* e as páginas /vagas/v<id> são permitidas).
"""
import re

from .jsonld import job_posting, para_vaga

NOME = "vagas_com"
BASE = "https://www.vagas.com.br"
TERMOS = ["engenheiro", "engenheira", "engenharia", "estagio-engenharia", "estagio-em-engenharia"]
MAX_PAGINAS = 60
PAUSA = 3.0  # segundos; site HTML com limite de taxa
LINK = re.compile(r'href="(/vagas/v(\d+)/[^"#?]+)"')


def coletar(cliente, ja_tem):
    for termo in TERMOS:
        links = {}
        for pagina in range(1, MAX_PAGINAS + 1):
            html = cliente.texto(f"{BASE}/vagas-de-{termo}", params={"pagina": pagina})
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
        print(f"  [vagas_com] {termo!r}: {len(links)} vagas listadas, {n_novas} páginas novas lidas")
