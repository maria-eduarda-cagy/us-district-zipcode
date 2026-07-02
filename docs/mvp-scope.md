# Escopo do MVP

Última atualização: 2026-07-02 (tarefa 7 concluída: validação ponta a ponta).

## Validação ponta a ponta (tarefa 7, 2026-07-02)

Rodada completa para o endereço de teste, com três checagens:

1. **Conferência automática contra o PDF certificado**: os 50 nomes de candidatos retornados pela API foram comparados programaticamente (não manualmente) contra o texto bruto extraído do PDF oficial — **0 divergências**. As 14 regras de "vote for N" também batem exatamente.
2. **Teste visual no navegador** (não só `curl`): encontrou um bug real que a checagem por API não pegou — o campo `scope` (`at_large` vs `district`) estava sendo inferido incorretamente a partir de `district_id` ser nulo ou não. Contests como "County Executive" e "County Council At-Large" têm `district_id` preenchido (para linkar ao nome/geometria do condado) mas são cargos at-large, não distritais — a inferência antiga invertia isso. Corrigido com uma coluna `scope` explícita em `contests` (migration `20260702160000_contests_explicit_scope.sql`), lida diretamente em vez de inferida. 6 contests estavam afetados; todos corrigidos e reconferidos visualmente.
3. **Caso negativo** (endereço fora do MVP, `1600 Pennsylvania Avenue NW, Washington, DC`): geocodifica e mostra os distritos de DC normalmente (dado real, carregado na tarefa 2), mas a seção de ballot degrada corretamente para "No offices were generated for this address" — sem inventar nada, sem erro no console.

9/9 testes automatizados passando.

## Decisão

O MVP roda de ponta a ponta **apenas para o endereço de teste**:

```
104 Ashton Oaks Court, Ashton, Maryland 20861
```

Não é uma cobertura geral de MD/DC/VA. Os dados eleitorais reais (ballot styles, contests, candidatos) existem só para esse endereço. A parte de geografia (distritos) tem cobertura mais ampla, mas desigual — ver detalhe abaixo. Expandir para o DMV inteiro é trabalho futuro, descrito em [dmv-expansion-plan.md](dmv-expansion-plan.md).

## O que funciona hoje, ponta a ponta

Para o endereço de teste, `search` e `sample-ballot` (Edge Functions em produção) retornam:

- Geocoding real (Census, fallback ArcGIS)
- Todos os distritos: Congressional District 8, State Senate District 14, State Legislative District 14, Montgomery County, Ashton-Sandy Spring CDP, Montgomery County Public Schools, House of Delegates Subdistrict 14, precinct 008-006
- Ballot style real e certificado: **BS DEM 125** (Democratic, primária 2026-06-23)
- 14 contests e 50 candidatos reais, extraídos do PDF certificado da MSBE
- **Locais de votação reais**, ordenados por distância (RPC `rpc_nearby_polling_locations`): os 14 early voting centers oficiais de Montgomery County para a primária 2026, incluindo o mais próximo do endereço-teste (Sandy Spring VFD, ~1,7km)
- **Eventos eleitorais reais**: early voting start/end, election day e prazo de filiação, para a primária (certificada) e a geral (agendada)

## Cobertura por camada (o que é DMV-wide vs. só o endereço de teste)

| Camada | Cobertura real |
|---|---|
| Distritos legados (CD, SLDU, SLDL, county, place, unsd) | MD inteiro, VA inteiro, DC — herdado do `download_data.py` original, já existia antes deste trabalho |
| Precincts (MD) | MD inteiro (2074 precincts, todos os condados) |
| Delegate subdistricts (MD) | MD inteiro (71 subdistritos) |
| DC (wards, ANC, SMD, SBOE) | DC inteiro |
| VA (distritos de supervisor, precincts) | **Só Fairfax e Loudoun County** — faltam Arlington, Alexandria, Prince William, Falls Church, Fairfax City, Manassas, Manassas Park |
| **Ballot styles + contests + candidatos reais** | **Só 1 precinct**: 008-006, Ashton, Montgomery County, ballot Democrata |
| Polling locations | **Só early voting de Montgomery County** (14 centros, primária 2026) — election-day por precinct e drop boxes não carregados; VA (Loudoun) e DC não carregados |
| Ballot measures (questions/referendos) | Não carregado ainda |
| Eleição geral de novembro/2026 | Não existe ainda — não há ballot certificado publicado (ver [election-research-notes.md](election-research-notes.md)) |

## O que foi deliberadamente deixado de fora (não é bug, é decisão)

- **Comitê Central Democrata e Board of Education** do precinct 008-006: o PDF certificado usa layout em duas colunas que o `pdftotext -layout` embaralha. Em vez de arriscar associar um candidato ao contest errado, essas seções ficaram de fora. Precisa de parser sensível a coordenadas (`pdfplumber`, ver [dmv-expansion-plan.md](dmv-expansion-plan.md)).
- **Ballot Republicano** do mesmo precinct: não foi extraído, só o Democrata.
- **Eleição geral (nov/2026)**: não existe candidato certificado ainda — ver prazos em [election-research-notes.md](election-research-notes.md).

## Por que não expandir automaticamente

Cada camada nova (um condado de VA, um partido a mais, uma eleição a mais) exige repetir manualmente o processo de extração de PDF certificado (tarefa 3), porque não existe uma API estruturada para ballot styles/candidatos em MD/DC/VA — só PDFs. Isso é uma decisão consciente de escopo, não uma limitação técnica escondida.
