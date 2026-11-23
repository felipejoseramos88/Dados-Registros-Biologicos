import json, urllib.request, urllib.parse, time
UA = {"User-Agent": "BioCAZ-inteligencia-de-mercado/1.0 (dados abertos)"}
S = "https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata/CusteioMunicipioProduto"
def t(q, show=True):
    u = S + "?" + q
    t0 = time.time()
    try:
        v = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=300).read())["value"]
        print(f"OK {len(v)} linhas {time.time()-t0:.0f}s · {urllib.parse.unquote(q)[:170]}", flush=True)
        if v and show: print("   ", v[0], flush=True)
        return v
    except Exception as e:
        print(f"ERRO {e} {time.time()-t0:.0f}s · {urllib.parse.unquote(q)[:170]}", flush=True)
f = lambda s: "$filter=" + urllib.parse.quote(s)
B = "AnoEmissao eq '2026' and MesEmissao eq '07'"
for cb in range(1, 29):
    t(f"$format=json&$top=1&" + f(f"{B} and cdEstado eq '{cb}'"))
t("$format=json&$top=5000&$select=codIbge,nomeProduto,VlCusteio,AreaCusteio,cdProduto&" + f(f"{B} and Atividade eq '1' and cdEstado eq '12'"), False)
t("$format=json&$top=5000&$select=codIbge,VlCusteio&" + f(f"{B} and cdEstado eq '12' and cdProduto ne '1'"), False)
