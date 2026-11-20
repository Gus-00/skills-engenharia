# Resumo da pesquisa — skills em vagas de engenharia

Gerado em 20/11/2026 por `analise.py`.

## Amostra
- **1850 vagas únicas** na população do estudo (cargos Engenheiro(a), Estágio, Trainee),
  de 976 empresas, vindas de 4 fontes
- 2807 anúncios coletados; 957 excluídos (motivos abaixo)

### Vagas por fonte
| fonte     |   count |
|:----------|--------:|
| gupy      |     682 |
| solides   |     608 |
| infojobs  |     530 |
| vagas_com |      30 |

### Exclusões
| exclusao                            |   count |
|:------------------------------------|--------:|
| cargo: Técnico/Auxiliar/Assistente  |     322 |
| cargo: Analista/Especialista/Gestão |     281 |
| banco de talentos                   |     123 |
| cargo: Outros                       |     117 |
| duplicata na mesma fonte            |      88 |
| anuncio suspeito                    |       8 |
| titulo sem engenharia               |       7 |
| texto invalido                      |       7 |
| duplicata entre fontes              |       4 |

- Publicação entre **01/03/2021** e **17/11/2026**
- Escopo da extração: 79.1% das vagas pelas seções
  Responsabilidades/Requisitos; o restante pelo texto completo
- Média por vaga: 3.5 hard skills,
  1.4 soft skills
- Vagas sem nenhuma soft skill detectada: 50.3%

### Vagas por subárea
| subarea                       |   count |
|:------------------------------|--------:|
| Civil                         |     600 |
| Engenharia (geral/outras)     |     393 |
| Software/Dados/Computação     |     221 |
| Produção/Processos/Qualidade  |     198 |
| Mecânica/Mecatrônica          |     158 |
| Elétrica/Eletrônica/Automação |     149 |
| Segurança do Trabalho         |      44 |
| Comercial/Aplicação           |      29 |
| Química/Alimentos/Materiais   |      26 |
| Ambiental/Sanitária           |      16 |
| Biomédica/Clínica             |       8 |
| Agronômica/Florestal          |       8 |

### Vagas por cargo
| cargo         |   count |
|:--------------|--------:|
| Engenheiro(a) |    1134 |
| Estágio       |     683 |
| Trainee       |      33 |

### Vagas por senioridade
| senioridade            |   count |
|:-----------------------|--------:|
| Não informada          |     763 |
| Estágio                |     683 |
| Sênior                 |     184 |
| Pleno                  |      91 |
| Júnior                 |      63 |
| Trainee                |      33 |
| Liderança/Especialista |      33 |

## Consistência entre fontes
Correlação de Spearman entre os rankings de cada par de fontes (todas as skills,
fontes com 50 ou mais vagas). Valores altos indicam que o resultado não depende da fonte.

| fonte    |   gupy |   solides |   infojobs |
|:---------|-------:|----------:|-----------:|
| gupy     |   1    |      0.81 |       0.7  |
| solides  |   0.81 |      1    |       0.87 |
| infojobs |   0.7  |      0.87 |       1    |

## Top 15 hard skills
| # | Skill | Categoria | % vagas | IC 95% |
|---|---|---|---|---|
| 1 | Pacote Office / Excel | Ferramentas de gestão e dados | 35.0 | 32.8–37.2 |
| 2 | Planejamento e controle (cronograma/custos) | Gestão e Melhoria contínua | 27.1 | 25.1–29.1 |
| 3 | AutoCAD | Software CAD/CAE/BIM | 19.0 | 17.2–20.8 |
| 4 | Orçamento de obras | Civil e Construção | 18.7 | 17.0–20.5 |
| 5 | Inglês | Idiomas | 17.1 | 15.4–18.9 |
| 6 | Desenho técnico | Software CAD/CAE/BIM | 15.4 | 13.8–17.1 |
| 7 | Gestão de obras / Execução | Civil e Construção | 14.4 | 12.8–16.1 |
| 8 | Normas técnicas (ABNT) | Normas e Certificações | 10.4 | 9.1–11.8 |
| 9 | Manutenção (preventiva/preditiva) | Mecânica e Manufatura | 9.1 | 7.9–10.5 |
| 10 | Gestão de projetos | Gestão e Melhoria contínua | 7.5 | 6.3–8.8 |
| 11 | Cloud (AWS/Azure/GCP) | Programação e TI | 7.3 | 6.2–8.6 |
| 12 | Python | Programação e TI | 7.2 | 6.2–8.5 |
| 13 | MS Project | Ferramentas de gestão e dados | 7.0 | 5.9–8.2 |
| 14 | Power BI | Ferramentas de gestão e dados | 7.0 | 5.9–8.2 |
| 15 | Gestão de contratos / fornecedores | Gestão e Melhoria contínua | 6.8 | 5.7–8.0 |

## Top 15 soft skills
| # | Skill | Categoria | % vagas | IC 95% |
|---|---|---|---|---|
| 1 | Comunicação | Comunicação e Relacionamento | 23.0 | 21.1–24.9 |
| 2 | Proatividade | Atitude e Autogestão | 16.3 | 14.7–18.1 |
| 3 | Trabalho em equipe | Comunicação e Relacionamento | 14.9 | 13.3–16.6 |
| 4 | Liderança | Liderança e Gestão de pessoas | 10.4 | 9.1–11.9 |
| 5 | Pensamento analítico | Pensamento e Resolução | 7.7 | 6.6–9.0 |
| 6 | Resolução de problemas | Pensamento e Resolução | 7.7 | 6.6–9.0 |
| 7 | Organização / Gestão do tempo | Atitude e Autogestão | 6.5 | 5.5–7.7 |
| 8 | Aprendizado contínuo | Atitude e Autogestão | 6.3 | 5.2–7.5 |
| 9 | Comprometimento / Responsabilidade | Atitude e Autogestão | 5.1 | 4.2–6.2 |
| 10 | Autonomia | Atitude e Autogestão | 4.7 | 3.8–5.7 |
| 11 | Negociação | Comunicação e Relacionamento | 4.3 | 3.4–5.3 |
| 12 | Tomada de decisão | Liderança e Gestão de pessoas | 4.2 | 3.3–5.2 |
| 13 | Relacionamento interpessoal | Comunicação e Relacionamento | 3.7 | 2.9–4.6 |
| 14 | Atenção aos detalhes | Pensamento e Resolução | 3.6 | 2.8–4.5 |
| 15 | Foco em resultados | Atitude e Autogestão | 3.5 | 2.8–4.5 |

## Requisitos não-skill
| # | Skill | Categoria | % vagas | IC 95% |
|---|---|---|---|---|
| 1 | Registro no CREA | Registro e documentação | 13.5 | 12.0–15.1 |
| 2 | Pós-graduação / Mestrado | Formação | 8.3 | 7.2–9.7 |
| 3 | Disponibilidade para viagens | Disponibilidade | 5.7 | 4.8–6.9 |
| 4 | CNH | Registro e documentação | 5.3 | 4.4–6.4 |
| 5 | Disponibilidade para mudança/turnos | Disponibilidade | 1.0 | 0.6–1.5 |

> % vagas = proporção de vagas que mencionam a skill ao menos uma vez.
> IC 95% = intervalo de confiança de Wilson para a proporção.
