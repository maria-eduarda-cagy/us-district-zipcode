# Roadmap e decisões

Última atualização: 2026-10-21. Este é o rumo atual do projeto; atualize sempre que uma decisão for tomada. English version: [roadmap.md](roadmap.md).

## Rumo

1. **Terminar Maryland:** fechar as lacunas de cobertura abaixo.
2. **Terminar a DMV:** DC e o resto do norte da Virginia.
3. **API pública:** veja [public-api-plan.pt-BR.md](public-api-plan.pt-BR.md). Só começa depois de a DMV estar completa.

## Onde estamos (2026-10-21)

| Área | Cédula da geral de 2026 | Observações |
|---|---|---|
| Maryland (24 jurisdições) | **Carregada**: 1.991 estilos em 1.975 de 2.040 precintos | Os 65 sem cédula: 34 de preenchimento, sem eleitores (-09x/-999), e 31 polígonos defasados (abaixo). Primária e resultados só para o precinto 008-006 de Montgomery |
| Condado de Fairfax, VA | **Carregada**: todos os 266 precintos | Disputas da cidade de Herndon, precinto dividido Pioneer, explicações oficiais das questões |
| Alexandria, VA | **Carregada**: todos os 32 precintos | Uma cédula para a cidade: Senado, Câmara do 8º distrito, 3 emendas |
| Resto do norte da Virginia | Precintos carregados (GIS do ELECT), cédulas ainda não | Prince William: cédulas acessíveis (uma por precinto). Arlington, Fairfax City, Manassas, Manassas Park, Loudoun: os sites bloqueiam acesso automatizado, e as cédulas precisam ser baixadas à mão. Falls Church: nenhum arquivo de cédula encontrado |
| DC | Não carregada | Camadas de ward, ANC, SMD e SBOE carregadas; fonte da cédula de amostra não confirmada (o dcboe.org bloqueia acesso automatizado) |

## Próximos passos

### 1. Terminar Maryland
- ~~Howard~~ **corrigido em 2026-10-21:** a camada estadual foi recarregada (Howard 118 → 67 precintos, batendo com as cédulas).
- ~~Garrett, Kent~~ **corrigido em 2026-10-21:** os 17 distritos eleitorais não divididos estavam na camada sem VTD; os códigos agora são derivados (veja o registro de decisões).
- **Checagem de consistência polígono × cédula (2026-10-21):** para cada precinto de MD com cédula, um ponto dentro do polígono cai nos distritos congressional, de senado, de delegados e de cidade da cédula. As exceções são Baltimore County 09-008 (59% no 42B e 41% no 42A pela camada de delegados de 2022; a cédula certificada diz 42B para o precinto inteiro) e um precinto dividido de Cumberland, como esperado.
- **Polígonos defasados:** a camada estadual foi montada com arquivos dos condados de 2025, anteriores a algumas mudanças de precintos de 2026.
  - **Anne Arundel 04-025** (precinto novo, sem polígono em lugar nenhum; a camada do próprio condado também é anterior): os eleitores dele caem no polígono de um vizinho cuja cédula tem **outro distrito congressional e de senado**. Mitigado em 2026-10-21: o `sample-ballot` agora sinaliza essas cédulas (`district_mismatches`), e a interface indica a busca oficial do estado. A correção de verdade ainda depende do polígono do precinto.
  - **Calvert 03-002** (sem polígono) e **31 precintos em 8 condados** que estão na camada mas em nenhuma cédula (provavelmente consolidados): endereços ali recebem só os distritos, sem cédula.
  - **Worcester 01-003/01-004** (sem polígono): sem impacto, as quatro cédulas 01-00x são idênticas.
- **Talbot:** 5 precintos divididos diferem só pelo distrito do Board of Education; sem camada de fronteiras, todos os estilos possíveis são mostrados.

### 2. Terminar a DMV
- Localidades da Virginia além de Fairfax e Alexandria: os precintos de todas já estão carregados; as cédulas dependem das cédulas de amostra de cada uma. Prince William é a próxima (acessível; precisa do distrito congressional de cada precinto, das 4 cidades e da eleição especial do distrito 20 da Câmara de Delegados). Os 5 sites bloqueados precisam dos PDFs baixados no navegador.
- Calendário da Virginia: só o dia da eleição está carregado (faltam prazos de registro e de votação antecipada).
- DC: confirmar a fonte da cédula de amostra.

### 3. API pública
Veja [public-api-plan.pt-BR.md](public-api-plan.pt-BR.md).

## Registro de decisões

