"""Funções compartilhadas: banco de dados, normalização de texto e HTTP."""
import html
import re
import socket
import sqlite3
import time
import unicodedata
from urllib.parse import urlparse

import requests

import config
from config import DB_PATH

ESQUEMA = """
CREATE TABLE IF NOT EXISTS vagas (
    id               TEXT PRIMARY KEY,   -- '<fonte>:<id na fonte>'
    fonte            TEXT,
    titulo           TEXT,
    empresa          TEXT,
    descricao        TEXT,
    publicada_em     TEXT,
    prazo            TEXT,
    cidade           TEXT,
    estado           TEXT,
    modalidade       TEXT,
    tipo             TEXT,
    url              TEXT,
    termo_busca      TEXT,
    primeira_coleta  TEXT,
    ultima_coleta    TEXT
);
CREATE TABLE IF NOT EXISTS vaga_info (
    vaga_id      TEXT PRIMARY KEY REFERENCES vagas(id),
    cargo        TEXT,
    na_populacao INTEGER,   -- 1 = entra na análise
    exclusao     TEXT,      -- motivo, quando na_populacao = 0
    duplicata_de TEXT,      -- id da vaga mantida, quando é a mesma vaga em outra fonte
    subarea      TEXT,
    senioridade  TEXT,
    escopo       TEXT,      -- 'secoes' (requisitos/responsabilidades) ou 'completo'
    n_caracteres INTEGER
);
CREATE TABLE IF NOT EXISTS vaga_skill (
    vaga_id   TEXT REFERENCES vagas(id),
    skill     TEXT,
    tipo      TEXT,
    categoria TEXT,
    trecho    TEXT,
    PRIMARY KEY (vaga_id, skill)
);
"""


def _migrar(con):
    """Bancos da 1ª versão (só Gupy, id inteiro) ganham a coluna fonte e id 'gupy:<id>'."""
    colunas = [c[1] for c in con.execute("PRAGMA table_info(vagas)")]
    if colunas and "fonte" not in colunas:
        con.executescript("""
            DROP TABLE IF EXISTS vaga_skill;
            DROP TABLE IF EXISTS vaga_info;
            ALTER TABLE vagas RENAME TO vagas_v1;
        """)
        con.executescript(ESQUEMA)
        con.execute("""
            INSERT INTO vagas SELECT 'gupy:' || id, 'gupy', titulo, empresa, descricao, publicada_em, prazo,
                   cidade, estado, modalidade, tipo, url, termo_busca, primeira_coleta, ultima_coleta
            FROM vagas_v1""")
        con.execute("DROP TABLE vagas_v1")
        con.commit()


def conectar() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # timeout + WAL: o painel pode ler o banco enquanto a coleta escreve, sem "database is locked"
    con = sqlite3.connect(DB_PATH, timeout=60)
    try:
        con.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass  # outro processo está usando o banco; o modo WAL é ativado numa próxima conexão
    _migrar(con)
    con.executescript(ESQUEMA)
    return con


def conectar_leitura(caminho=DB_PATH) -> sqlite3.Connection:
    """Conexão só de leitura (painel): não altera o banco e não disputa trava com a coleta."""
    return sqlite3.connect(f"file:{caminho.as_posix()}?mode=ro", uri=True, timeout=60)


def limpar_html(texto: str) -> str:
    # Fim de título/negrito vira ":" (marca cabeçalhos de seção); fim de parágrafo/item vira "."
    texto = re.sub(r"</(h\d|strong|b)>", ": ", texto or "", flags=re.I)
    texto = re.sub(r"<(br|/p|/li|/div)\s*/?>", ". ", texto, flags=re.I)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos, sem HTML, espaços simples."""
    texto = limpar_html(texto).lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto)


class LimiteDoSite(Exception):
    """O site bloqueou temporariamente a coleta (HTTP 429 com espera longa)."""


def esperar_rede(url, limite=900, intervalo=30):
    """Espera até o host da URL voltar a resolver no DNS (no máximo `limite` segundos)."""
    host = urlparse(url).hostname
    inicio = time.time()
    while time.time() - inicio < limite:
        time.sleep(intervalo)
        try:
            socket.getaddrinfo(host, 443)
            print(f"  rede de volta ({host})")
            return True
        except OSError:
            continue
    return False


class Cliente:
    """Sessão HTTP com pausa fixa entre requisições e novas tentativas."""

    def __init__(self, pausa=None):
        self.sessao = requests.Session()
        self.sessao.headers["User-Agent"] = config.USER_AGENT
        self.pausa = config.PAUSA_ENTRE_REQUISICOES if pausa is None else pausa

    def get(self, url, **kwargs):
        for tentativa in range(5):
            try:
                r = self.sessao.get(url, timeout=30, **kwargs)
                time.sleep(self.pausa)
                if r.status_code == 404:
                    return None
                if r.status_code == 429:  # limite do site: respeita Retry-After e desacelera
                    retry = r.headers.get("Retry-After", "")
                    espera = int(retry) if retry.isdigit() else 30 * 2 ** tentativa
                    if espera > 600:
                        raise LimiteDoSite(f"o site pediu {espera}s de espera (Retry-After); "
                                           f"rode esta fonte de novo depois desse prazo")
                    self.pausa *= 1.5
                    print(f"  429 em {url}; aguardando {espera}s (pausa agora {self.pausa:.1f}s)")
                    time.sleep(espera)
                    continue
                r.raise_for_status()
                return r
            except requests.ConnectionError as erro:
                # Queda de rede/DNS: espera a conexão voltar sem gastar tentativas da vaga.
                print(f"  sem conexão ({type(erro).__name__}); aguardando a rede voltar...")
                if not esperar_rede(url):
                    print("  rede não voltou em 15 min; pulando esta página")
                    return None
            except requests.RequestException as erro:
                espera = 5 * (tentativa + 1)
                print(f"  erro em {url} ({erro}); nova tentativa em {espera}s")
                time.sleep(espera)
        return None

    def texto(self, url, **kwargs):
        r = self.get(url, **kwargs)
        if r is None:
            return None
        try:
            return r.content.decode("utf-8")
        except UnicodeDecodeError:
            return r.content.decode("cp1252", errors="replace")
