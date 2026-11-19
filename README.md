# API Agrofit · BioCAZ

Coleta diária dos produtos biológicos registrados no Agrofit, para a aba Registros da plataforma de Inteligência de Mercado BioCAZ.

## Fonte
Arquivo oficial de produtos formulados do Agrofit, nos dados abertos do MAPA (licença CC-BY, atualização diária):
https://dados.agricultura.gov.br/dataset/sistema-de-agrotoxicos-fitossanitarios-agrofit

O script lê só esse arquivo público. Não acessa o site de consulta do Agrofit.

## O que gera
- `dados/agrofit_bio.json`: resumo (total de produtos formulados, biológicos, grupos de agente, classes, agentes, titulares, culturas, data do arquivo e da leitura).
- `dados/agrofit_bio_produtos.json`: lista dos produtos biológicos (registro, marca, ingrediente ativo, titular, grupo, nº de culturas e pragas).

## Como roda
A tarefa `.github/workflows/agrofit.yml` roda todo dia às 06h17 (Brasília), antes da coleta da plataforma (07h44), e grava os dois arquivos no repositório. Também pode ser disparada à mão em Actions › Coleta Agrofit › Run workflow.

## Teste local
    python coleta_agrofit.py --arquivo teste/amostra.csv --saida /tmp/agrofit_bio.json

## Critério de biológico
Se o arquivo tiver uma coluna que marque o produto como biológico, ela é usada. Se não tiver, o produto entra quando o ingrediente ativo traz um agente biológico conhecido (fungos, bactérias, vírus, macrobiológicos, semioquímicos, extratos) ou a classe indica microbiológico, biológico ou feromônio. O resumo informa qual critério foi usado.
