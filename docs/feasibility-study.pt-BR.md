# Estudo de viabilidade: distritos e precintos nos EUA

Pesquisado em 2026-10-29. Pergunta: o projeto escala para todos os estados, e como manter os dados atualizados, antes da integração com a Voting Buddy? English version: [feasibility-study.md](feasibility-study.md).

## Resumo

**Distritos são viáveis em todo o país; precintos, só em parte. Para o que a Voting Buddy mostra hoje (candidatos federais), só os distritos são necessários.**

O relatório tem duas partes: **Parte 1 — Distritos** e **Parte 2 — Precintos**, cada uma avaliada nos níveis federal, estadual e local.

| Nível | Distritos (Parte 1) | Precintos (Parte 2) |
|---|---|---|
| Federal | 100% viável, confiança alta. Só dados públicos e gratuitos | Não é necessário |
| Estadual | ~100% viável, confiança alta. Só dados públicos e gratuitos | Não é necessário, salvo exceções pontuais |
| Local | Parcial: condado, cidade e distrito escolar em 100% dos estados; os demais distritos locais não foram medidos | Necessário: 72% da população com dado público (65% gratuito), confiança média; 28% condado por condado |

- **Redistritamento:** 9 estados trocaram o mapa congressional para 2026. As fontes nacionais levam de 3 a 13 meses para refletir um mapa novo; a fonte do estado publica na hora.
- **Dado privado:** distritos por endereço são baratos (Geocodio, Cicero). Cédula por endereço, sem precinto, sai por orçamento (Ballotpedia a partir de US$ 500).
- **Hoje no projeto:** distritos de MD, VA e DC (4,7% da população dos EUA); precintos e cédulas de Maryland cobrindo 99,45% dos eleitores registrados.
- **Fora do escopo:** listas de candidatos estaduais e locais.

**Sugestão principal:** mostrar a cédula por ponto no mapa (endereço → distritos → candidatos), sem precinto. Com dados públicos, isso cobre 100% da população no federal e no estadual, e 100% no local usando o condado como reserva (veja a Parte 2).

Definições: **cobertura** = parte da população (ou dos eleitores) que o projeto atende. **Viabilidade** = parte da população onde dá para construir e manter a feature com dados públicos e gratuitos. Nenhuma das duas mede **acurácia**: isso só a prova real de Maryland vai medir.

