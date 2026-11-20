# Skills em vagas de engenharia

Ferramenta de pesquisa que coleta vagas de engenharia de plataformas brasileiras de
recrutamento (Gupy, Sólides, InfoJobs e VAGAS.com), remove anúncios duplicados, identifica as
**hard skills**, **soft skills** e **requisitos** pedidos em cada vaga e gera rankings,
tabelas por subárea, senioridade e fonte, uma planilha para análise e um painel interativo.

## Como usar

**Windows:** dois cliques em `rodar.bat`. Na primeira execução ele instala as dependências;
depois mostra um menu para coletar, atualizar os resultados, abrir o painel e rodar a validação.

**Linha de comando:**

```bash
python -m pip install -r requirements.txt
python coleta.py          # baixa as vagas (gupy, solides, infojobs) -> dados/vagas.db  (~1 h na 1ª vez)
python coleta.py infojobs # ou só algumas fontes
python extrai.py          # identifica as skills
python analise.py         # gera resultados/ e dados/painel.db
python -m streamlit run app.py --server.port 8510   # painel em http://localhost:8510
```

**Planilha.** `resultados/planilha_skills.xlsx` reúne o ranking de todas as skills com IC 95%,
tabelas por subárea, senioridade, fonte e cargo, a lista de vagas com as skills de cada uma e o
link do anúncio, a coocorrência de skills e o dicionário. No painel, o botão
**Planilha Excel completa** baixa a mesma planilha só com as vagas do filtro atual.
Os CSVs usam `;` como separador e `,` como decimal (Excel em português).

**Coleta interrompida.** Basta rodar `coleta.py` de novo: vagas já salvas não são baixadas
outra vez. Se a internet cair, o coletor espera a conexão voltar (até 15 min). Se um site
responder HTTP 429 pedindo espera longa, o coletor encerra aquela fonte e avisa.

| Arquivo | Função |
|---|---|
| `config.py` | Termos de busca, regras de subárea/senioridade/cargo, definição da população |
| `dicionario_skills.csv` | Dicionário de skills (nome, tipo, categoria, padrões, exclusões) |
| `coleta.py` | Roda os coletores de `fontes/`; nas coletas seguintes só baixa vagas novas |
| `fontes/` | Um coletor por plataforma (`gupy.py`, `solides.py`, `infojobs.py`, `vagas_com.py`) |
| `extrai.py` | Define a população, remove duplicatas, recorta as seções relevantes e detecta as skills |
| `analise.py` | Rankings com IC 95%, tabelas cruzadas, consistência entre fontes, banco do painel |
| `planilha.py` | Planilha Excel formatada |
| `validacao.py` | Amostra para anotação manual e cálculo de precisão/revocação |
| `app.py` | Painel Streamlit (filtros, gráficos, comparação entre subáreas, busca por skill, downloads) |

## Publicação do painel

O painel publicado lê `dados/painel.db`, uma versão enxuta do banco gerada por `analise.py`:
contém só as vagas analisadas, com título, empresa, local, skills detectadas, um trecho curto de
contexto e o link do anúncio. O texto integral dos anúncios fica apenas no banco completo
(`dados/vagas.db`), que não vai para o repositório.

