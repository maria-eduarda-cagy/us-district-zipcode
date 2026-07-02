# Catálogo de fontes de dados

Última atualização: 2026-07-02. "Carregado" = já está no banco Supabase. "Disponível" = a fonte existe e foi mapeada, mas ainda não foi carregada.

## Geografia / distritos

| Fonte | Cobertura | Status | URL base |
|---|---|---|---|
| Census TIGER/Line | CD, SLDU, SLDL, county, place, unsd — MD+DC+VA | Carregado (legado, anterior a este trabalho) | `www2.census.gov/geo/tiger/` |
| Maryland iMAP — MD_ElectionBoundaries | Precincts MD (nome oficial: "Maryland Precincts 2026"), delegate subdistricts ("Maryland Legislative Districts 2022") | Carregado | `mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer` |
| DC GIS — Administrative_Other_Boundaries | Wards ("Ward - 2022"), ANC ("Advisory Neighborhood Commission - 2023"), SMD ("Single Member District - 2023") | Carregado | `maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer` |
| DC GIS — Education | SBOE districts | Carregado | `maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Education_WebMercator/MapServer` |
| Fairfax County GIS | Supervisor districts | Carregado | `fairfaxcounty.gov/idrisi/rest/services/Jade/Electoral/MapServer` |
| Loudoun County GIS | Election districts, precincts, polling places (polling places só mapeado, não carregado) | Parcial (precincts/districts carregados; polling places não) | `logis.loudoun.gov/gis/rest/services/COL/ElectionDistricts/MapServer` |
| Arlington, Alexandria, Prince William, Falls Church, Fairfax City, Manassas, Manassas Park (VA) | — | **Não mapeado ainda** — cada um provavelmente publica GIS próprio, precisa descobrir URL individualmente | — |

## Calendário e ballots

| Fonte | O que tem | Status |
|---|---|---|
| Maryland State Board of Elections (`elections.maryland.gov`) | Calendário oficial, candidatos, ballots certificados em PDF por condado | Usado para pesquisa de datas ([election-research-notes.md](election-research-notes.md)) e para o ballot de Montgomery ([mvp-scope.md](mvp-scope.md)) |
| PDF certificado — primária MD 2026, Montgomery County | `elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf` — 1542 páginas, certificado 2026-04-14 | Extraído parcialmente (1 de ~125+ ballot styles Democratas do condado) |
| PDF certificado — Early Voting Centers 2026 (MSBE) | `elections.maryland.gov/elections/2026/2026_Early_Voting_Centers-EN.pdf` — publicado 2026-04-23 | **Carregado**: 14 centros de Montgomery County (geocodificados e em `polling_locations`) |
| Montgomery County Board of Elections (`mcg.montgomerycountymd.gov/elections`) | Voter guide personalizado, mapas de precinct/distrito, mapa online de early voting | Mapeado, não usado para carga ainda |
| DC Board of Elections | Sample ballots por ward/partido, calendário | Não pesquisado a fundo ainda |
| Virginia Department of Elections | Candidatos, polling/ballot lookup, GIS de redistricting | Não pesquisado a fundo ainda |
| Google Civic API | Eleições, divisões OCD, contests | Não usado — fonte secundária de cross-check, nunca fonte de verdade |

## Regras usadas neste projeto

1. **Fonte oficial > agregador secundário.** Nunca usar Vote.org/Ballotpedia/Google Civic como fonte de verdade — só como checagem cruzada.
2. **Nunca inventar dado.** Se a fonte oficial não publicou ainda (ex: ballot da geral 2026), a tabela fica vazia, não recebe placeholder. Isso já causou um problema real neste projeto (measures fictícias no `main.py` antigo) e foi corrigido.
3. **Todo dado carregado tem `source_url` rastreável** na tabela `sources`, ligado via `source_id` nas linhas de `elections`, `ballot_styles`, `contests`, `candidates`, `district_layers`, `district_boundaries`, `precincts`.
4. **Verificar nome oficial da camada antes de rotular**, não confiar em nome de arquivo herdado (aconteceu com precincts de MD: arquivo antigo dizia "2022", fonte já tinha atualizado para "2026").
