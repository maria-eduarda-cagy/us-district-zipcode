# Use uma imagem Python leve
FROM python:3.11-slim

# Instala dependências do sistema necessárias para GeoPandas e Fiona
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do projeto
COPY . .

# Expõe a porta que o FastAPI usará
EXPOSE 8000

# Comando para rodar a aplicação
# Nota: No Docker, usamos 0.0.0.0 para que seja acessível fora do container
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
