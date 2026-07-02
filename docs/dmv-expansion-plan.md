# Plano: de 1 endereço para o DMV inteiro

Última atualização: 2026-07-02. Ver escopo atual em [mvp-scope.md](mvp-scope.md).

Duas frentes independentes: **geografia** (onde ficam os distritos/precincts) e **dado eleitoral** (quem concorre, em qual ballot). A geografia é resolvível com scripts reutilizáveis; o dado eleitoral hoje depende de transcrição manual de PDF por falta de API estruturada.

## Frente 1 — Geografia (expandir `district_layers`/`district_boundaries`)

### Virginia: faltam Arlington, Alexandria, Prince William, Falls Church, Fairfax City, Manassas, Manassas Park

Processo por localidade:
1. Achar o servidor ArcGIS REST do condado/cidade (cada um publica o seu — não existe um serviço estadual único de precincts para VA, ao contrário de MD)
2. Inspecionar `{MapServer}?f=json` para achar o `layer id` certo (distritos eleitorais, precincts) e o **nome oficial da camada** (não confiar em nome de arquivo antigo — foi exatamente o bug que corrigimos no layer de precincts de MD, que estava rotulado "2022" quando a fonte já tinha renomeado para "2026")
3. Adicionar a entrada em `LAYERS` no `scripts/load_district_layers.py` com o mapper de campos correto (cada fonte usa nomes de propriedade diferentes)
4. Rodar o script, revisar o SQL gerado, aplicar em lotes (arquivos grandes estouram o limite de 413 da API do Supabase — dividir em ~1.5MB por lote)

### Maryland e DC

Já cobertos por completo nas camadas carregadas (precincts, delegate subdistricts, wards, ANC, SMD, SBOE). Manutenção = re-rodar `load_district_layers.py` periodicamente (o script já é idempotente) e reconferir nomes oficiais de camada a cada execução, já que agências reeditam sem avisar.

## Frente 2 — Dado eleitoral real (ballot styles, contests, candidatos)

Este é o gargalo. Não existe API pública estruturada para isso em MD/DC/VA — só PDFs certificados por condado/jurisdição.

### Processo repetível (o que foi feito manualmente na tarefa 3, para 1 precinct)

1. Achar o PDF do ballot certificado da jurisdição (ex: `elections.maryland.gov/elections/<ano>/primary_ballots/<Condado>.pdf`)
2. Baixar e extrair texto com `pdftotext -layout`
3. Localizar a página do ballot style de interesse (buscar pelo código do precinct)
4. Transcrever contests + candidatos para uma estrutura de dados (como em `scripts/load_montgomery_primary_2026_bs_dem_125.py`)
5. Gerar e aplicar o SQL

### O que precisa mudar para escalar (não fazer manualmente por precinct)

- **Parser sensível a coordenadas** (`pdfplumber`, lendo posição x/y de cada palavra) em vez de `pdftotext -layout`, que embaralha layout de duas colunas — foi por isso que Comitê Central e Board of Education ficaram de fora na tarefa 3
- **Automatizar a localização do ballot style por precinct dentro do PDF**, em vez de grep manual por código de precinct
- Montgomery County sozinho tem **125+ ballot styles Democratas** (o código "BS DEM 125" indica isso) — cada um é uma combinação diferente de distritos. Popular todos exige rodar esse parser para cada um, não só transcrever à mão.
- Repetir para o ballot Republicano (não carregado ainda) e para os outros 23 condados de MD, DC (sample ballots por ward/partido) e VA (por localidade — cada uma publica separado, sem padrão único)

### Ordem de prioridade recomendada (do relatório de pesquisa original)

1. Maryland + Montgomery County completo (mais fontes oficiais estruturadas, já é o piloto)
2. Resto de Maryland (mesmo pipeline, outros condados)
3. DC (sample ballots por ward/partido, vote centers em vez de polling place fixo — modelagem ligeiramente diferente)
4. Virginia (mais fragmentado — cada localidade com sua própria fonte; lookup completo mais forte só nas eleições estaduais primárias/gerais)

## Frente 3 — Dados ainda não iniciados

- **`polling_locations` — carregado só parcialmente** (tarefa 6): os 14 early voting centers de Montgomery County (primária 2026), via PDF certificado da MSBE, geocodificados e expostos por `rpc_nearby_polling_locations` (ordenação por distância, não por precinct — early voting em MD é county-wide, não precinct-restrito). **Falta**: local de votação do dia da eleição por precinct (esse é específico por precinct, não county-wide, e não achei fonte estruturada — nem ArcGIS nem PDF simples; o lookup oficial da MSBE é só formulário web, sem API documentada), drop boxes, e early voting de DC/VA. VA/Loudoun já tem `loudoun_polling_places.geojson` disponível via `download_data.py`, nunca carregado.
- `ballot_measures` (questions/referendos) — schema pronto, zero dado real carregado
- Eleição geral de novembro/2026 — bloqueada até a MSBE certificar (ver [election-research-notes.md](election-research-notes.md))
