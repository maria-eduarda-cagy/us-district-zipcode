# Plano: uma API pública de distritos e cédulas

Situação: **ideia para o futuro, não iniciada** (escrito em 2026-10-20). Vem depois de completar a DMV; veja [roadmap.pt-BR.md](roadmap.pt-BR.md). English version: [public-api-plan.md](public-api-plan.md).

## Ideia

Oferecer o que o app já calcula (endereço → distritos → cédula, locais de votação, calendário) como uma API para outras pessoas construírem em cima.

## O que já existe

As duas Edge Functions do Supabase já são, na prática, uma API privada:

- `search`: endereço → geocodificação → todos os distritos que contêm o ponto
- `sample-ballot`: o mesmo, mais a cédula (disputas, candidatos, questões, explicações oficiais), locais de votação próximos, calendário eleitoral, nível de cobertura e atualidade dos dados (`data_sources`, `data_last_updated`)

Então o trabalho é menos "construir uma API" e mais "operar uma".

## O que falta para uma API pública

- **Chave de acesso por cliente, limite de requisições e registro de uso.** Hoje qualquer um com a chave anon chama as functions, e cada chamada consome uma geocodificação (Censo, com ArcGIS de reserva).
- **Contrato estável e versionado** (`/v1/...`): mudar um campo não pode quebrar quem consome. O formato atual da resposta cresceu de forma orgânica e precisa de revisão antes de ser congelado.
- **Documentação** (OpenAPI), com declaração explícita de cobertura e aviso sobre precisão: dado eleitoral errado tem consequência real.
- **Cache:** distritos e cédulas mudam pouco; a maioria das respostas pode ficar em cache por horas (por ponto geocodificado ou por precinto).

## Manter os dados atualizados

É a parte difícil. O esforço depende do tipo de dado:

| Dado | Com que frequência muda | Manutenção |
|---|---|---|
| Distritos (congressional, legislativo, condado) | A cada redistritamento (10 anos, mais exceções como a tentativa da Virginia em 2026, anulada na Justiça) | Baixa: o Censo publica o TIGER para os EUA inteiros todo ano |
| Precintos | Antes de eleições, por condado | Média: cada condado publica do seu jeito (veja as lacunas de Garrett, Kent e Howard em MD) |
| Cédulas, candidatos | A cada eleição; candidatos mudam até a certificação | Alta: um formato por estado ou condado |
| Resultados, locais de votação, prazos | A cada eleição | Média |

O que torna isso sustentável é o padrão que os loaders já seguem: **buscar a fonte oficial direto, poder rodar de novo sem estragar nada e abortar se a validação falhar** (por exemplo, o loader da geral de MD confere cada cédula contra a lista oficial de candidatos do MSBE). Próximo passo: agendar os loaders (diariamente perto das eleições, semanalmente fora delas) e alertar quando uma validação falhar. Assim, "atualizar constantemente" vira "investigar alertas".

## Escopo: EUA ou DMV

- **Distritos para os EUA inteiros:** viável e barato de manter (TIGER). Pode ser uma camada nacional separada da API.
- **Cédulas para os EUA inteiros:** são mais de 3.000 condados, cada um com seu formato. Parsers feitos à mão (como o de MD) não escalam para uma pessoa. Quem cobre o país faz isso com equipes dedicadas ou com arquivos padronizados dos estados: o Voting Information Project (os estados publicam arquivos padronizados) e empresas que licenciam os dados (BallotReady, Ballotpedia). Um caminho nacional realista é combinar uma dessas fontes com os nossos dados de fontes oficiais onde quisermos mais precisão. Verificar a licença antes de redistribuir dados de terceiros.

## Abordagem recomendada (quando chegarmos lá)

1. Lançar com o que está verificado: DC, MD e VA, com cédulas validadas contra fontes oficiais.
2. Adicionar distritos nacionais (TIGER) como uma camada separada e de baixa manutenção.
3. Expandir as cédulas estado por estado, começando pelos que publicam dados estruturados.
4. Antes do lançamento: chaves de API e limite de requisições, revisão do contrato `/v1`, documentação OpenAPI, cache das respostas, loaders agendados com alertas.
