"""Inspeção das bases da Etapa 2 (uso manual pelo Actions)."""
import json, urllib.request, urllib.parse
UA = {"User-Agent": "BioCAZ-inteligencia-de-mercado/1.0 (dados abertos)"}
def get(url, n=1500):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)
        b = r.read()
        print(f"\n### OK {r.status} {len(b)} bytes · {url}\n{b[:n].decode('utf-8','replace')}")
        return b
    except Exception as e:
        print(f"\n### ERRO {url}\n{e}")
# IBGE: metadados da PAM (5457) e LSPA (6588)
b = get("https://servicodados.ibge.gov.br/api/v3/agregados/5457/metadados", 300)
if b:
    m = json.loads(b)
    print("variaveis:", [(v["id"], v["nome"]) for v in m["variaveis"]])
    for c in m["classificacoes"]:
        cats = [(x["id"], x["nome"]) for x in c["categorias"] if any(k in x["nome"].lower() for k in ["soja", "milho", "algod", "café", "cana", "feijão", "sorgo", "trigo"])]
        print("classif", c["id"], c["nome"], cats)
    print("periodo", m["periodicidade"])
get("https://apisidra.ibge.gov.br/values/t/5457/n3/51/v/8331/p/last/c782/40124?formato=json", 800)
get("https://servicodados.ibge.gov.br/api/v3/agregados/6588/metadados", 600)
# Banco Central: SICOR OData (MDCR)
get("https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata/", 3000)
# Comex Stat
get("https://api-comexstat.mdic.gov.br/general/dates/updated", 500)
# Conab
get("https://www.conab.gov.br/info-agro/safras/progresso-de-safra", 300)
get("https://portaldeinformacoes.conab.gov.br/", 300)
