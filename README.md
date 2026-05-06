# ElectorMap & Downballot Finder (Maryland 2026 Edition)

Este projeto é um MVP para identificação de distritos legislativos, cargos em disputa e calendário eleitoral utilizando geocodificação de endereços e Shapefiles TIGER/Line do Censo dos EUA. Esta versão está configurada especificamente para o ciclo eleitoral de **Maryland 2026**.

## Funcionalidades
- **Geocodificação**: Converte endereços completos ou ZIP+4 em coordenadas usando a API ArcGIS REST.
- **Lógica Espacial (Point-in-Polygon)**: Utiliza GeoPandas para identificar distritos a partir de shapefiles oficiais.
- **Mapa Interativo**: Visualiza a localização do usuário e os limites dos distritos usando Leaflet.js.
- **Calendário Eleitoral**: Exibe datas de Primárias, Votação Antecipada e horários das urnas para Maryland 2026.
- **Cargos na Urna**: Lista automaticamente os cargos em disputa (Governador, Congresso, Senado Estadual, Conselho Escolar, etc.) com base na localização.

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

### Passo 4: Baixar Dados Geográficos (Maryland)
O sistema precisa dos shapefiles do Censo para funcionar. O script abaixo baixará os dados necessários de Maryland (FIPS 24) para a pasta `data/`:
```bash
python3 download_data.py
```

### Passo 5: Iniciar o Servidor
```bash
python3 main.py
```
O servidor estará disponível em: `http://localhost:8000`

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
Para verificar se tudo está funcionando corretamente em Maryland, tente pesquisar este endereço:
- **Endereço**: `100 State Cir, Annapolis, MD 21401`
- **Resultado Esperado**: O mapa deve focar em Annapolis, mostrar o calendário da Primária de Junho de 2026 e listar cargos como "Governor", "State Senator" e "County Executive".

## Estrutura do Projeto
- `main.py`: Servidor FastAPI com lógica de busca espacial.
- `download_data.py`: Script para baixar shapefiles do Censo dos EUA.
- `static/`: Frontend (HTML/JS/CSS) utilizando Leaflet.js.
- `requirements.txt`: Lista de bibliotecas Python necessárias.
