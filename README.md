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

## SIPEAGRO (semanal)
`coleta_sipeagro.py`, pela tarefa `.github/workflows/sipeagro.yml` (segunda, 06h37), lê os estabelecimentos da área de fertilizantes, inoculantes e corretivos nos dados abertos do MAPA e grava `dados/sipeagro_bio.json`: fábricas e importadores de inoculante e biofertilizante por UF e empresa, e revendas (comerciantes) por UF e município.

## Movimentos do Agrofit
A cada coleta diária, `coleta_agrofit.py` compara a lista de biológicos com a do dia anterior e acrescenta em `dados/agrofit_movimentos.csv` os produtos que entraram ou saíram do cadastro.

## Território e importação (dias 8 e 22, 07h53)

- `coleta_comex.py` → `dados/comex_fertilizantes.json`: importação de adubos e fertilizantes (capítulo 31 da NCM) pela API do Comex Stat, total do ano, comparação com o ano anterior, estados de destino e série mensal.
- `coleta_territorio.py` → `dados/territorio.json` e `dados/territorio_municipios.csv`: para os municípios de MT, GO, MG, BA, TO, MA e PI, área plantada das culturas-alvo (IBGE, PAM), crédito de custeio agrícola da safra corrente e do mesmo período do ano anterior (Banco Central, SICOR), revendas com registro ativo (SIPEAGRO) e mercado potencial estimado de biológicos.
- A API do Banco Central só aceita até 5.000 linhas por consulta e não pagina; a coleta divide as consultas por estado, mês e produto. Meses fechados ficam em `dados/cache_sicor/` para não serem consultados de novo. Uma coleta completa leva cerca de uma hora.
- Para coletar só a importação, rode a tarefa manualmente marcando "Coletar só a importação de fertilizantes".
