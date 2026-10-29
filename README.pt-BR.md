# ElectorMap & Downballot Finder (DMV + 2026 cycle)

Versão em português. English version: [README.md](README.md).

Digite um endereço em DC, Maryland ou Virginia e veja seus distritos, sua **cédula certificada real** da eleição geral de 3 de novembro de 2026 (disputas, candidatos, questões com explicações oficiais), os locais de votação antecipada próximos e o calendário eleitoral. As cédulas vêm de fontes oficiais (cédulas de amostra do estado e dos condados), são validadas contra as listas oficiais de candidatos e nunca são inventadas: onde não temos a cédula, o app diz isso.

Todas as fontes de dados com a URL exata: [docs/references.pt-BR.md](docs/references.pt-BR.md). Rumo atual, cobertura e todas as decisões: [docs/roadmap.pt-BR.md](docs/roadmap.pt-BR.md) ([EN](docs/roadmap.md)).

## Funcionalidades
- **Geocodificação**: geocodificador do Censo, com ArcGIS de reserva.
- **Distritos (point-in-polygon)**: PostGIS no Supabase — congressional, legislativo estadual, condado, cidade, distrito escolar, precinto, subdistritos de delegados, wards/ANC/SMD de DC, distritos de supervisor da VA.
- **Cédula por precinto**: o precinto do endereço → seu(s) estilo(s) de cédula → disputas, candidatos (partido, ordem na cédula) e questões. Precintos divididos (um precinto com vários estilos de cédula, por exemplo com parte dentro de uma cidade) são resolvidos pelos distritos do endereço; quando nada os distingue, todas as cédulas possíveis são mostradas.
- **Lacunas explícitas**: aviso de cobertura quando não há cédula, alerta quando os distritos da cédula não contêm o endereço (mapas de precintos mais antigos que a eleição) e nota quando a cédula é inferida.
- **Questões da cédula**: texto da questão, a explicação FOR/AGAINST impressa na cédula (Maryland) ou a explicação oficial publicada à parte (emendas da Virginia, bonds dos condados), com a fonte.
- **Resultados da primária** (primária de Maryland de 2026, um precinto de teste), **locais de votação antecipada** (todo Maryland), **calendário eleitoral** e **atualidade dos dados** (cada fonte com sua data).
- **Mapa interativo** (Leaflet.js).

## Cobertura (eleição geral de 2026)

| Área | Cédulas |
|---|---|
| Maryland (24 jurisdições) | 1.988 de 2.040 precintos. Em eleitores: 99,45% recebem a cédula do próprio precinto, 0,43% veem todas as cédulas possíveis (precintos divididos de Talbot), 0,12% estão em precintos que faltam no mapa do estado (cédula inferida ou com aviso). O resto dos polígonos: 34 precintos "fantasmas" sem eleitores e 18 de precintos que não existem mais (~333 moradores) |
| Condado de Fairfax, VA | Todos os 266 precintos |
| Alexandria, VA | Todos os 32 precintos |
| Condado de Prince William, VA | Todos os 103 precintos |
| Arlington, Fairfax City, Falls Church, Loudoun, Manassas, Manassas Park (VA) | Só distritos e precintos — cédulas de amostra ainda não carregadas |
| Washington, DC | Só distritos — fonte da cédula ainda não confirmada |

## Requisitos Prévios
- Supabase (Postgres + PostGIS) com as Edge Functions `search` e `sample-ballot` publicadas.
- Deno (para rodar os testes e as Edge Functions localmente).
- Python 3.9+ (servidor local do frontend e loaders de dados); `pdftotext`/`pdftohtml` (poppler) e `ogr2ogr` (GDAL) para os loaders.

## Guia de Instalação e Execução

### Passo 1: Clonar o repositório
```bash
git clone <repo-url>
cd us-district-zipcode
```

### Passo 2: Configurar variáveis de ambiente
Crie um arquivo `.env` (não commitar) com pelo menos:
```bash
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-jwt-que-comeca-com-eyJ...>
# para os loaders de dados (psql):
SUPABASE_DB_HOST=... SUPABASE_DB_PORT=... SUPABASE_DB_NAME=... SUPABASE_DB_USER=... SUPABASE_DB_PASSWORD=...
```

Observações:
- A anon key precisa ser o JWT (normalmente começa com `eyJ...`), não a publishable key (`sb_publishable...`).
- Para desenvolvimento local com `supabase functions serve`, o projeto também aceita `TARGET_SUPABASE_URL` e `TARGET_SUPABASE_SERVICE_ROLE_KEY`.

### Passo 3: Rodar o frontend localmente
```bash
set -a; source .env; set +a
venv/bin/python main.py   # http://localhost:8000
```
A página chama as Edge Functions publicadas. Depois de alterá-las, publique com `supabase functions deploy sample-ballot` (ou `search`).