Hospedagem no [Streamlit Community Cloud](https://share.streamlit.io): *Create app* →
repositório → branch `main` → arquivo `app.py` → *Deploy*.

Para atualizar os dados publicados:

```bash
python coleta.py && python extrai.py && python analise.py
git add dados/painel.db resultados && git commit -m "Atualiza dados" && git push
```

## Método

**Fontes.** Plataformas de recrutamento com atuação nacional que publicam a descrição completa
da vaga de forma pública e estruturada:

| Fonte | Acesso | Perfil |
|---|---|---|
| Gupy (`portal.gupy.io`) | API JSON de busca do portal | ATS de grandes e médias empresas; a vaga é publicada pela empresa contratante |
| Sólides (`vagas.solides.com.br`) | API JSON de busca do portal | ATS usado por pequenas e médias empresas |
| InfoJobs (`infojobs.com.br`) | Listagem + bloco schema.org `JobPosting` de cada vaga | Portal generalista, com muitas vagas de indústria |
| VAGAS.com (`vagas.com.br`) | Listagem + bloco schema.org `JobPosting` de cada vaga | Fora da coleta padrão: o site bloqueia por 24 h (HTTP 429) mesmo em ritmo lento; entram só as vagas coletadas antes do bloqueio |

`JobPosting` é o formato padronizado que os sites publicam para o Google for Jobs.
Fontes não utilizadas: **LinkedIn** e **Indeed** proíbem coleta automatizada nos termos de uso;
a **Catho** bloqueia as páginas de busca no `robots.txt`; a **API Adzuna** entrega apenas um
trecho truncado da descrição. Os coletores respeitam o `robots.txt`, fazem no máximo uma
requisição por segundo (três nos sites HTML) e obedecem ao cabeçalho `Retry-After`.
Na Gupy cada busca devolve no máximo 500 vagas, por isso são usados 34 termos
(`config.TERMOS_BUSCA`).

**População.** Entram no banco as vagas cujo título contém "engenheir" ou "engenhari".
A análise considera os anúncios que (a) têm texto válido (150 caracteres ou mais, sem repetição
artificial), (b) não são anúncios suspeitos (cobrança de taxa, cadastro em site externo),
(c) não são banco de talentos ou cadastro reserva, (d) são para cargos de Engenheiro(a), Estágio
ou Trainee, classificados pelo título, (e) opcionalmente foram publicados após `DATA_MINIMA`, e
(f) não são duplicatas. Cargos de técnico, auxiliar, assistente e analista "de engenharia" ficam
fora por não serem vagas *para engenheiros*. O motivo de cada exclusão é registrado em
`resultados/exclusoes_por_fonte.csv`.

**Duplicatas.** A mesma vaga pode aparecer em mais de um site ou repetida no mesmo site
(ex.: uma por cidade). Dois anúncios contam como uma vaga quando têm o mesmo título normalizado
e descrições com similaridade de Jaccard ≥ 0,5 (conjuntos de 5 palavras seguidas). Fica a versão
da fonte de maior prioridade (`config.PRIORIDADE_FONTES`). A unidade de análise é a
**vaga única**, não o anúncio.

**Escopo do texto.** A extração usa o trecho entre o primeiro cabeçalho de atividades/requisitos
("Responsabilidades e atribuições", "Requisitos:", "O que você vai fazer"…) e o cabeçalho de
benefícios ou informações adicionais, de modo que o texto institucional da empresa e a lista de
benefícios não contam como exigência da vaga. Sem esses cabeçalhos, usa-se o texto completo;
o resumo informa a proporção de cada caso.

**Extração.** Dicionário com 114 itens (82 hard, 27 soft, 5 requisitos) agrupados em
categorias. Cada item tem padrões (regex sobre texto minúsculo e sem acento) e, quando
necessário, padrões de exclusão para contextos enganosos (ex.: "protocolos de comunicação" não
conta como a soft skill Comunicação). A métrica é a **presença por vaga**: a skill conta uma vez
por vaga, independentemente de quantas vezes apareça.

**Classificação hard/soft.** Hard skills são conhecimentos técnicos, ferramentas, métodos,
normas e idiomas; soft skills são competências comportamentais e interpessoais. As categorias
podem ser mapeadas para a taxonomia ESCO (competências transversais × conhecimentos/aptidões)
ou para o *Future of Jobs* do Fórum Econômico Mundial. "Requisitos" (CREA, CNH, pós-graduação,
disponibilidade) são analisados à parte.

**Estatística.** Proporção de vagas que mencionam cada skill, com intervalo de confiança de 95%
de Wilson; tabelas cruzadas por subárea, senioridade, fonte e cargo; pares de skills mais
frequentes na mesma vaga. Como checagem de robustez, o resumo traz a correlação de Spearman entre
os rankings de cada par de fontes.

**Validação.** `validacao.py amostra` sorteia vagas (semente 42) e lista as detecções com o
trecho de contexto. Cada detecção é anotada como correta ou não, e as skills não detectadas são
registradas; `validacao.py metricas` calcula precisão, revocação e F1 por tipo e a precisão por
skill. A concordância entre dois anotadores pode ser medida pelo kappa de Cohen.

## Limitações

- **Cobertura das fontes.** As plataformas cobrem bem o setor privado; concursos públicos e
  vagas divulgadas só no LinkedIn ou por indicação ficam de fora. O peso de cada fonte depende
  de quantas vagas ela tem.
- **Deduplicação aproximada.** Anúncios da mesma vaga com títulos diferentes não são unidos, e
  vagas distintas com texto padronizado da mesma empresa podem ser unidas.
- **Retrato de um momento.** As plataformas mostram só as vagas abertas no dia da coleta. Para
  medir tendência, a coleta deve ser repetida periodicamente; o banco acumula vagas novas e
  registra `primeira_coleta`.
- **Menção ≠ demanda real.** Soft skills costumam ficar implícitas: quase metade das vagas não
  cita nenhuma, então as proporções de soft skills são um limite inferior.
- **Obrigatório × desejável.** O método não distingue requisito obrigatório de diferencial.
- **Dicionário fechado.** Skills fora do dicionário não são detectadas; a revocação medida na
  validação quantifica essa perda.
- **Classificação pelo título.** Subárea e senioridade vêm do título; parte das vagas fica como
  "geral" ou "não informada".

## Ética e uso dos dados

A coleta usa apenas dados públicos das vagas, sem dados pessoais (LGPD), com intervalo entre
requisições e respeito ao `robots.txt` e aos limites de cada site. O repositório não redistribui
o texto integral dos anúncios.
