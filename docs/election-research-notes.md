# Pesquisa: calendário eleitoral e disponibilidade de dados (Maryland 2026)

Pesquisado em 2026-07-02 via busca web (fontes oficiais). Ver [data-sources.md](data-sources.md) para URLs completas.

## Datas confirmadas — ciclo 2026, Maryland

| Evento | Data |
|---|---|
| Primária (Gubernatorial Primary Election) | 2026-06-23 |
| Early voting da primária | 2026-06-11 a 2026-06-18 |
| **Certificação do conteúdo/arranjo do ballot da primária** | 2026-04-14 (base legal: EL § 9-207(a)(2)) |
| Eleição geral | 2026-11-03 |
| Early voting da geral | 2026-10-22 a 2026-10-29 |
| Prazo de filiação de candidatos de partido não-principal para a geral (Deadline #1) | 2026-07-06 |

## Estado em 2026-07-02 (data de hoje)

- A **primária já ocorreu** (23/jun) e seu ballot já está certificado e é dado público real — foi isso que usamos na tarefa 3.
- A **geral (03/nov) ainda não tem ballot certificado**. O prazo de filiação de candidatos de partido não-principal só vence em 06/jul/2026 — ou seja, a lista de candidatos nem fechou ainda na data desta pesquisa.
- Certificação do ballot da geral normalmente acontece **depois** do fechamento de filiação — pelo padrão histórico do calendário eleitoral de MD, isso tende a cair entre agosto e setembro, mas essa data específica **não foi confirmada** nesta pesquisa (é inferência baseada em ciclos anteriores, não fato verificado). Antes de usar essa data para qualquer coisa, checar de novo na fonte oficial.

## Implicação prática

**Não é possível hoje montar um ballot real e certificado para a eleição geral de novembro/2026.** Popular `elections`/`ballot_styles`/`contests`/`candidates` para a geral agora seria necessariamente dado inventado ou provisório (candidatos ainda não confirmados) — o mesmo erro que motivou remover as `ballot_measures` fictícias do `main.py` antigo.

Recomendação: a tarefa 4 (popular `elections`/`deadlines`) deve criar a **linha da eleição geral** (data, tipo, prazos já conhecidos) para o calendário funcionar, mas **sem** ballot_styles/contests/candidates associados até a MSBE publicar o ballot certificado. Quando isso acontecer, repetir o processo da tarefa 3 (localizar PDF certificado → extrair texto → transcrever contests/candidatos).

## Cadência de atualização recomendada (do relatório de pesquisa original)

| Dado | Frequência sugerida |
|---|---|
| Calendário e prazos | Diário em ano eleitoral perto da janela; semanal fora dela |
| Lista de candidatos | Diário durante a janela de filiação; 2x/dia perto da certificação do ballot |
| Locais de votação / early voting / drop boxes | Diário nas 8 semanas antes da eleição |
| Ballot styles certificados | Checar quando a MSBE anunciar certificação; forte checagem nas semanas finais |
| Limites de distrito / precinct | Sob evento (redistricting) + verificação mensal |

## Fontes usadas nesta pesquisa

- [2026 Gubernatorial Election - Maryland State Board of Elections](https://elections.maryland.gov/elections/2026/index.html)
- [Candidacy Introduction - Maryland State Board of Elections](https://elections.maryland.gov/candidacy/index.html)
- [Official Voter Guide and Sample Ballot - Montgomery County](https://mcg.montgomerycountymd.gov/elections/VotingServices/SampleBallotVoterGuide.html)
- [Official Ballot certificado, Montgomery County, Primária 2026-06-23 (PDF)](https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf)
