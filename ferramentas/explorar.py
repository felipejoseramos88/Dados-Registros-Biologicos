"""Inspeção das bases da Etapa 2 (uso manual pelo Actions)."""
import json, re, urllib.request, urllib.parse, io, csv
from collections import Counter
UA = {"User-Agent": "BioCAZ-inteligencia-de-mercado/1.0 (dados abertos)"}
def get(url, n=1500, show=True):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300)
        b = r.read()
        if show: print(f"\n### OK {r.status} {len(b)} bytes · {url}\n{b[:n].decode('utf-8','replace')}")
        return b
    except Exception as e:
        print(f"\n### ERRO {url}\n{e}"); return None
S = "https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata/"
md = get(S + "$metadata", 0, False).decode()
m = re.search(r'<EntityType Name="TipoCusteioMunicipioProduto">(.*?)</EntityType>', md)
print("CAMPOS CusteioMunicipioProduto:", re.findall(r'Name="(\w+)"', m.group(1)) if m else "?")
fs = re.findall(r'<FunctionImport Name="(\w+)"[^>]*>', md); print("FUNCOES:", fs[:30])
print(re.findall(r'<EntitySet Name="CusteioMunicipioProduto"[^>]*>', md))
for f in ["AnoEmissao eq '2026' and cdEstado eq '51'", "AnoEmissao eq '2026'"]:
    get(S + "CusteioMunicipioProduto?$format=json&$top=3&$filter=" + urllib.parse.quote(f), 1500)
# Conab preços: produtos com 'fertiliz' ou fórmulas
b = get("https://portaldeinformacoes.conab.gov.br/downloads/arquivos/PrecosSemanalUF.txt", 0, False)
t = b.decode("latin-1")
rows = list(csv.reader(io.StringIO(t), delimiter=";"))
print("PRECOS cabeçalho:", rows[0], len(rows))
c = Counter((r[0].strip(), r[1].strip()) for r in rows[1:] if r and r[5].strip() >= "2026")
print("PRODUTOS 2026:", c.most_common(120))
print("NIVEIS:", Counter(r[9].strip() for r in rows[1:]).most_common())
# Conab levantamento: últimos levantamentos
b = get("https://portaldeinformacoes.conab.gov.br/downloads/arquivos/LevantamentoGraos.txt", 0, False)
t = b.decode("latin-1"); rows = list(csv.reader(io.StringIO(t), delimiter=";"))
print("LEV cab:", rows[0])
print("LEV safras/levs:", sorted(Counter((r[0].strip(), r[5].strip(), r[6].strip()) for r in rows[1:] if r[0].strip() >= "2025/26").items())[-12:])
print("LEV produtos:", Counter(r[3].strip() for r in rows[1:] if r[0].strip() == "2026/27").most_common(30))
print("LEV safra campo:", Counter(r[1].strip() for r in rows[1:] if r[0].strip() == "2026/27").most_common())
