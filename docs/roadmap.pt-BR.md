# Roadmap e decisões

Última atualização: 2026-10-21. Este é o rumo atual do projeto; atualize sempre que uma decisão for tomada. English version: [roadmap.md](roadmap.md).

## Rumo

1. **Terminar Maryland:** fechar as lacunas de cobertura abaixo.
2. **Terminar a DMV:** DC e o resto do norte da Virginia.
3. **API pública:** veja [public-api-plan.pt-BR.md](public-api-plan.pt-BR.md). Só começa depois de a DMV estar completa.

## Onde estamos (2026-10-21)

| Área | Cédula da geral de 2026 | Observações |
|---|---|---|
| Maryland (24 jurisdições) | **Carregada**: 1.975 de 2.040 precintos pelas próprias cédulas + 13 inferidos (1.988) | Os 52 sem cédula: 34 precintos "fantasmas" do MSBE (sem eleitores) e 18 polígonos de precintos extintos onde a cédula não pode ser inferida (abaixo). Primária e resultados só para o precinto 008-006 de Montgomery |
| Condado de Fairfax, VA | **Carregada**: todos os 266 precintos | Disputas da cidade de Herndon, precinto dividido Pioneer, explicações oficiais das questões |
| Alexandria, VA | **Carregada**: todos os 32 precintos | Uma cédula para a cidade: Senado, Câmara do 8º distrito, 3 emendas |
| Prince William, VA | **Carregada**: todos os 103 precintos | Câmara do 7º/10º (Colgan dividido), eleição especial do distrito 20 da Câmara de Delegados (5 precintos), 4 cidades (Dumfries, Haymarket, Occoquan, Quantico) |
| Resto do norte da Virginia | Precintos carregados (GIS do ELECT), cédulas ainda não | Arlington, Fairfax City, Manassas, Manassas Park, Loudoun: os sites bloqueiam acesso automatizado, e as cédulas precisam ser baixadas à mão. Falls Church: nenhum arquivo de cédula encontrado |
| DC | Não carregada | Camadas de ward, ANC, SMD e SBOE carregadas; fonte da cédula de amostra não confirmada (o dcboe.org bloqueia acesso automatizado) |

## Próximos passos

### 1. Terminar Maryland
- ~~Howard~~ **corrigido em 2026-10-21:** a camada estadual foi recarregada (Howard 118 → 67 precintos, batendo com as cédulas).
- ~~Garrett, Kent~~ **corrigido em 2026-10-21:** os 17 distritos eleitorais não divididos estavam na camada sem VTD; os códigos agora são derivados (veja o registro de decisões).
- **Checagem de consistência polígono × cédula (2026-10-21):** para cada precinto de MD com cédula, um ponto dentro do polígono cai nos distritos congressional, de senado, de delegados e de cidade da cédula. As exceções são Baltimore County 09-008 (59% no 42B e 41% no 42A pela camada de delegados de 2022; a cédula certificada diz 42B para o precinto inteiro) e um precinto dividido de Cumberland, como esperado.
- **Polígonos defasados:** a camada estadual foi montada com arquivos dos condados de 2025, anteriores a algumas mudanças de precintos de 2026.
  - **Anne Arundel 04-025** (precinto novo, sem polígono em lugar nenhum; a camada do próprio condado também é anterior): os eleitores dele caem no polígono de um vizinho cuja cédula tem **outro distrito congressional e de senado**. Mitigado em 2026-10-21: o `sample-ballot` agora sinaliza essas cédulas (`district_mismatches`), e a interface indica a busca oficial do estado. A correção de verdade ainda depende do polígono do precinto.
  - **31 polígonos de precintos que não existem mais** (fora da lista oficial de precintos de 2026 do MSBE, que bate com as cédulas: 1.979 precintos + 34 fantasmas). **13 agora recebem cédula inferida** (2026-10-21): Calvert 03-007/03-008 (Dunkirk, Chesapeake Beach, a maior lacuna; o novo 03-002 de Calvert não tem polígono), Montgomery 05-024/06-018, St. Mary's 02-005/03-007 e 7 em Baltimore City. **18 continuam sem cédula** porque a inferência é ambígua ou impossível: Dorchester 01-002/01-003, Washington 03-005/24-002, St. Mary's 06-005, Baltimore City 11-008/11-009, Carroll 04-008/05-007, Frederick 07-006/20-002/20-003/21-005/21-006/23-003/23-004/26-003 (alguns são os 6 fantasmas de Frederick), Montgomery 04-043. A correção de verdade depende de camadas atualizadas dos condados (o servidor GIS de Calvert não respondeu; as camadas de Anne Arundel e Montgomery são tão antigas quanto a estadual).
  - **Worcester 01-003/01-004** (sem polígono): sem impacto, as quatro cédulas 01-00x são idênticas.
- **Talbot:** 5 precintos divididos diferem só pelo distrito do Board of Education; sem camada de fronteiras, todos os estilos possíveis são mostrados.

### 2. Terminar a DMV
- Localidades da Virginia além de Fairfax e Alexandria: os precintos de todas já estão carregados; as cédulas dependem das cédulas de amostra de cada uma. Os 5 sites bloqueados (Arlington, Fairfax City, Manassas, Manassas Park, Loudoun) precisam dos PDFs baixados no navegador; Falls Church não tem arquivo de cédula.
- Calendário da Virginia: só o dia da eleição está carregado (faltam prazos de registro e de votação antecipada).
- DC: confirmar a fonte da cédula de amostra.

### 3. API pública
Veja [public-api-plan.pt-BR.md](public-api-plan.pt-BR.md).

## Registro de decisões

### 2026-10-21
- **A cédula de um polígono de precinto extinto só é inferida quando não há ambiguidade:** todos os precintos de 2026 do mesmo distrito eleitoral do condado cujos distritos localizáveis (congressional, senado, delegados, cidade) cobrem a maior parte do polígono têm exatamente a mesma cédula. O estilo é marcado "(inferred)", e a interface diz que a cédula vem dos precintos atuais com os mesmos distritos. Fora disso, o endereço continua "só distritos". 13 de 31 inferidos.
- **Os precintos divididos de Talbot continuam como estilos empatados:** eles se dividem por distrito do Board of Education, e não existe camada pública com essas fronteiras.
- **Os precintos 706 a 711 de Prince William recebem a cédula padrão do 7º distrito, embora a cédula de novembro deles não esteja na página do condado:** ficam 100% no 7º distrito, sem cidade nem eleição especial, então a cédula é totalmente determinada (igual à dos outros 54 precintos comuns do 7º). Registrado como inferência, não transcrição.
- **As disputas de cidade são um estilo à parte nos precintos onde a cidade fica** (as cédulas "só para residentes" de Prince William, como em Herndon): a camada `place` escolhe, pelo endereço, o estilo com ou sem a cidade.
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
