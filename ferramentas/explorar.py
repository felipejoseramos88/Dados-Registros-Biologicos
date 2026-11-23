import json, urllib.request, urllib.parse, time
UA = {"User-Agent": "BioCAZ-inteligencia-de-mercado/1.0 (dados abertos)"}
S = "https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata/CusteioMunicipioProduto"
def t(q):
    u = S + "?" + q
    t0 = time.time()
    try:
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=300).read()
        v = json.loads(b)["value"]
        print(f"OK {len(v)} linhas {time.time()-t0:.0f}s · {q[:160]}")
        if v: print("   ", v[0])
    except Exception as e:
        print(f"ERRO {e} {time.time()-t0:.0f}s · {q[:160]}")
f = lambda s: "$filter=" + urllib.parse.quote(s)
t("$format=json&$top=3&" + f("AnoEmissao eq '2026' and MesEmissao eq '07'"))
t("$format=json&$top=3&" + f("AnoEmissao eq '2026' and MesEmissao eq '07' and Atividade eq '1'"))
t("$format=json&$top=3&$select=codIbge,VlCusteio&" + f("AnoEmissao eq '2026' and MesEmissao eq '07'"))
t("$format=json&$top=5000&" + f("AnoEmissao eq '2026' and MesEmissao eq '07'"))
t("$format=json&$top=5000&$skip=5000&" + f("AnoEmissao eq '2026' and MesEmissao eq '07'"))
t("$format=json&$top=3&" + f("AnoEmissao eq '2026' and MesEmissao eq '07' and startswith(codIbge,'51')"))
t("$format=json&$top=3&" + f("AnoEmissao eq '2026' and MesEmissao eq '07' and cdEstado eq '12'"))
t("$format=json&$top=3&$orderby=codIbge&" + f("AnoEmissao eq '2026' and MesEmissao eq '07'"))
t("$format=json&$top=3&" + f("AnoEmissao eq '2026' and MesEmissao eq '11'"))
t("$format=json&$top=3&" + f("AnoEmissao eq '2026' and MesEmissao eq '10'"))