### Carregando dados
Os loaders imprimem SQL na saída padrão; aplique com `psql -v ON_ERROR_STOP=1 -1 -f out.sql`. Todos podem ser rodados de novo sem estragar nada. A lista completa está em [docs/architecture.md](docs/architecture.md):
- `scripts/load_district_layers.py` — camadas de fronteiras (precintos de MD, DC, distritos de Fairfax e Loudoun…)
- `scripts/load_va_precincts.py` — precintos do norte da Virginia (GIS do Departamento de Eleições da VA)
- `scripts/load_md_general_2026.py <pasta dos pdfs>` — todas as cédulas de Maryland (lê os 24 PDFs do MSBE; aborta se não baterem com as listas oficiais de candidatos do MSBE)
- `scripts/load_fairfax_general_2026.py`, `scripts/load_va_localities_general_2026.py` — cédulas da Virginia

## Endereços de teste
Conferidos em produção em 2026-10-22. Marque **Include downballot offices** para ver as disputas locais.

| Endereço | O que mostra |
|---|---|
| 104 Ashton Oaks Court, Ashton, MD 20861 | Montgomery: primária de 2026 com resultados + geral (19 disputas, 3 questões com texto FOR/AGAINST) |
| 100 Holliday St, Baltimore, MD 21202 | Baltimore City: 14 disputas, 12 questões (9 bonds e emendas à carta da cidade) |
| 57 N Liberty St, Cumberland, MD 21502 | Allegany: prefeito e conselho da cidade de Cumberland |
| 12 E Church St, Frederick, MD 21701 | Frederick: distrito congressional tirado da lista oficial de candidatos (a cédula não imprime o número) |
| 3430 Court House Dr, Ellicott City, MD 21043 | Howard: questões da carta do condado (mapa de precintos recarregado após a consolidação de 2026) |
| 203 S 4th St, Oakland, MD 21550 | Garrett: precinto cujo código o mapa do estado omite (derivado) |
| 11 N Washington St, Easton, MD 21601 | Talbot: precinto dividido sem fronteira que distinga os estilos — as 3 cédulas possíveis aparecem |
| 1920 Haven Ln, Dunkirk, MD 20754 | Calvert: polígono de precinto extinto — cédula inferida, com nota |
| 777 Lynn St, Herndon, VA 20170 | Fairfax: prefeito e conselho de Herndon, bonds do condado, explicações oficiais |
| 6021 Farrington Ave, Alexandria, VA 22304 | Precinto de Fairfax dividido entre dois distritos congressionais — lado do 8º |
| 6540 Franconia Rd, Springfield, VA 22150 | Mesmo precinto — lado do 11º |
| 7145 Main St, Clifton, VA 20124 | Fairfax: 10º distrito |
| 301 King St, Alexandria, VA 22314 | Alexandria: uma cédula para a cidade inteira |
| 15000 Washington St, Haymarket, VA 20169 | Prince William: disputas da cidade de Haymarket |
| 17739 Main St, Dumfries, VA 22026 | Prince William: disputas da cidade de Dumfries, 7º distrito |
| 8100 Birmingham Dr, Manassas, VA 20111 | Prince William: eleição especial do distrito 20 da Câmara de Delegados |
| 2100 Clarendon Blvd, Arlington, VA 22201 | Arlington: só distritos, com aviso (cédula não carregada) |
| 1350 Pennsylvania Ave NW, Washington, DC 20004 | DC: só distritos, com aviso |
| 20 Meadow Rd, Princeton, NJ 08540 | Fora da área coberta |

Exemplo de API:
```bash
curl -s -X POST "https://<project-ref>.supabase.co/functions/v1/sample-ballot?include_downballot=true" \
  -H "Content-Type: application/json" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -d '{"address":"777 Lynn St, Herndon, VA 20170"}' | head
```

## Testes Automatizados
Testes unitários das Edge Functions (offline, com mocks):
```bash
deno test -A supabase/functions/search supabase/functions/sample-ballot
```
O GitHub Actions roda os testes em todo push/PR; um hook do git roda antes de cada commit.

## Estrutura do Projeto
- `supabase/functions/search`: Edge Function `search` (endereço → geocodificação → RPC PostGIS → distritos).
- `supabase/functions/sample-ballot`: Edge Function `sample-ballot` (distritos → precinto → estilos de cédula → disputas, candidatos, questões; cobertura, alertas de divergência, locais de votação, calendário, fontes dos dados).
- `supabase/migrations/`: esquema do banco.
- `scripts/`: loaders de dados e o parser dos PDFs de cédula do MSBE.
- `static/`: frontend (HTML/JS/CSS, Leaflet.js), servido pelo `main.py`.
- `docs/`: roadmap e decisões, arquitetura, fontes de dados, plano da API pública.
