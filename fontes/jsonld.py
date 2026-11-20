"""Leitura do bloco schema.org/JobPosting (JSON-LD) das páginas de vaga.

JobPosting é o formato padrão que os sites de emprego publicam para o Google for Jobs,
por isso é a forma mais estável de ler título, descrição, empresa e local de uma página.
"""
import json
import re

_SCRIPT = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S | re.I)


def job_posting(html):
    for bloco in _SCRIPT.findall(html or ""):
        try:
            dados = json.loads(bloco.strip())
        except json.JSONDecodeError:
            continue
        for item in dados if isinstance(dados, list) else dados.get("@graph", [dados]):
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return None


def para_vaga(jp, id_original, url, termo):
    org = jp.get("hiringOrganization") or {}
    local = jp.get("jobLocation") or {}
    if isinstance(local, list):
        local = local[0] if local else {}
    end = local.get("address") or {}
    tipo = jp.get("employmentType")
    return {
        "id_original": id_original, "titulo": jp.get("title"),
        "empresa": org.get("name") if isinstance(org, dict) else str(org),
        "descricao": jp.get("description"), "publicada_em": jp.get("datePosted"),
        "prazo": jp.get("validThrough"), "cidade": end.get("addressLocality"),
        "estado": end.get("addressRegion"),
        "modalidade": "remote" if jp.get("jobLocationType") == "TELECOMMUTE" else None,
        "tipo": ", ".join(tipo) if isinstance(tipo, list) else tipo,
        "url": url, "termo_busca": termo,
    }
