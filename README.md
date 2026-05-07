# ElectorMap & Downballot Finder (DMV + 2026 cycle)

Este projeto é um MVP para identificar distritos legislativos (DC/MD/VA), gerar um “sample ballot” (somente cargos, sem candidatos) e exibir calendário eleitoral (quando disponível), usando geocodificação de endereços + camadas geográficas (TIGER/Line + fontes autoritativas locais).

## Funcionalidades
- **Geocodificação hierárquica**: Converte endereço em coordenadas e normaliza o endereço (priorizando fontes locais quando aplicável, com fallback).
- **Lógica espacial (point-in-polygon)**: Identifica distritos a partir das camadas carregadas via GeoPandas/Shapely.
- **Mapa interativo**: Visualiza a localização e limites dos distritos via Leaflet.js.
- **Sample Ballot (Offices Only)**: Gera uma lista de cargos por distrito e at-large; suporta “downballot” opcional.
- **Calendário eleitoral**: Mostra o calendário do ciclo 2026 (atualmente Maryland).

## Requisitos Prévios
- Python 3.9 ou superior.
- [Opcional] Docker e Docker Compose.

## Guia de Instalação e Execução

### Passo 1: Clonar o Repositório
```bash
git clone <url-do-repositorio>
cd us-district-zipcode
```

### Passo 2: Configurar o Ambiente Virtual
É altamente recomendado o uso de um ambiente virtual para gerenciar as dependências:

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

### Passo 3: Instalar Dependências
```bash
pip install -r requirements.txt
```

### Passo 4: Baixar Dados Geográficos (DMV)
O sistema usa dados TIGER/Line (Censo) e, quando disponíveis, camadas autoritativas locais (DC/MD/VA). Você pode baixar tudo manualmente:
```bash
python3 download_data.py
```

### Passo 5: Iniciar o Servidor
```bash
python3 main.py
```
O servidor estará disponível em: `http://127.0.0.1:8000`

Observações:
- No startup, o servidor pode disparar um refresh automático de dados se estiver faltando algo em `data/` ou se a última atualização estiver “velha” (padrão: 24h). Isso é controlado por:
  - `DATA_REFRESH_INTERVAL_HOURS` (padrão: `24`)
  - `FORCE_DATA_REFRESH=1` (força re-download)
- Se a porta 8000 estiver em uso, finalize o processo antigo antes de iniciar um novo.

---

## Executando com Docker (Alternativa)
Se você prefere usar Docker para evitar configurar o Python localmente:

1. **Build e Execução**:
   ```bash
   docker-compose up --build
   ```

2. **Acesse**: `http://localhost:8000`
   *(O Docker já está configurado para baixar os dados necessários durante o build ou inicialização)*.

---

## Validação de Teste
Para verificar rapidamente:
- Abra `http://127.0.0.1:8000/` e busque um endereço em MD/DC/VA (o input já vem com um exemplo em MD).
- Na seção **Sample Ballot (Offices Only)**:
  - Com o checkbox “Include downballot offices” desligado: aparece o top-of-ticket (ex.: U.S. Representative, State Senator, statewide MD).
  - Com o checkbox ligado: aparecem também downballots (ex.: county, school, delegate subdistrict, quando aplicável).

Testes por API (exemplo):
```bash
curl -s -X POST "http://127.0.0.1:8000/api/sample-ballot?include_downballot=false" \
  -H "Content-Type: application/json" \
  -d '{"address":"104 Ashton Oaks Court, Ashton, Maryland 20861"}'
```

## Estrutura do Projeto
- `main.py`: Servidor FastAPI com lógica de busca espacial.
- `download_data.py`: Script para baixar TIGER/Line + camadas autoritativas (quando disponíveis) para `data/`.
- `static/`: Frontend (HTML/JS/CSS) utilizando Leaflet.js.
- `requirements.txt`: Lista de bibliotecas Python necessárias.
