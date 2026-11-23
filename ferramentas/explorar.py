"""Inspeção das bases da Etapa 2 (uso manual pelo Actions)."""
import json, re, urllib.request, urllib.parse
UA = {"User-Agent": "BioCAZ-inteligencia-de-mercado/1.0 (dados abertos)"}
def get(url, n=1500, data=None, ct=None):
    try:
        h = dict(UA)
        if ct: h["Content-Type"] = ct
        r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=180)
        b = r.read()
        print(f"\n### OK {r.status} {len(b)} bytes · {url}\n{b[:n].decode('utf-8','replace')}")
        return b
    except Exception as e:
        print(f"\n### ERRO {url}\n{e}")
S = "https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata/"
get(S + "CusteioMunicipioProduto?$top=3&$format=json", 2500)
get(S + "CusteioMunicipioProduto?$top=5&$format=json&$filter=" + urllib.parse.quote("AnoEmissao eq '2026' and nomeUF eq 'MT'"), 2500)
get(S + "$metadata", 6000)
# Comex Stat: importação NCM capítulo 31 por UF, 2026
q = {"flow": "import", "monthDetail": False, "period": {"from": "2026-01", "to": "2026-10"},
     "filters": [{"filter": "chapter", "values": ["31"]}], "details": ["state"], "metrics": ["metricFOB", "metricKG"]}
get("https://api-comexstat.mdic.gov.br/general?language=pt", 2500, json.dumps(q).encode(), "application/json")
# Conab: página de downloads do portal
b = get("https://portaldeinformacoes.conab.gov.br/download-arquivos.html", 200)
if b:
    for h in sorted(set(re.findall(r'href="([^"]+\.(?:txt|csv|xlsx|zip))"', b.decode("utf-8", "replace"))))[:60]:
        print("  ", h)
for nome in ["SerieHistoricaGraos.txt", "ProgressoSafra.txt", "LevantamentoGraos.txt", "PrecosSemanalUF.txt"]:
    get("https://portaldeinformacoes.conab.gov.br/downloads/arquivos/" + nome, 400)
