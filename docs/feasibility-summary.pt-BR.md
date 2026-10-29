# Distritos e precintos — resumo da viabilidade

2026-10-29. **Dá para mostrar a cédula nos 50 estados sem depender de precintos: endereço → ponto no mapa → distritos → candidatos. Só com dados públicos e gratuitos, isso cobre 100% da população no nível federal e no estadual.** Detalhes, dados e fontes completas: [feasibility-study.pt-BR.md](feasibility-study.pt-BR.md). English version: [feasibility-summary.md](feasibility-summary.md).

## 1. Distritos: viáveis nos 50 estados

**Distrito é a área que elege um cargo** (ex.: o 8º distrito congressional de Maryland). Ele responde "quem te representa?".

**Por que é viável:** o Censo publica os distritos de todos os estados, de graça e num formato único ([TIGER/Line](https://www.census.gov/geographies/mapping-files/2027/dec/rdo/120-congressional-district-bef.html)). O [Redistricting Data Hub](https://redistrictingdatahub.org/state/national/) também publica os mapas nacionais de 2026.

| Nível | Distritos necessários | Viabilidade com dado público |
|---|---|---|
| Federal | Estado e distrito congressional | 100% |
| Estadual | Distritos da Assembleia e do Senado estaduais | ~100% |
| Local | Condado, município, distrito escolar | 100% |

**O único risco é o redistritamento.** [9 estados trocaram o mapa congressional para 2026](https://en.wikipedia.org/wiki/2025%E2%80%932026_United_States_redistricting), alguns cerca de 5 meses antes da eleição. As fontes nacionais levam de 3 a 13 meses para refletir um mapa novo. Por isso, mapas novos devem ser lidos direto da fonte do estado, com um aviso automático de mudança.

## 2. Precintos: o gargalo

**Precinto é a menor unidade de uma eleição**, parecida com a zona/seção eleitoral no Brasil. Define onde a pessoa vota e qual cédula recebe. Um distrito contém vários precintos.

**Por que é um problema:**

- São desenhados por [6.461 escritórios eleitorais locais](https://www.eac.gov/sites/default/files/2026-07/2024_EAVS_Data_Brief_US.pdf), cada um no seu formato.
- Mudam antes de várias eleições, sem calendário e sem virar notícia (ex.: o condado de Howard, MD, passou de 118 para 67 precintos em 2026).
- Não existe base nacional atual: a última aberta é de 2020; as de 2022–2024 são pagas.
- [17 dos 51 não publicam precintos](https://redistrictingdatahub.org/resources/precinct-level-data-sources/) no nível estadual; é preciso ir condado por condado.

| Situação dos precintos | Estados | % da população dos EUA |
|---|---|---|
| Com fonte estadual (pública) | 34 | 72% (65% gratuito) |
| Condado por condado | 17 | 28% |

Só Nova York, Pensilvânia, Ohio, Arizona e Missouri já somam 18% dos EUA nesse grupo difícil.

## 3. A solução: cédula por ponto no mapa

**Em vez de descobrir o precinto, o app descobre os distritos do endereço e monta a cédula a partir deles.** É o método do [Ballotpedia](https://ballotpedia.org/Sample_Ballot_Frequently_Asked_Questions), e o projeto já tem as peças.

1. **Endereço → ponto:** geocodificação.
2. **Ponto → distritos:** point-in-polygon no PostGIS.
3. **Distritos → candidatos:** lista oficial de cada disputa.
4. **Sem mapa de um distrito local:** mostrar todas as disputas daquele tipo no condado, com aviso.

| Nível | Pelo precinto | Por ponto no mapa |
|---|---|---|
| Federal (o que a Voting Buddy usa hoje) | Não precisa | 100% |
| Estadual | Não precisa | ~100% |
| Local | 72% | 100%, mas menos preciso onde falta mapa (usa o condado como reserva) |

**Onde o precinto ainda é necessário:** para mostrar o local de votação, em estilos de cédula sem mapa público e para conferir endereços perto de fronteiras (em Fairfax, a fronteira do Censo diverge dos precintos em até ~14% da área).

**Este é o caminho escolhido.** Sem precinto, o aviso de mudanças só precisa vigiar os mapas de distritos (cerca de 50 fontes estaduais, mais o Censo), em vez de milhares de condados. Os precintos já carregados de Maryland e da Virgínia passam a servir só para validar o método.

## 4. Quanto custa

**No federal e no estadual, nada: os mapas são públicos e gratuitos.** Pagar só faz sentido para terceirizar uma parte.

| Opção paga | O que resolve | Preço |
|---|---|---|
| [Geocodio](https://geocod.io/pay-as-you-go-geocoding) | Distritos federais e estaduais por endereço | 2.500 consultas/dia grátis; depois US$ 1 por 1.000 |
| [Cicero](https://www.cicerodata.com/pricing/) | Distritos, inclusive locais | A partir de US$ 298 por 5.000 endereços |
| [Ballotpedia](https://www.ballotpedia.org/Ballotpedia:Buy_Political_Data) | Candidatos por ponto no mapa | A partir de US$ 500; valor exato sob consulta |

O Ballotpedia usa o mesmo método com dado público. O que ele vende é o trabalho de coletar listas de candidatos, que é o custo real no nível local.

## 5. Conclusão e próximos passos

**Seguir pelos distritos, não pelos precintos.** O federal (o que a Voting Buddy precisa hoje) é 100% viável nos 50 estados só com dado público. O precinto fica para o local de votação e para o nível local mais tarde.

1. **Lançar o federal nos 50 estados** com o método por ponto no mapa.
2. **Ler mapas novos da fonte do estado**, com aviso automático de redistritamento.
3. **Fazer a prova real de Maryland**, que mede o erro perto das fronteiras.
4. **Deixar estadual e local para depois**; no local, pedir orçamento ao Ballotpedia para as listas de candidatos.

Para acompanhar: a emenda de Maryland vai a voto em 2026-11-03 e pode trazer um mapa congressional novo em 2028.

## Fontes principais

- [Censo, 120th Congress Block Equivalency Files](https://www.census.gov/geographies/mapping-files/2027/dec/rdo/120-congressional-district-bef.html)
- [Redistricting Data Hub, dados nacionais](https://redistrictingdatahub.org/state/national/) e [fontes de precintos por estado](https://redistrictingdatahub.org/resources/precinct-level-data-sources/)
- [Wikipedia, redistritamento 2025–2026](https://en.wikipedia.org/wiki/2025%E2%80%932026_United_States_redistricting)
- [EAC, EAVS 2024](https://www.eac.gov/sites/default/files/2026-07/2024_EAVS_Data_Brief_US.pdf)
- [Ballotpedia, como funciona a cédula de amostra](https://ballotpedia.org/Sample_Ballot_Frequently_Asked_Questions)
- [Censo 2020, população por estado](https://planning.maryland.gov/MSDC/Documents/Census/Census2020/resident-population.pdf)

A lista completa está no estudo técnico.
