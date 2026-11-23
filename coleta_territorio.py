"""
Território BioCAZ · área plantada, crédito de custeio, revendas e mercado potencial de biológicos por município.

Fontes (todas públicas):
- IBGE · Produção Agrícola Municipal (tabela 5457, API SIDRA): área plantada por município.
- Banco Central · SICOR/MDCR (API OData): crédito de custeio agrícola por município e mês.
- MAPA · SIPEAGRO (dados abertos): revendas (comerciantes) registradas por município.
Mercado potencial ≈ = mercado nacional de biológicos (CropData) × participação do município
na área das culturas-alvo no Brasil. É uma estimativa da ferramenta, não um dado oficial.

Saídas: dados/territorio.json (resumo) e dados/territorio_municipios.csv (todos os municípios).
"""
import csv, io, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta

UA = {"User-Agent": "BioCAZ-inteligencia-de-mercado/1.0 (dados abertos)"}
BRT = timezone(timedelta(hours=-3))
UFS = {"51": "MT", "52": "GO", "31": "MG", "29": "BA", "17": "TO", "21": "MA", "22": "PI"}
CULTURAS = {"40124": "Soja", "40122": "Milho", "40099": "Algodão", "40139": "Café", "40106": "Cana", "40112": "Feijão"}
MERCADO_BIO_RS = 6.2e9          # CropData: mercado de bioinsumos 2025
MERCADO_FONTE = "CropData · 31/03/2026 (R$ 6,2 bi em 2025)"
SICOR = "https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata/CusteioMunicipioProduto"
SIPEAGRO = ("https://dados.agricultura.gov.br/dataset/52a01565-72d6-410e-b21b-64035831a7be/"
            "resource/e0bbc9d5-f161-448b-a6d4-c7beb312ec33/download/sipeagrofertilizante.csv")


def get(url, tent=8):
    for n in range(tent):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read()
        except Exception as e:
            print(f"tentativa {n+1}: {e} · {url[:120]}", file=sys.stderr)
            time.sleep(min(20 * (n + 1), 90))
    raise SystemExit(f"falhou: {url}")


def norm(t):
    t = "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9]", "", t.upper())


# ---------- IBGE · PAM ----------
def pam():
    prods = ",".join(CULTURAS)
    ufs = ",".join(UFS)
    u = f"https://apisidra.ibge.gov.br/values/t/5457/n6/in%20n3%20{ufs}/v/8331/p/last/c782/{prods}?formato=json"
    rows = json.loads(get(u))[1:]
    ano = rows[0]["D3N"]
    mun = {}
    for r in rows:
        cod, nome = r["D1C"], r["D1N"]
        v = r["V"]
        ha = float(v) if re.match(r"^\d+(\.\d+)?$", v) else 0.0
        m = mun.setdefault(cod, {"cod": cod, "nome": nome.rsplit(" - ", 1)[0], "uf": UFS[cod[:2]],
                                 "area": 0.0, **{c: 0.0 for c in CULTURAS.values()}})
        m[CULTURAS[r["D4C"]]] += ha
        m["area"] += ha
    br = json.loads(get(f"https://apisidra.ibge.gov.br/values/t/5457/n1/all/v/8331/p/{ano}/c782/{prods}?formato=json"))[1:]
    area_br = sum(float(r["V"]) for r in br if re.match(r"^\d+(\.\d+)?$", r["V"]))
    return ano, mun, area_br


# ---------- Banco Central · SICOR ----------
# A API não aceita $skip e devolve no máximo 5.000 linhas: dividimos a consulta por estado, mês e,
# quando preciso, por produto, tipo de seguro e programa, até cada parte ficar abaixo do limite.
# Numeração de estados do BCB (ordem alfabética das siglas, conferida em 23/11/2026 pelo município de cada código)
BCB_UF = {"51": "14", "52": "10", "31": "12", "29": "5", "17": "28", "21": "11", "22": "18"}
LIMITE = 5000
DIMS = ["cdProduto", "cdTipoSeguro", "cdPrograma", "cdFonteRecurso", "cdModalidade"]
CAMPOS = "codIbge,nomeProduto,VlCusteio,AreaCusteio," + ",".join(DIMS)


def sicor_consulta(filtro):
    u = f"{SICOR}?$format=json&$select={CAMPOS}&$top={LIMITE}&$filter={urllib.parse.quote(filtro)}"
    return json.loads(get(u))["value"]