### 2026-10-21
- **Os precintos da Virginia vêm dos arquivos GIS por localidade do Departamento de Eleições** (uma fonte, mesmo formato para todas), exceto o condado de Fairfax, que mantém a camada validada do próprio condado. A camada antiga de Loudoun foi removida para que um endereço nunca caia em dois precintos; onde as camadas de localidades vizinhas se sobrepõem na fronteira, o `sample-ballot` usa o precinto do condado do endereço.
- **Disputas e emendas comuns a todas as cédulas da Virginia ficam num módulo só** (`va_general_2026.py`), e todas as localidades apontam para as mesmas linhas (refatoração verificada: o SQL gerado para Fairfax ficou idêntico byte a byte).
- **As cédulas da Virginia são validadas contra as listas de candidatos do ELECT** (Fairfax: 25/25). As listas não substituem as cédulas de amostra: não têm a ordem dos candidatos nem as questões locais.
- **Uma cédula cujas disputas distritais não contêm o endereço é mostrada com um aviso, e não escondida** (`district_mismatches`): provavelmente ela está certa para o precinto, e o eleitor é encaminhado à busca oficial do estado. Disputas de condado não são checadas (não têm fronteira própria). Ruído conhecido: onde a fronteira congressional do TIGER difere da oficial (faixas de alguns precintos de Fairfax), o aviso pode aparecer para uma cédula correta. Nenhum aviso indevido nos 12 endereços de teste.
- **Precintos de Maryland sem VTD ganham um código derivado:** os distritos eleitorais não divididos de Garrett e Kent vêm da camada estadual só com o número do distrito; o código segue a numeração das cédulas de cada condado ("02-000" em Garrett, "02-001" em Kent), conferida contra as listas de precintos das cédulas. Polígonos sem nenhum código são pulados em vez de gravados com ID nulo.
- **Precintos de preenchimento sem eleitores (-098/-099/-999) não têm cédula, e isso é o esperado** (a camada do próprio Anne Arundel mostra 0 eleitores registrados neles).
- **A cédula certificada prevalece sobre as camadas de fronteira** quando divergem (Baltimore County 09-008): o eleitor recebe a cédula do precinto; a lista de distritos ainda pode mostrar o distrito da camada.

### 2026-10-20
- **A camada de precintos espelha a fonte ao vivo.** `load_district_layers.py` apaga distritos que a fonte deixa de publicar e reconstrói `precincts` de MD a partir de `md_precincts_2026`; se os códigos de precinto mudarem, rode `load_md_general_2026.py` depois. Motivo: a consolidação de Howard (118 → 67) deixou 51 polígonos obsoletos sobrepostos aos novos.
- **O distrito congressional de cada precinto na Virginia vem das descrições oficiais de precintos do condado, não da geometria.** O TIGER e até a camada de distritos do próprio condado divergem dos polígonos dos precintos em até ~14% da área; as descrições são exatas (só Pioneer é oficialmente dividido).
- **O redistritamento da Virginia de 2026 não vale.** Aprovado em referendo (2026-04-21), foi anulado pela Suprema Corte da Virginia (2026-05-08); vale o mapa de 2021.
- **Precintos divididos ganham um estilo de cédula por variante**; o `sample-ballot` fica com o estilo cujas disputas distritais contêm o endereço. Disputas de condado não contam, e quando os estilos continuam empatados (nenhuma camada de fronteira os distingue) todos são mostrados, em vez de chutar um.
- **As cédulas "Federal Only" de Fairfax não são carregadas:** dependem da situação do eleitor, não do endereço.
- **As explicações oficiais das questões ficam num campo próprio** (`ballot_measures.explanation` + link da fonte), literais. `impact_yes`/`impact_no` ficam reservados ao texto FOR/AGAINST impresso na cédula (Maryland). Erros de digitação de documentos oficiais são mantidos como impressos.
- **As cédulas de Maryland são lidas dos PDFs do MSBE e validadas contra as listas oficiais de candidatos do MSBE:** o loader aborta em qualquer divergência. Ele reconstrói a geral de MD numa única transação e substituiu o loader manual do BS 125 de Montgomery.
- **Cargos de condado ficam restritos ao seu condado** (o mesmo título, como "County Council District 1", existe em vários condados; juízes da Circuit Court diferem por condado mesmo dentro de um circuito). Disputas estaduais, congressionais, de senado e de delegados são compartilhadas entre condados.
- **Ordem de trabalho: terminar MD, depois a DMV, depois a API pública.**
- **A documentação acompanha cada decisão** e é mantida em inglês e em português (`*.md` e `*.pt-BR.md`) para os docs de rumo do projeto.
