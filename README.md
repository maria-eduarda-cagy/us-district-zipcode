# ElectorMap & Downballot Finder (DMV + 2026 cycle)

Este projeto é um MVP para identificar distritos legislativos (DC/MD/VA), gerar um “sample ballot” (somente cargos, sem candidatos) e exibir calendário eleitoral (quando disponível), usando geocodificação de endereços + camadas geográficas (TIGER/Line + fontes autoritativas locais).

## Funcionalidades
- **Geocodificação hierárquica**: Converte endereço em coordenadas e normaliza o endereço (priorizando fontes locais quando aplicável, com fallback).
- **Lógica espacial (point-in-polygon)**: Identifica distritos via PostGIS (Supabase) com camadas TIGER/Line carregadas no banco.
- **Mapa interativo**: Visualiza a localização e limites dos distritos via Leaflet.js.
- **Sample Ballot (Offices Only)**: Gera uma lista de cargos por distrito e at-large; suporta “downballot” opcional.
- **Calendário eleitoral**: Mostra o calendário do ciclo 2026 (atualmente Maryland).

## Requisitos Prévios
- Supabase (Postgres + PostGIS) com as Edge Functions `search` e `sample-ballot` publicadas.
- Deno (para rodar os testes localmente).
- [Opcional] Python 3.9+ (apenas para rodar o servidor legado local e/ou scripts auxiliares).

## Guia de Instalação e Execução

### Passo 1: Clonar o Repositório
```bash
git clone <url-do-repositorio>
cd us-district-zipcode
```

### Passo 2: Configurar variáveis de ambiente (para testes locais e chamadas via curl)
Crie um arquivo `.env` (não commitar) contendo ao menos:
```bash
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-jwt-que-comeca-com-eyJ...>
```

Observações:
- A anon key usada aqui deve ser o JWT (geralmente começa com `eyJ...`). Não use a publishable key (`sb_publishable...`).
- Para desenvolvimento local com `supabase functions serve`, este projeto também suporta:
  - `TARGET_SUPABASE_URL`
  - `TARGET_SUPABASE_SERVICE_ROLE_KEY`

---

## Validação de Teste
Para verificar rapidamente:
- Abra o frontend e busque um endereço em MD/DC/VA (o input já vem com um exemplo em MD).
- Na seção **Sample Ballot (Offices Only)**:
  - Com o checkbox “Include downballot offices” desligado: aparece o top-of-ticket (ex.: U.S. Representative, State Senator, statewide MD).
  - Com o checkbox ligado: aparecem também downballots (ex.: county, school, delegate subdistrict, quando aplicável).

Testes por API (produção, exemplo):
```bash
curl -s -X POST "https://<project-ref>.supabase.co/functions/v1/search" \
  -H "Content-Type: application/json" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -d '{"address":"104 Ashton Oaks Court, Ashton, Maryland 20861"}' | head

curl -s -X POST "https://<project-ref>.supabase.co/functions/v1/sample-ballot?include_downballot=true" \
  -H "Content-Type: application/json" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -d '{"address":"104 Ashton Oaks Court, Ashton, Maryland 20861"}' | head
```

## Testes automatizados
Este repositório inclui testes unitários das Edge Functions (sem rede, usando mocks).

Rodar localmente:
```bash
deno test -A supabase/functions/search supabase/functions/sample-ballot
```

CI:
- O GitHub Actions executa os testes automaticamente em push/PR.

## Estrutura do Projeto
- `supabase/functions/search`: Edge Function `search` (address → geocode → PostGIS RPC → memberships).
- `supabase/functions/sample-ballot`: Edge Function `sample-ballot` (gera contests/offices a partir das memberships).
- `supabase/config.toml`: Config das Edge Functions (inclui `verify_jwt`).
- `main.py`: Servidor FastAPI legado (útil para desenvolvimento antigo/local; não é necessário para o caminho Supabase).
- `download_data.py`: Script auxiliar para baixar dados locais (quando aplicável).
- `static/`: Frontend (HTML/JS/CSS) utilizando Leaflet.js.
- `requirements.txt`: Lista de bibliotecas Python necessárias.