def sicor_partes(filtro, nivel=0):
    v = sicor_consulta(filtro)
    if len(v) < LIMITE:
        return v
    if nivel >= len(DIMS):
        raise SystemExit(f"consulta ainda no limite após dividir: {filtro}")
    dim = DIMS[nivel]
    vals = sorted({r[dim] for r in v})
    out = []
    for x in vals:
        out += sicor_partes(f"{filtro} and {dim} eq '{x}'", nivel + 1)
    resto = " and ".join(f"{dim} ne '{x}'" for x in vals)
    out += sicor_partes(f"{filtro} and {resto}", nivel + 1)
    return out


CACHE = os.path.join("dados", "cache_sicor")


def sicor_mes(ano, mes):
    """Linhas do mês já somadas por município e produto. Meses fechados ficam guardados em cache."""
    arq = os.path.join(CACHE, f"{ano}-{mes:02d}.json")
    hoje = datetime.now(BRT)
    fechado = (hoje.year - ano) * 12 + hoje.month - mes >= 3
    if fechado and os.path.exists(arq):
        return [dict(zip(("codIbge", "nomeProduto", "VlCusteio", "AreaCusteio"), r)) for r in json.load(open(arq))]
    base = f"AnoEmissao eq '{ano}' and MesEmissao eq '{mes:02d}' and Atividade eq '1'"
    soma = defaultdict(lambda: [0.0, 0.0])
    for ibge, cb in BCB_UF.items():
        p = sicor_partes(f"{base} and cdEstado eq '{cb}'")
        errados = [r for r in p if not (r.get("codIbge") or "").startswith(ibge)]
        if p and len(errados) > len(p) * 0.02:
            raise SystemExit(f"código de estado do BCB {cb} não corresponde à UF {ibge}")
        for r in p:
            k = (r.get("codIbge") or "", (r.get("nomeProduto") or "").strip('"'))
            soma[k][0] += float(r.get("VlCusteio") or 0)
            soma[k][1] += float(r.get("AreaCusteio") or 0)
    linhas = [[k[0], k[1], round(v[0], 2), round(v[1], 2)] for k, v in sorted(soma.items())]
    if fechado:
        os.makedirs(CACHE, exist_ok=True)
        json.dump(linhas, open(arq, "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"  crédito {mes:02d}/{ano}: {len(linhas)} pares município × produto", flush=True)
    return [dict(zip(("codIbge", "nomeProduto", "VlCusteio", "AreaCusteio"), r)) for r in linhas]


def credito():
    hoje = datetime.now(BRT)
    ano = hoje.year if hoje.month >= 7 else hoje.year - 1     # safra começa em julho
    meses = []
    for mes in range(7, 13):
        u = f"{SICOR}?$format=json&$select=codIbge&$top=1&$filter=" + urllib.parse.quote(
            f"AnoEmissao eq '{ano}' and MesEmissao eq '{mes:02d}' and cdEstado eq '{BCB_UF['51']}'")
        if not json.loads(get(u))["value"]:
            break
        meses.append((mes, sicor_mes(ano, mes)))
    if not meses:
        raise SystemExit("sem dados de crédito na safra corrente")
    atual, anterior = defaultdict(float), defaultdict(float)
    area_cred = defaultdict(float)
    por_cultura = defaultdict(float)
    for mes, dados in meses:
        for r in dados:
            c = (r.get("codIbge") or "")
            if c[:2] in UFS:
                atual[c] += float(r["VlCusteio"] or 0)
                area_cred[c] += float(r.get("AreaCusteio") or 0)
                por_cultura[(UFS[c[:2]], (r.get("nomeProduto") or "").strip('"').capitalize())] += float(r["VlCusteio"] or 0)
        for r in sicor_mes(ano - 1, mes):
            c = (r.get("codIbge") or "")
            if c[:2] in UFS:
                anterior[c] += float(r["VlCusteio"] or 0)
    periodo = f"jul–{['jul','ago','set','out','nov','dez'][len(meses)-1]}"
    return ano, periodo, atual, anterior, area_cred, por_cultura


# ---------- SIPEAGRO · revendas ----------
def revendas():
    t = get(SIPEAGRO).decode("utf-8-sig", "replace")
    vistos, cont = set(), defaultdict(int)
    for r in csv.DictReader(io.StringIO(t), delimiter=";"):
        if r["STATUS_DO_REGISTRO"].strip().lower() != "ativo" or r["ATIVIDADE"].upper() != "COMERCIANTE":
            continue
        k = r["NUMERO_REGISTRO_ESTABELECIMENTO"]
        if k in vistos:
            continue
        vistos.add(k)
        cont[(r["UNIDADE_DA_FEDERACAO"], norm(r["MUNICIPIO"]))] += 1
    return cont


def main():
    ano_pam, mun, area_br = pam()
    print(f"PAM {ano_pam}: {len(mun)} municípios; área Brasil das culturas-alvo {area_br/1e6:.1f} mi ha")
    ano_cr, periodo, cr, cr_ant, area_cr, por_cult = credito()
    print(f"Crédito {periodo}/{ano_cr}: R$ {sum(cr.values())/1e9:.2f} bi nas 7 UFs (ano anterior R$ {sum(cr_ant.values())/1e9:.2f} bi)")
    rev = revendas()
    rs_ha = MERCADO_BIO_RS / area_br

    linhas = []
    for cod, m in mun.items():
        pot = m["area"] * rs_ha
        linhas.append({**m, "potencial": pot, "credito": cr.get(cod, 0.0), "creditoAnterior": cr_ant.get(cod, 0.0),
                       "areaCredito": area_cr.get(cod, 0.0), "revendas": rev.get((m["uf"], norm(m["nome"])), 0)})
    # municípios só com crédito (sem área na PAM) também entram
    for cod in cr.keys() - mun.keys():
        linhas.append({"cod": cod, "nome": "", "uf": UFS[cod[:2]], "area": 0.0, **{c: 0.0 for c in CULTURAS.values()},
                       "potencial": 0.0, "credito": cr[cod], "creditoAnterior": cr_ant.get(cod, 0.0),
                       "areaCredito": area_cr.get(cod, 0.0), "revendas": 0})

    with open("dados/territorio_municipios.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        cols = ["cod", "nome", "uf", "area"] + list(CULTURAS.values()) + ["potencial", "credito", "creditoAnterior", "areaCredito", "revendas"]
        w.writerow(cols)
        for l in sorted(linhas, key=lambda x: -x["potencial"]):
            w.writerow([l[c] if isinstance(l[c], str) else round(l[c], 2) for c in cols])

    por_uf = {}
    for uf in UFS.values():
        L = [l for l in linhas if l["uf"] == uf]
        c, ca = sum(l["credito"] for l in L), sum(l["creditoAnterior"] for l in L)
        top = sorted(L, key=lambda x: -x["potencial"])[:15]
        culturas_cr = sorted([(k[1], v) for k, v in por_cult.items() if k[0] == uf], key=lambda x: -x[1])[:5]
        por_uf[uf] = {
            "area": round(sum(l["area"] for l in L)), "culturas": {c2: round(sum(l[c2] for l in L)) for c2 in CULTURAS.values()},
            "potencial": round(sum(l["potencial"] for l in L)), "credito": round(c), "creditoAnterior": round(ca),
            "variacaoCredito": round((c / ca - 1) * 100, 1) if ca else None,
            "revendas": sum(l["revendas"] for l in L), "municipios": len([l for l in L if l["area"] > 0]),
            "creditoCulturas": [[k, round(v)] for k, v in culturas_cr],
            "top": [[l["nome"], round(l["area"]), round(l["Soja"]), round(l["potencial"]), round(l["credito"]),
                     round((l["credito"] / l["creditoAnterior"] - 1) * 100, 1) if l["creditoAnterior"] else None, l["revendas"]]
                    for l in top],
        }
    agora = datetime.now(BRT)
    out = {
        "lidoEm": agora.strftime("%d/%m/%Y %Hh%M"), "lidoIso": agora.isoformat(timespec="seconds"),
        "pam": {"ano": ano_pam, "culturas": list(CULTURAS.values()), "areaBrasil": round(area_br),
                "fonte": f"IBGE · Produção Agrícola Municipal {ano_pam} (tabela 5457)"},
        "credito": {"safra": f"{ano_cr}/{str(ano_cr+1)[2:]}", "periodo": periodo, "anoAnterior": ano_cr - 1,
                    "fonte": "Banco Central · SICOR/MDCR, custeio agrícola por município (API pública)"},
        "potencial": {"rsPorHa": round(rs_ha, 2), "mercado": MERCADO_BIO_RS, "fonte": MERCADO_FONTE,
                      "metodo": "Mercado nacional de biológicos dividido pela área das culturas-alvo no Brasil (soja, milho, algodão, café, cana e feijão) e aplicado à área de cada município. Estimativa da ferramenta."},
        "revendas": {"fonte": "MAPA · SIPEAGRO, comerciantes com registro ativo"},
        "colunasTop": ["município", "área (ha)", "soja (ha)", "potencial ≈ (R$)", "crédito (R$)", "variação do crédito (%)", "revendas"],
        "uf": por_uf,
    }
    with open("dados/territorio.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for uf, d in por_uf.items():
        print(uf, d["area"], d["potencial"], d["credito"], d["variacaoCredito"], d["revendas"])


if __name__ == "__main__":
    main()
