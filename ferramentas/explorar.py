"""Inspeção das fontes (uso manual pelo Actions). Imprime links, colunas e amostras."""
import csv, io, re, sys, urllib.request, html
from collections import Counter
UA = {"User-Agent": "Mozilla/5.0 (BioCAZ-inteligencia-de-mercado)"}

def get(url, limit=None):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300)
    return r.read(limit) if limit else r.read()

def links(url, filtro):
    try:
        t = get(url).decode("utf-8", "replace")
    except Exception as e:
        print("ERRO", url, e); return []
    out = []
    for h, txt in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', t, re.S):
        txt = re.sub(r"<[^>]+>", " ", html.unescape(txt)).strip()
        if re.search(filtro, h + " " + txt, re.I):
            out.append((txt[:90], h))
    print(f"\n### {url}\n{len(out)} links")
    for x in out[:80]:
        print("  ", x)
    return out

def amostra_csv(url, nome):
    b = get(url)
    for enc in ("utf-8-sig", "cp1252"):
        try: t = b.decode(enc); break
        except UnicodeDecodeError: pass
    d = ";" if t[:5000].count(";") > t[:5000].count(",") else ","
    rows = list(csv.reader(io.StringIO(t), delimiter=d))
    print(f"\n### {nome}: {len(b)/1e6:.1f} MB, {len(rows)} linhas, delim {d!r}, enc {enc}")
    print("COLUNAS:", rows[0])
    for r in rows[1:4]: print("  ", r)
    for i, c in enumerate(rows[0]):
        vals = Counter(r[i] for r in rows[1:] if len(r) > i)
        if 1 < len(vals) <= 60:
            print(f"  [{c}] {vals.most_common(25)}")
    return rows

# 1. Planilha de registros do MAPA
L = links("https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-agricolas/agrotoxicos/informacoes-tecnicas", r"registros?concedidos|\.xlsx")
for txt, h in L:
    if "RegistrosConcedidos" in h:
        import openpyxl
        b = get(h if h.startswith("http") else "https://www.gov.br" + h)
        wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
        print("\nABAS:", wb.sheetnames)
        for ws in wb.worksheets[:3]:
            print(f"\n--- {ws.title} ---")
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i > 12: break
                print("  ", [c for c in row if c is not None][:14])
        ws = wb.worksheets[2]
        print(f"\n--- {ws.title} (final) ---")
        rows = list(ws.iter_rows(values_only=True))
        for row in rows[-12:]:
            print("  ", [c for c in row if c is not None][:14])
        break

# 2. SIPEAGRO
rows = amostra_csv("https://dados.agricultura.gov.br/dataset/52a01565-72d6-410e-b21b-64035831a7be/resource/e0bbc9d5-f161-448b-a6d4-c7beb312ec33/download/sipeagrofertilizante.csv", "SIPEAGRO fertilizantes")
bio = [r for r in rows[1:] if re.search(r"inocul|biofert|bradyrhiz|azospir|rhizob", " ".join(r), re.I)]
print(f"\nLinhas com inoculante/biofertilizante: {len(bio)}")
for r in bio[:8]: print("  ", r)

# 3. Ibama
for u in ["https://www.gov.br/ibama/pt-br/assuntos/quimicos-e-biologicos/agrotoxicos/relatorios-de-comercializacao-de-agrotoxicos",
          "https://www.gov.br/ibama/pt-br/assuntos/quimicos-e-biologicos/agrotoxicos/relatorios-de-comercializacao-de-agrotoxicos/boletins-anuais-de-producao-importacao-exportacao-e-vendas-de-agrotoxicos-no-brasil",
          "https://www.gov.br/ibama/pt-br/assuntos/quimicos-e-biologicos/agrotoxicos/relatorios-de-comercializacao-de-agrotoxicos/relatorios-de-comercializacao-de-agrotoxicos"]:
    links(u, r"biol|boletim|xls|vendas|comercializa|painel")
