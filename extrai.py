"""Extrai skills das vagas usando o dicionário (dicionario_skills.csv).

Para cada vaga:
  1. normaliza o texto (minúsculas, sem acentos, sem HTML);
  2. decide se entra na população (título, texto válido, banco de talentos, cargo, data)
     e marca duplicatas — a mesma vaga em outra fonte ou repetida na mesma fonte;
  3. recorta o escopo: de atividades/requisitos até benefícios/informações adicionais
     (exclui texto institucional e benefícios); se não houver seções, usa o texto todo;
  4. classifica cargo, subárea e senioridade pelo título;
  5. registra cada skill do dicionário encontrada (presença binária por vaga)
     e o trecho de contexto, usado depois na validação manual.

Reprocessa tudo a cada execução, então alterar o dicionário e rodar de novo é seguro.
"""
import csv
import re

import config
from comum import ESQUEMA, conectar, normalizar

CONTEXTO = 70  # caracteres de cada lado do trecho salvo


def carregar_dicionario():
    with open(config.DICIONARIO_PATH, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    for linha in linhas:
        linha["regex"] = re.compile(rf"(?<![a-z0-9])(?:{linha['padroes']})(?![a-z0-9])")
        excl = (linha.get("excluir") or "").strip()
        linha["regex_excluir"] = re.compile(excl) if excl else None
    return linhas


def buscar(item, texto):
    """Primeira ocorrência da skill cujo contexto (±40 caracteres) não casa com 'excluir'."""
    for m in item["regex"].finditer(texto):
        if item["regex_excluir"] is None:
            return m
        janela = texto[max(0, m.start() - 40): m.end() + 40]
        if not item["regex_excluir"].search(janela):
            return m
    return None


def classificar(titulo_norm, regras, padrao):
    for nome, regex in regras:
        if re.search(regex, titulo_norm):
            return nome
    return padrao


def recortar_escopo(texto):
    inicios = [m.start() for p in config.INICIO_ESCOPO for m in [re.search(p, texto)] if m]
    if not inicios:
        return texto, "completo"
    inicio = min(inicios)
    fins = [m.start() for p in config.FIM_ESCOPO for m in [re.search(p, texto[inicio:])] if m]
    fim = inicio + min(fins) if fins else len(texto)
    return texto[inicio:fim], "secoes"


def titulo_chave(titulo_norm):
    """Título reduzido para comparar vagas: sem códigos, pontuação e palavras de gênero."""
    t = re.sub(r"[^a-z ]", " ", titulo_norm)
    t = re.sub(r"\b(pessoa|a|o|as|os|vaga|para|em|de|da|do|e)\b", " ", t)
    return " ".join(t.split())


def shingles(texto, k=5):
    palavras = re.findall(r"[a-z0-9]+", texto)
    return {tuple(palavras[i:i + k]) for i in range(max(1, len(palavras) - k + 1))}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def texto_valido(texto):
    palavras = texto.split()
    if len(texto) < config.TEXTO_MIN_CARACTERES:
        return False
    amostra = palavras[:300]
    return len(set(amostra)) / len(amostra) >= config.DIVERSIDADE_MIN


def motivo_exclusao(v):
    if not re.search(config.FILTRO_TITULO, v["titulo_norm"]):
        return "titulo sem engenharia"
    if not texto_valido(v["texto_norm"]):
        return "texto invalido"
    if re.search(config.TEXTO_SUSPEITO, v["texto_norm"]):
        return "anuncio suspeito"
    if v["tipo"] in config.TIPOS_EXCLUIDOS or re.search(config.TITULO_EXCLUIDO, v["titulo_norm"]):
        return "banco de talentos"
    if v["cargo"] not in config.CARGOS_POPULACAO:
        return f"cargo: {v['cargo']}"
    if config.DATA_MINIMA and (v["publicada_em"] or "") < config.DATA_MINIMA:
        return "data"
    return None


def marcar_duplicatas(vagas):
    """Agrupa por título reduzido; dentro do grupo, compara descrições (Jaccard)."""
    prioridade = {f: i for i, f in enumerate(config.PRIORIDADE_FONTES)}
    grupos = {}
    for v in vagas:
        if v["exclusao"] is None:
            grupos.setdefault(titulo_chave(v["titulo_norm"]), []).append(v)
    for grupo in grupos.values():
        grupo.sort(key=lambda v: (prioridade.get(v["fonte"], 99), v["publicada_em"] or ""))
        mantidas = []
        for v in grupo:
            v["sh"] = shingles(v["texto_norm"])
            igual = next((m for m in mantidas if jaccard(v["sh"], m["sh"]) >= config.DEDUP_JACCARD), None)
            if igual:
                v["duplicata_de"] = igual["id"]
                v["exclusao"] = ("duplicata entre fontes" if igual["fonte"] != v["fonte"]
                                 else "duplicata na mesma fonte")
            else:
                mantidas.append(v)


def main():
    con = conectar()
    dicionario = carregar_dicionario()
    con.execute("DROP TABLE IF EXISTS vaga_info")  # recria com o esquema atual
    con.executescript(ESQUEMA)
    con.execute("DELETE FROM vaga_skill")

    vagas = []
    for vid, fonte, titulo, descricao, tipo, publicada_em in con.execute(
            "SELECT id, fonte, titulo, descricao, tipo, publicada_em FROM vagas"):
        titulo_norm = normalizar(titulo)
        v = {"id": vid, "fonte": fonte, "titulo_norm": titulo_norm, "texto_norm": normalizar(descricao),
             "tipo": tipo, "publicada_em": publicada_em, "duplicata_de": None,
             "cargo": classificar(titulo_norm, config.CARGOS, config.CARGO_PADRAO)}
        v["exclusao"] = motivo_exclusao(v)
        vagas.append(v)
    marcar_duplicatas(vagas)

    n_skills = 0
    for v in vagas:
        texto, escopo = recortar_escopo(v["texto_norm"])
        con.execute(
            "INSERT INTO vaga_info VALUES (?,?,?,?,?,?,?,?,?)",
            (v["id"], v["cargo"], int(v["exclusao"] is None), v["exclusao"], v["duplicata_de"],
             classificar(v["titulo_norm"], config.SUBAREAS, config.SUBAREA_PADRAO),
             classificar(v["titulo_norm"], config.SENIORIDADES, config.SENIORIDADE_PADRAO),
             escopo, len(texto)),
        )
        for item in dicionario:
            m = buscar(item, texto)
            if m:
                trecho = texto[max(0, m.start() - CONTEXTO): m.end() + CONTEXTO]
                con.execute("INSERT INTO vaga_skill VALUES (?,?,?,?,?)",
                            (v["id"], item["skill"], item["tipo"], item["categoria"], trecho))
                n_skills += 1
    con.commit()

    print(f"{len(vagas)} vagas processadas, {n_skills} ocorrências de skills\n")
    print("Situação por fonte (na_populacao=1 entra na análise):")
    for linha in con.execute("""SELECT v.fonte, COALESCE(i.exclusao, '-> na populacao'), COUNT(*)
                                FROM vagas v JOIN vaga_info i ON i.vaga_id = v.id
                                GROUP BY 1, 2 ORDER BY 1, 3 DESC"""):
        print(f"  {linha[0]:10s} {linha[1]:30s} {linha[2]}")


if __name__ == "__main__":
    main()