Fontes: [população do Censo 2020 por estado](https://planning.maryland.gov/MSDC/Documents/Census/Census2020/resident-population.pdf); cobertura de Maryland do [roadmap](roadmap.pt-BR.md) (view `ballot_coverage`, 2026-10-28).

## O que é distrito e o que é precinto

**Para os candidatos federais que a Voting Buddy mostra hoje, precinto não é necessário: basta o distrito congressional.** O precinto só entra quando o app chegar à cédula completa, ao local de votação ou a disputas locais.

**O que é um precinto:** a menor unidade de organização de uma eleição nos EUA. É uma área pequena, geralmente um bairro ou parte dele, onde todos os eleitores:

- **votam no mesmo lugar** (o mesmo local de votação);
- **recebem a mesma cédula** (os mesmos cargos e candidatos);
- **têm os votos contados juntos** (o resultado sai "por precinto").

É parecido com a zona/seção eleitoral no Brasil: o endereço define a seção, e a seção define o local de votação. Exemplo: o condado de Howard, em Maryland, tem 67 precintos, e cada endereço cai em exatamente um deles.

O **distrito** responde "quem te representa?". O **precinto** responde "onde você vota e qual cédula recebe?". Um distrito contém vários precintos.

| | Distrito | Precinto |
|---|---|---|
| O que é | Área que elege um cargo (ex.: 8º distrito congressional) | Área administrativa da eleição, parecida com a zona/seção eleitoral no Brasil |
| Para que serve | Representação política: quem te representa | Logística: onde a pessoa vota, qual cédula recebe, como os votos são contados |
| Quem desenha | Legislativo, comissão ou tribunal do estado | O escritório eleitoral local |
| Quando muda | No redistritamento (raro) | Antes de qualquer eleição, por motivos práticos |
| Como se relacionam | Um distrito contém vários precintos | Cada precinto fica dentro de um só distrito de cada tipo, ou é dividido |

## Com que frequência cada um muda

O redistritamento é raro, mas deixou de ser previsível. Os precintos mudam muito mais e são o verdadeiro gargalo: não existe arquivo nacional atualizado deles.

| Camada | Quem decide | Com que frequência muda | Existe fonte nacional atualizada? |
|---|---|---|---|
| Distritos congressionais | Legislativo, comissão, tribunal ou referendo do estado | A cada 10 anos (Censo) e, agora, no meio da década: 9 estados trocaram o mapa para 2026 | Sim, com atraso: Censo (120º Congresso) e Redistricting Data Hub |
| Distritos legislativos estaduais | Os mesmos | A cada 10 anos, mais exceções (o Alabama mudou também o Senado estadual em 2026) | Sim: arquivo nacional de 2026 do Redistricting Data Hub (16/09/2026) |
| Condado, cidade, distrito escolar | Governos locais | Pouco, por anexações | Sim: TIGER/Line, anual |
| Precintos | Condado ou município | Antes de várias eleições, sem calendário nacional (ex.: Howard, MD, de 118 para 67 em 2026) | Não: o arquivo nacional aberto mais recente é de 2020; 2022–2024 são pagos |

Consequência: distritos dá para cobrir os EUA inteiros com fontes nacionais. Precintos (e portanto cédulas) precisam ser buscados estado por estado, às vezes condado por condado.

# Parte 1 — Distritos

**Distritos são viáveis nos 50 estados nos níveis federal e estadual, só com dados públicos e gratuitos.** No local, o Censo cobre as camadas básicas; o resto depende de cada condado ou cidade.

## Viabilidade dos distritos por nível

| Nível | O que o endereço precisa resolver | Fonte pública | Viabilidade | Confiança | Manutenção |
|---|---|---|---|---|---|
| Federal | Estado (Presidente e Senado) e distrito congressional (Câmara) | Censo (120º Congresso), Redistricting Data Hub, fonte do estado para mapas novos | 100% | Alta | Vigiar redistritamento: 9 estados mudaram para 2026 |
| Estadual | Distritos da Assembleia e do Senado estaduais | Censo (camadas legislativas), Redistricting Data Hub (arquivo de 2026) | ~100% (DC não tem legislativo) | Alta | Mesmo ritmo do congressional; o Alabama mudou o Senado estadual em 2026 |
| Local | Condado, cidade e distrito escolar; e também conselhos, wards, juízes e distritos especiais | O Censo cobre condado, cidade e distrito escolar; o resto só no condado ou na cidade | Camadas básicas: 100%. Demais: não medida | Baixa | Uma fonte por condado ou cidade |

- **Hoje no projeto:** distritos de MD, VA e DC, 4,7% da população dos EUA.
- **Alternativa paga:** Geocodio (federal e estadual; 2.500 consultas por dia grátis, depois US$ 1 por 1.000) e Cicero (inclui distritos locais; a partir de US$ 298 por 5.000 endereços). Detalhes em "Dados privados e preços", na Parte 2.
- **Regra de ouro:** ler o mapa novo direto da fonte do estado. O Censo e os agregadores atrasam meses (veja abaixo).

## Fontes nacionais

| Fonte | O que oferece | Custo e licença | Formato | Atualidade |
|---|---|---|---|---|
| Censo TIGER/Line | Distritos congressionais e legislativos, condados, cidades, distritos escolares | Gratuito, domínio público | Shapefile, GeoPackage, API ArcGIS (TIGERweb) | Anual. O 120º Congresso já inclui os 9 estados com mapa novo (página revisada em 07/10/2026) |
| Redistricting Data Hub (RDH) | Planos congressionais e legislativos atuais, com tabela de quarteirões; precintos nacionais de 2020 | Gratuito com conta; API só para usuários aprovados; termos a conferir | Shapefile, CSV | 120º Congresso e legislativos de 2026 publicados em 16/09/2026 |
| VEST / UF Election Lab | Fronteiras de precintos com resultados eleitorais | 2016–2020 grátis (CC BY-NC-ND: uso não comercial); 2022–2024 por assinatura | Arquivos GIS | Histórico; serve para validação, não para a eleição atual |
| Google Civic Information API | `divisionByAddress` (endereço → OCD-IDs), eleições | Gratuito com chave | API JSON | O endpoint de representantes foi desligado em abril de 2025 |
| Voting Information Project | Locais de votação e cédula, aprovados pelos órgãos eleitorais | Grátis para os estados; acesso pela API do Google; sem download aberto | API | Mais de 40 estados e DC participam |
| Cicero (Melissa) | Distritos por endereço e eleitos | Pago, por créditos | API | Diz acompanhar mudanças em tempo real |

Atenção à licença: a Voting Buddy é comercial, então dados CC BY-NC-ND (VEST) não podem ser usados no produto sem autorização. Pergunta em aberto: preços de BallotReady e L2 não foram pesquisados.

## Redistritamento no meio da década (2025–2026)

Entre agosto de 2025 e junho de 2026, 9 estados passaram a usar um mapa congressional novo em 2026 (a lista do Censo). Alguns mapas mudaram cerca de 5 meses antes da eleição, então o monitoramento precisa ser contínuo, não só depois do Censo.

| Data | Estado | Como | Vale em 2026? |
|---|---|---|---|
| 2026-08-04 | Maryland | Emenda constitucional aprovada; vai a voto em novembro. Não há mapa novo | Não (abre caminho para um mapa novo em 2028) |
| 2026-06-02 | Alabama | Suprema Corte liberou o mapa legislativo de 2023 | Sim |
| 2026-05-29 | Louisiana | Legislativo, depois de Louisiana v. Callais; primária adiada para 03/11 | Sim |
| 2026-05-07 | Tennessee | Legislativo | Sim |
| 2026-05-04 | Flórida | Legislativo | Sim |
| 2026-04-21 | Virgínia | Referendo, anulado pela Suprema Corte estadual em 08/05/2026 | Não (vale o mapa de 2021) |
| 2025-11-10 | Utah | Tribunal estadual | Sim |
| 2025-11-04 | Califórnia | Referendo (Proposition 50) | Sim |
| 2025-10-31 | Ohio | Comissão de redistritamento | Sim |
| 2025-10-22 | Carolina do Norte | Legislativo | Sim |
| 2025-09-28 | Missouri | Legislativo; bloqueado na Justiça | Não (vale o mapa antigo) |
| 2025-08-29 | Texas | Legislativo | Sim |

Quanto tempo até virar dado público:

- **Fonte do estado:** o arquivo sai junto com a proposta, antes da aprovação. No Texas, os planos ficam no Capitol Data Portal com shapefile e tabela de quarteirões. Mas cada estado publica de um jeito: uma das comissões soltou só tabela de quarteirões e PDF.
- **Fontes nacionais:** de 3 a 13 meses depois. O RDH publicou o 120º Congresso em 16/09/2026 (3,5 meses depois do Alabama, 12,5 depois do Texas). O Censo revisou o arquivo dele em 07/10/2026; a data em que cada estado entrou no Censo não está publicada.
- **É dado público e gratuito** em todos os casos verificados. Não foi preciso pagar por nenhum mapa.

Consequência: para estar certo na eleição, o projeto precisa ler a fonte do estado, não esperar o Censo.

# Parte 2 — Precintos

**Precinto só é necessário no nível local.** Lá, 72% da população pode ser coberta com dado público; os outros 28% exigem trabalho condado por condado ou uma API paga de cédula.

## Viabilidade dos precintos por nível

| Nível | Precisa de precinto? | Por quê | Viabilidade | Confiança |
|---|---|---|---|---|
| Federal | Não | Os candidatos saem do distrito congressional. O precinto só entraria para mostrar o local de votação | Não se aplica | — |
| Estadual | Não, na maioria dos casos | Os candidatos saem dos distritos legislativos. Exceção: distritos estaduais sem camada pública (ex.: Board of Education em Talbot, MD) | Não se aplica, salvo exceções | — |
| Local | Sim | A cédula local e o local de votação são definidos por precinto | 72% da população com dado público (65% gratuito); 28% condado por condado | Média |

- **Hoje no projeto:** Maryland com 99,45% dos eleitores registrados cobertos; na Virgínia, cédulas em Fairfax, Alexandria e Prince William.
- **Alternativa paga:** APIs de cédula por endereço (BallotReady, Ballotpedia, Democracy Works) dispensam o precinto. Preço sob consulta; detalhes em "Dados privados e preços".

## Sugestão: cédula por ponto no mapa, sem precinto

**É uma boa forma de evitar o precinto, e é o que o Ballotpedia faz.** Com dados públicos, cobre 100% da população no federal e no estadual. No local, cobre os cargos de condado, município e distrito escolar, e usa o condado inteiro como reserva para o resto.

Como funciona:

1. **Endereço → ponto:** geocodificação (Censo, com ArcGIS de reserva; já existe no projeto).
2. **Ponto → distritos:** point-in-polygon no PostGIS, com camadas do Censo e dos estados.
3. **Distritos → disputas e candidatos:** FEC para o federal, sempre confirmada pela lista oficial do estado.
4. **Sem mapa para um distrito local:** mostrar todas as disputas daquele tipo no condado, com um aviso (o mesmo que o [Ballotpedia faz](https://ballotpedia.org/Sample_Ballot_Frequently_Asked_Questions)).

| Nível | Viabilidade com dados públicos | Precisão | Confiança |
|---|---|---|---|
| Federal | 100% da população | Alta, exceto endereços perto de fronteiras | Alta |
| Estadual | ~100% (DC, 0,2% da população, não tem legislativo estadual) | Alta, exceto endereços perto de fronteiras | Alta |
| Local: condado, município, distrito escolar | 100% (camadas do Censo) | Alta | Média |
| Local: conselhos, wards, juízes, distritos especiais | Com mapa: não medida. Com a reserva do condado: 100% | Baixa na reserva (mostra disputas a mais) | Baixa |

Comparando: pelo precinto, o local chega a 72% da população com dado público. Por ponto, chega a 100% de cobertura, mas com menos precisão onde falta mapa.

**Onde o precinto ainda ganha:**

- **Endereços perto de fronteiras:** a geocodificação ou a camada do Censo podem errar o lado. Em Fairfax, a fronteira congressional do Censo diverge dos polígonos de precintos em até ~14% da área.
- **Cédula exata:** alguns estilos dependem de distritos sem camada pública (ex.: Board of Education em Talbot, MD).
- **Local de votação:** depende do precinto, ou de uma API de terceiros.
- **Candidatos:** o mapa não resolve a lista de candidatos, que continua sendo o trabalho pesado.

Recomendação: usar o método por ponto como padrão e o precinto só onde ele é indispensável (local de votação e estilos sem camada pública). A prova real de Maryland mede o erro perto das fronteiras.

## Por que é mais difícil acompanhar precintos

- São desenhados por milhares de escritórios locais: foram [6.461 jurisdições eleitorais em 2024](https://www.eac.gov/sites/default/files/2026-07/2024_EAVS_Data_Brief_US.pdf), cada uma com seu formato.
- Mudam por motivos práticos (local de votação novo, crescimento da população, distrito novo), sem calendário e sem virar notícia.
- Nem todo condado publica o mapa em formato GIS. Alguns têm só PDF ou um mapa na tela.
- A única base nacional oficial (os VTDs do Censo) é atualizada a cada 10 anos. A de 2020 já está defasada.

## Levantamento dos 50 estados + DC

**34 dos 51 têm alguma fonte estadual de precintos; 17 não têm, e aí é condado por condado.** A base é a [tabela de fontes de precintos do Redistricting Data Hub](https://redistrictingdatahub.org/resources/precinct-level-data-sources/) (atualizada em 2026-05-05), cruzada com o que este estudo verificou.

Critério dos grupos:

- **Grupo 1:** arquivo estadual oficial, com atualidade confirmada neste estudo.
- **Grupo 2:** existe arquivo estadual (no site ou sob pedido), mas está defasado, incompleto ou a atualidade ainda não foi confirmada. Parte deste grupo deve virar grupo 1 depois de checada.
- **Grupo 3:** o estado não publica. Os precintos têm que vir de cada condado.

### Nordeste

| Estado | Fonte dos precintos | Grupo | Observação |
|---|---|---|---|
| Connecticut | Não publicada pelo estado | 3 | Condado por condado |
| Maine | Não publicada pelo estado | 3 | Condado por condado |
| Massachusetts | [MassGIS, wards e precintos](https://www.mass.gov/info-details/massgis-data-2022-wards-and-precincts) | 2 | Versão de 2022 |
| New Hampshire | [NH GRANIT, wards de votação](https://www.nhgeodata.unh.edu/datasets/NHGRANIT::new-hampshire-political-districts-voting-wards/about) | 2 | Atualidade a confirmar |
| New Jersey | [NJOGIS, voting districts](https://njogis-newjersey.opendata.arcgis.com/search?q=voting%20districts) | 2 | Atualidade a confirmar |
| New York | Não publicada pelo estado | 3 | Condado por condado; 20,2 milhões de pessoas |
| Pensilvânia | Não publicada pelo estado | 3 | 67 condados |
| Rhode Island | [RIGIS, precintos 2022](https://www.rigis.org/datasets/edc::voting-precincts-2022/about) | 2 | Versão de 2022 |
| Vermont | [VCGI, áreas de tabulação](https://vcgi.vermont.gov/data-release/vt-house-and-senate-vote-tabulation-areas-municipal-voting-districts-available) | 2 | Atualidade a confirmar |

### Centro-Oeste

| Estado | Fonte dos precintos | Grupo | Observação |
|---|---|---|---|
| Dakota do Norte | [Secretaria de Estado](https://www.sos.nd.gov/elections/election-resources) | 2 | Atualidade a confirmar |
| Dakota do Sul | Não publicada pelo estado | 3 | Condado por condado |
| Illinois | [Conselho Eleitoral, mapas de precintos](https://www.elections.il.gov/precinctmaps/) | 2 | Atualidade e formato a confirmar |
| Indiana | [IndianaMap, 2023](https://indianamap-inmap.hub.arcgis.com/datasets/INMap::voting-district-boundaries-2023/about) | 2 | Versão de 2023 |
| Iowa | [Secretaria de Estado](https://sos.iowa.gov/precinct-and-district-shapefiles) | 2 | Planos de precintos de 2022, base Censo 2020 |
| Kansas | Não publicada pelo estado | 3 | Condado por condado |
| Michigan | [Michigan GIS, precintos 2022](https://gis-michigan.opendata.arcgis.com/datasets/2022-voting-precincts/explore) | 2 | Versão de 2022 |
| Minnesota | [Secretaria de Estado](https://sos.mn.gov/election-administration-campaigns/data-maps/voting-precincts/) | 2 | Atualidade a confirmar |
| Missouri | Não publicada pelo estado | 3 | Condado por condado |
| Nebraska | Não publicada pelo estado | 3 | Condado por condado |
| Ohio | Não publicada pelo estado | 3 | 88 condados |
| Wisconsin | [LTSB](https://gis-ltsb.hub.arcgis.com/pages/download-data) | 1 | Versão de primavera de 2026 |

### Sul

| Estado | Fonte dos precintos | Grupo | Observação |
|---|---|---|---|
| Alabama | Não publicada pelo estado | 3 | Condado por condado |
| Arkansas | [Arkansas GIS Office](http://gis.arkansas.gov/product/election-precincts/) | 2 | Atualidade a confirmar |
| Carolina do Norte | [NCSBE](https://dl.ncsbe.gov/?prefix=PrecinctMaps/) | 1 | Pasta com versões atuais e antigas |
| Carolina do Sul | Mapas dos condados sob pedido ao estado, de graça | 2 | Sem download direto |
| Delaware | [FirstMap, distritos eleitorais](https://de-firstmap-delaware.hub.arcgis.com/datasets/delaware::election-districts-1/explore) | 2 | Atualidade a confirmar |
| Distrito de Colúmbia | [Open Data DC, precintos](https://opendata.dc.gov/datasets/voting-precinct-2002/explore) | 2 | Versão do link a confirmar |
| Flórida | Mapas dos condados sob pedido ao estado, com taxa | 2 | Sem download direto; 21,5 milhões de pessoas |
| Geórgia | [Office of Reapportionment](https://www.legis.ga.gov/joint-office/reapportionment) | 2 | Cobre bem 105 de 159 condados |
| Kentucky | Não publicada pelo estado | 3 | Condado por condado |
| Louisiana | [Legislativo, shapefiles de 2020](https://redist.legis.la.gov/default_ShapeFiles2020) | 2 | Base de 2020; mapa congressional mudou em 2026 |
| Maryland | [iMAP](https://data.imap.maryland.gov/datasets/e2d183719fe345c8abfffc9cc4196390_2/explore) | 2 | Maioria dos condados de 2025 (já carregado no projeto) |
| Mississippi | Não publicada pelo estado | 3 | Condado por condado |
| Oklahoma | [OU, precintos](https://csagis-uok.opendata.arcgis.com/datasets/8c2c841e2eb54007bd1872c4274d6e07_0/explore) | 2 | Publicado por universidade; atualidade a confirmar |
| Tennessee | [TNMap, voting districts](https://hub.arcgis.com/datasets/tnmap::tn-voting-districts/about) | 2 | Atualidade a confirmar |
| Texas | [Texas Legislative Council](https://data.capitol.texas.gov/dataset/precincts) | 2 | VTDs de 2024 (atualizados em 2025-01-29) |
| Virgínia | [Departamento de Eleições](https://www.elections.virginia.gov/casting-a-ballot/redistricting/gis/) | 1 | Por localidade, mesmo formato (já carregado no projeto) |
| Virgínia Ocidental | [WVGIS Clearinghouse](https://data.wvgis.wvu.edu/pub/Clearinghouse/Boundaries/) | 2 | Atualidade a confirmar |

### Oeste

| Estado | Fonte dos precintos | Grupo | Observação |
|---|---|---|---|
| Alasca | [Estado do Alasca, precintos](https://dcra-cdo-dcced.opendata.arcgis.com/datasets/precincts/about) | 2 | Atualidade a confirmar |
| Arizona | Não publicada pelo estado | 3 | Condado por condado |
| Califórnia | [Statewide Database](https://statewidedatabase.org/election.html) | 2 | Publicada depois de cada eleição; antes, só nos 58 condados |
| Colorado | Não publicada pelo estado | 3 | Condado por condado |
| Havaí | [ArcGIS do estado](https://www.arcgis.com/home/item.html?id=37f83ac7f930421b97976956cccbd840) | 2 | Atualidade a confirmar |
| Idaho | Não publicada pelo estado | 3 | Condado por condado |
| Montana | [Biblioteca do Estado](https://mslservices.mt.gov/geographic_information/data/datalist/datalist_Details.aspx?did=%7Bb5296489-2764-4a09-9fec-1b0c3c74690c%7D) | 2 | Atualidade a confirmar |
| Nevada | [Secretaria de Estado, mapas por condado](https://www.nvsos.gov/sos/elections/county-precinct-maps) | 2 | Formato por condado a confirmar |
| Novo México | [RGIS (UNM)](https://rgis.unm.edu/rgis6/) | 2 | Publicado por universidade; atualidade a confirmar |
| Oregon | Não publicada pelo estado | 3 | Condado por condado |
| Utah | [UGRC, áreas de cédula do VISTA](https://opendata.gis.utah.gov/datasets/utah-vista-ballot-areas/about) | 2 | Vem do sistema eleitoral do estado; forte candidato a grupo 1 |
| Washington | [Secretaria de Estado](https://www.sos.wa.gov/elections/data-research/election-results-and-voters-pamphlets) | 2 | Atualidade a confirmar |
| Wyoming | Não publicada pelo estado | 3 | Condado por condado |

## Resultado nacional dos precintos

**Com os 51 avaliados, a viabilidade dos precintos é de 72% da população dos EUA** (grupos 1 e 2). Os outros 28% estão em 17 estados sem fonte estadual.

| Grupo | Estados | População (Censo 2020) | % dos EUA |
|---|---|---|---|
| 1 — oficial e atual | 3 | 25,0 milhões | 7,5% |
| 2 — arquivo estadual | 29 | 185,8 milhões | 56,1% |
| 2 — sob pedido (FL, SC) | 2 | 26,7 milhões | 8,0% |
| 3 — condado por condado | 17 | 94,0 milhões | 28,4% |

- **O grosso do custo está em 5 estados:** Nova York, Pensilvânia, Ohio, Arizona e Missouri somam 58 milhões de pessoas (18% dos EUA), quase dois terços do grupo 3.
- **A incerteza agora está no grupo 2:** 19 desses estados ainda estão com atualidade a confirmar. Checar cada fonte é o próximo passo para mover estados para o grupo 1.
- **O número bate com a fonte:** o RDH diz que cerca de dois terços dos estados publicam precintos; aqui deu 34 de 51 (67%).

**Os 72% usam só dado público, de governo.** A Flórida entra com uma pequena taxa cobrada pelo estado. Só com dado público e gratuito, a viabilidade é de 65%. Nenhum dado de empresa privada entrou na conta (veja "Dados privados e preços").

Cálculo: população de cada estado no [Censo 2020](https://planning.maryland.gov/MSDC/Documents/Census/Census2020/resident-population.pdf), somada por grupo.

## Dados privados e preços

**Nenhum fornecedor vende "precintos atuais dos 50 estados" com preço público.** O que existe são APIs que resolvem o problema por outro caminho: endereço → distritos (preço público e barato) ou endereço → cédula completa (preço sob consulta). As duas dispensam o precinto.

| Fornecedor | O que resolve | Tem precinto? | Preço |
|---|---|---|---|
| [Geocodio](https://geocod.io/pay-as-you-go-geocoding) | Distritos congressionais e legislativos por endereço | Não | 2.500 consultas por dia grátis; depois US$ 1 por 1.000. Cada distrito pedido conta como uma consulta a mais |
| [Cicero (Melissa)](https://www.cicerodata.com/pricing/) | Distritos (inclusive locais) e eleitos por endereço | Não | De US$ 298 por 5.000 endereços a US$ 8.848 por 1 milhão (US$ 0,06 a 0,009 cada); 1.000 grátis para testar; cerca de 10% de desconto para ONGs |
| [Ballotpedia](https://www.ballotpedia.org/Ballotpedia:Buy_Political_Data) | Eleições e candidatos por ponto (lat/long): federal, estadual, legislativo e as 100 maiores cidades; local em 32 estados | Não (resolve pelo ponto) | Pacotes a partir de US$ 500; valor exato sob consulta |
| [BallotReady](https://organizations.ballotready.org/ballotready-api) | Todos os candidatos da cédula, cargos, locais de votação, polígonos de distritos até o nível local | Não informado | Sob consulta (demo) |
| [Democracy Works](https://www.democracy.works/elections-api) | Datas, locais de votação e cédula (disputas e candidatos) em jurisdições com mais de 5.000 habitantes | Não informado | Sob consulta; é uma ONG |
| [UF Election Lab (VEST)](https://election.lab.ufl.edu/paid-datasets) | Fronteiras de precintos com resultados, 2022–2024 | Sim, histórico | Sob consulta |
| L2 | Arquivo de eleitores com o precinto de cada eleitor; o RDH já usou para [estimar o precinto de cada quarteirão](https://redistrictingdatahub.org/wp-content/uploads/2023/06/readme_al_20230403_vf_precs.txt) | Indireto | Sob consulta. Referência de mercado (não é preço da L2): [US$ 2.000 a 15.000 por estado, US$ 5.000 a 50.000+ por ano](https://www.vottiv.com/blog/voter-database-pricing) |

**Quanto dos 28% isso resolve:**

- **Polígonos de precinto atuais:** nenhuma opção paga resolve de forma limpa. VEST e L2 cobrem os 17 estados do grupo 3, mas com dados históricos ou estimados, que também precisariam de manutenção.
- **Cédula por endereço:** BallotReady, Ballotpedia e Democracy Works cobrem federal e estadual em todo o país. No local, a profundidade varia (Ballotpedia: 32 estados; Democracy Works: jurisdições com mais de 5.000 habitantes).
- **Conclusão:** com dado privado, a feature de cédula pode chegar perto de 100% no federal e estadual sem tocar em precinto. O custo não dá para fechar sem pedir orçamento a esses três.

**Para o orçamento da Voting Buddy:** o nível federal já sai de graça com dados públicos, e o Geocodio cobre até cerca de 1.250 endereços por dia sem custo. Pagar só faz sentido no nível local, e aí o primeiro passo é pedir o orçamento ao Ballotpedia (o único com preço inicial publicado).

Pergunta em aberto: arquivos de eleitores vendidos pelos próprios estados também trazem o precinto de cada eleitor, mas preço e regras de uso mudam por estado e não foram pesquisados.

# Comum às duas partes

## Sistema de aviso (distritos e precintos)

Duas camadas alimentam um só alerta, e nenhuma altera dados sozinha:

```
Fontes oficiais ──► Checagem de arquivos (data, hash) ──┐
                                                        ├─► Alerta (issue / e-mail) ─► Revisão humana ─► Loader + validação ─► Dados atualizados
Notícias e tribunais ─► Triagem com IA ─────────────────┘
```

A checagem de arquivos é o detector principal, porque mudança de precinto quase nunca vira notícia. A IA serve para o redistritamento, que aparece no noticiário antes de o arquivo oficial mudar.

| Tipo de fonte | Sinal de mudança | Exemplo |
|---|---|---|
| Portal CKAN | Campo `metadata_modified` do dataset | Texas Capitol Data Portal |
| Portal ArcGIS | Data da última edição, quando o serviço informa; senão, hash do arquivo | Wards do Wisconsin |
| Pasta de arquivos | Arquivo novo ou data diferente na listagem | NCSBE (`dl.ncsbe.gov`) |
| Página HTML | Hash do conteúdo ou data de revisão | Página do 120º Congresso no Censo |
| Notícias e trackers | Texto novo, lido pela IA | Ballotpedia, NCSL |

Como a IA entra:

- **Entrada:** páginas e notícias novas desde a última checagem.
- **Saída estruturada:** estado, camada (congressional, legislativa, precinto), tipo (mapa aprovado, decisão judicial, referendo), data e link da fonte.
- **Regra:** a IA só abre o alerta. A decisão de recarregar é humana, porque a IA pode errar ou deixar passar algo.

Versão mínima para começar: uma lista das fontes no repositório (o [references.pt-BR.md](references.pt-BR.md) já tem as URLs), um job diário no GitHub Actions que compara datas e hashes, e uma issue aberta para cada mudança. A IA entra depois que essa base funcionar.

### Com precinto x sem precinto

**O caminho escolhido é sem precinto.** Como a viabilidade dos precintos é menor (72% da população no local, contra 100% pelo método por ponto), o aviso passa a vigiar só os mapas de distritos. Isso deixa o sistema bem mais simples.

| | Com precinto | Sem precinto (caminho escolhido) |
|---|---|---|
| O que vigiar | Mapas de distritos e de precintos | Só mapas de distritos |
| Quantas fontes | 34 arquivos estaduais e os condados dos 17 estados sem fonte estadual | Cerca de 50 fontes estaduais, mais Censo e Redistricting Data Hub |
| Com que frequência muda | Antes de várias eleições | Raro: só no redistritamento |
| Detector principal | Checagem de arquivos, porque mudança de precinto quase nunca vira notícia | Triagem com IA, porque redistritamento sempre vira notícia; a checagem de arquivos confirma |

**O que continua sendo acompanhado no caminho sem precinto:**

- **Mapas de distritos** (congressional e legislativos), direto da fonte de cada estado.
- **Listas de candidatos:** mudam até a certificação (desistências, substituições). Passa a ser o ponto de mais trabalho.

**Os precintos já carregados (Maryland e Virgínia) viram ferramenta de validação:** servem para conferir se o método por ponto acerta os endereços perto das fronteiras. Não precisam mais ficar sempre atualizados para o produto funcionar.

## Recomendação e próximos passos

**Parte 1 — Distritos:**

1. **Lançar o nível federal para os 50 estados** com dados públicos; o estadual vem logo depois, com as mesmas fontes.
2. **Ler os mapas novos direto da fonte do estado**, sem esperar o Censo.
3. **Construir a versão mínima do aviso** (job diário + issue no GitHub) para redistritamento.
4. **Fazer a prova real de Maryland** e publicar a taxa de acerto.

**Parte 2 — Precintos:**

1. **Usar a cédula por ponto no mapa como padrão; só investir em precintos para local de votação e estilos sem camada pública.**
2. **Confirmar a atualidade das 19 fontes do grupo 2** marcadas "a confirmar".
3. **Pedir orçamento ao Ballotpedia** e comparar com BallotReady e Democracy Works, como alternativa para os 28% sem fonte estadual.
4. **Conferir licenças** antes de usar dados no produto: termos do Redistricting Data Hub e qualquer dado CC BY-NC.

Para acompanhar agora:

- **Maryland:** a emenda constitucional vai a voto em 03/11/2026. Se passar, abre caminho para um mapa congressional novo em 2028, e o projeto vai precisar trocar a camada de 2022.
- **Missouri:** o mapa novo foi barrado para 2026, mas a disputa pode voltar para 2028.

# Conclusão resumida

**Seguir pelos distritos, não pelos precintos.** Versão curta deste estudo: [feasibility-summary.pt-BR.md](feasibility-summary.pt-BR.md).

- **Distritos:** 100% viáveis no federal e ~100% no estadual, só com dados públicos e gratuitos. O risco é o redistritamento (9 estados em 2026), resolvido lendo a fonte do estado com aviso automático.
- **Precintos:** 72% da população tem fonte estadual pública (65% gratuita); 28% exige trabalho condado por condado. Por isso são o gargalo.
- **Solução:** cédula por ponto no mapa (endereço → distritos → candidatos). Cobre 100% no federal e no estadual, e 100% no local usando o condado como reserva, com menos precisão.
- **Precinto continua necessário** só para local de votação, estilos de cédula sem mapa público e endereços perto de fronteiras.
- **Custo:** zero no federal e no estadual. No local, o custo real são as listas de candidatos (Ballotpedia a partir de US$ 500).
- **Próximo passo:** federal nos 50 estados pelo método por ponto, e a prova real de Maryland para medir o erro nas fronteiras.

## Fontes

- [Wikipedia, 2025–2026 United States redistricting](https://en.wikipedia.org/wiki/2025%E2%80%932026_United_States_redistricting)
- [NCSL, Changing the Maps: Tracking Mid-Decade Redistricting](https://www.ncsl.org/redistricting-and-census/changing-the-maps-tracking-mid-decade-redistricting)
- [WYPR, emenda de redistritamento de Maryland (2026-08-04)](https://www.wypr.org/wypr-news/2026-08-04/maryland-lawmakers-pass-redistricting-constitutional-amendment-voters-will-have-final-say)
- [Censo, 120th Congress Block Equivalency Files](https://www.census.gov/geographies/mapping-files/2027/dec/rdo/120-congressional-district-bef.html)
- [TIGERweb, camada do 120º Congresso](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/54)
- [Redistricting Data Hub, dados nacionais](https://redistrictingdatahub.org/state/national/) e [sobre o RDH](https://redistrictingdatahub.org/about/)
- [UF Election Lab / VEST, precinct data](https://election.lab.ufl.edu/precinct-data/)
- [Google, desligamento da Representatives API](https://groups.google.com/g/google-civicinfo-api/c/9fwFn-dhktA/m/ftUoL83mAwAJ)
- [Democracy Works, Voting Information Project](https://www.democracy.works/voting-info-project)
- [SD Times, Cicero API](https://sdtimes.com/data/melissas-cicero-api-accurate-address-matching-for-legislative-districts-and-officeholders/)
- [revaddress, arquivos dos mapas de 2026](https://revaddress.com/blog/2026-redistricting-address-files/)
- [Texas Capitol Data Portal, plano PLANC2323](https://data.capitol.texas.gov/dataset/planc2323) e [VTDs](https://data.capitol.texas.gov/dataset/vtds)
- [NCSBE, Voting Maps/Redistricting](https://www.ncsbe.gov/results-data/voting-maps-redistricting)
- [LTSB, WI Municipal Wards](https://gis-ltsb.hub.arcgis.com/maps/2cfddfff49474fda9c81955bede7f0bd)
- [Statewide Database, 2024 general](https://statewidedatabase.org/d20/g24_geo_conv.html)
- RDH readmes: [Ohio 2024](https://redistrictingdatahub.org/wp-content/uploads/2025/05/readme_oh_2024_gen_prec.txt), [Geórgia 2024](https://redistrictingdatahub.org/wp-content/uploads/2025/07/readme_ga_2024_gen_pber.txt), [Carolina do Norte](https://redistrictingdatahub.org/state/north-carolina/)
