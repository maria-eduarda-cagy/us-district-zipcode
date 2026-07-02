# Arquitetura de dados

Última atualização: 2026-07-02.

## Visão geral do pipeline

```
Endereço → Geocoding (Census → ArcGIS fallback) → PostGIS overlay (rpc_district_lookup)
  → District stack (CD, SLDU, SLDL, county, place, unsd, precinct, delegate subdistrict, ward, ANC, SMD...)
  → precinct → ballot_style → contests → candidates / measures
  → Resposta unificada: offices + measures + ballots + eventos eleitorais
```

Implementado como Supabase (Postgres + PostGIS) com duas Edge Functions (`search`, `sample-ballot`).

## Bancos de tabelas (duas gerações coexistindo)

### Tabelas legadas (já existiam antes deste trabalho, nunca versionadas em migration até 2026-07-02)

- `cd119`, `sldu`, `sldl`, `county`, `place`, `unsd` — uma tabela por tipo de camada, colunas `id`/`name`/`geom`, dados TIGER/Line para MD+DC+VA inteiros
- `layer_metadata` — existe mas está vazia (0 linhas), não é usada de fato
- `cd119_raw`, `sldu_raw`, etc. — tabelas de staging com todos os atributos originais do TIGER

Essas tabelas sustentam a função `rpc_district_lookup` desde antes deste projeto ter migrations. **Não foram tocadas nem migradas** — só foram registradas em `district_layers` (ver abaixo) para permitir que `contests.district_layer_id` referencie `cd119`, `sldu` etc.

### Tabelas novas (criadas em 2026-07-02, migrations em `supabase/migrations/`)

- `district_layers` / `district_boundaries` — registro genérico de camada + geometria, usado para toda camada nova que não é TIGER (precincts de MD, wards/ANC/SMD/SBOE de DC, distritos de supervisor de VA). `rpc_district_lookup` faz `UNION ALL` entre as tabelas legadas e essas novas — ver migration `20260702130000_fix_rpc_district_lookup_legacy_tables.sql`.
- `elections`, `deadlines` — eleições e prazos
- `precincts` — precinct como entidade própria (separada de `district_boundaries`, pensada para ligar com `ballot_styles`)
- `offices`, `contests`, `candidates` — cargo abstrato vs. corrida específica vs. candidato, seguindo a distinção recomendada nos relatórios de pesquisa originais
- `ballot_styles`, `ballot_style_contests` — estilo de cédula (por eleição + precinct + partido) e quais contests ele contém
- `ballot_measures`, `ballot_style_measures` — questions/referendos (schema pronto, ainda sem dado real carregado)
- `polling_locations` — locais de votação (schema pronto, ainda sem dado carregado)
- `sources` — proveniência: toda linha carregada por script tem `source_url`, `fetched_at`/`effective_date`, para auditoria

Todas as tabelas novas têm RLS habilitado **sem policies** — só a `service_role key` das Edge Functions lê/escreve. A anon key nunca acessa tabela diretamente, só via `rpc_district_lookup` e as Edge Functions.

## Scripts de carga (`scripts/`)

- `load_district_layers.py` — busca ao vivo 9 camadas ArcGIS REST (MD precincts/delegate subdistricts, DC wards/ANC/SMD/SBOE, VA Fairfax/Loudoun) e gera SQL idempotente (`ON CONFLICT DO UPDATE`) para `district_layers`/`district_boundaries`. Reutilizável — roda de novo sempre que uma fonte publicar atualização.
- `load_montgomery_primary_2026_bs_dem_125.py` — **não é reutilizável automaticamente**. Contém os contests/candidatos do ballot BS DEM 125 transcritos manualmente do PDF certificado da MSBE. Serve de modelo/padrão para repetir o processo em outros ballot styles, não de pipeline genérico.
- `load_md_2026_elections_calendar.py` — popula `elections`/`deadlines` (primária certificada + geral agendada) a partir de datas verificadas em [election-research-notes.md](election-research-notes.md).
- `load_montgomery_early_voting_2026_primary.py` — geocodifica (Census, fallback ArcGIS) e carrega os 14 early voting centers oficiais de Montgomery County (PDF certificado da MSBE) em `polling_locations`.

## Edge Functions

- `supabase/functions/search` — endereço → geocode → `rpc_district_lookup` → memberships (todos os distritos que contêm o ponto)
- `supabase/functions/sample-ballot` — geocode + memberships +:
  - `contests`/`measures`/`candidates` reais via embedding PostgREST (`precincts → ballot_styles → ballot_style_contests → contests → offices/district_layers/sources/candidates`), filtrados por `include_downballot`
  - `polling_locations`: 5 locais mais próximos via RPC `rpc_nearby_polling_locations` (ordenação por `ST_Distance`, não dá para fazer isso só com filtros REST)
  - `election_events`: todos os `deadlines` + `elections` associados, via embedding PostgREST simples
  - `ballot_status`: `"loaded"` ou `"not_available"` — nunca inventa dado quando não há ballot_style carregado para o precinct

## Incidente relevante (2026-07-02)

A primeira migration de `district_layers` recriou `rpc_district_lookup` apontando só para as tabelas novas (vazias), quebrando a busca em produção momentaneamente porque as tabelas legadas com dado real (`cd119` etc.) não eram conhecidas até serem inspecionadas diretamente no banco. Corrigido na mesma sessão com uma migration de hotfix que faz `UNION ALL` entre legado e novo. Lição: **o schema de produção nunca esteve documentado antes deste trabalho** — daí a importância de manter esta pasta `/docs` atualizada.
