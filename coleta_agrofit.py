"""
API Agrofit · BioCAZ
Baixa o arquivo oficial de produtos formulados do Agrofit (dados abertos do MAPA),
separa os produtos biológicos e grava um resumo em dados/agrofit_bio.json.

Fonte: https://dados.agricultura.gov.br/dataset/sistema-de-agrotoxicos-fitossanitarios-agrofit
O arquivo traz uma linha por produto × cultura × praga; o script agrupa por registro.

Uso:
  python coleta_agrofit.py                 # baixa da fonte oficial
  python coleta_agrofit.py --arquivo x.csv # usa um arquivo local (teste)
"""
import argparse
import csv
import io
import json
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

PACOTE = "https://dados.agricultura.gov.br/api/3/action/package_show?id=6c913699-e82e-4da3-a0a1-fb6c431e367f"
URL_PADRAO = ("https://dados.agricultura.gov.br/dataset/6c913699-e82e-4da3-a0a1-fb6c431e367f/"
              "resource/d30b30d7-e256-484e-9ab8-cd40974e1238/download/agrofitprodutosformulados.csv")
BRT = timezone(timedelta(hours=-3))
UA = {"User-Agent": "BioCAZ-inteligencia-de-mercado/1.0 (dados abertos)"}

# Agentes biológicos: usados quando o arquivo não traz uma coluna que marque o produto como biológico.
GRUPOS = [
    ("Fungos entomopatogênicos e nematófagos",
     r"beauveria|metarhizium|cordyceps|isaria|lecanicillium|paecilomyces|purpureocillium|pochonia|hirsutella|arthrobotrys"),
    ("Trichoderma", r"trichoderma"),
    ("Bactérias (Bacillus e outras)",
     r"bacillus|pseudomonas|streptomyces|burkholderia|chromobacterium|serratia|pasteuria|lysinibacillus|paenibacillus|bradyrhizobium|azospirillum"),
    ("Outros fungos", r"clonostachys|gliocladium|aspergillus|saccharomyces|ampelomyces|coniothyrium"),
    ("Vírus", r"baculov|nucleopoliedrov|granulov|v[ií]rus|npv"),
    ("Macrobiológicos",
     r"cotesia|trichogramma|telenomus|neoseiulus|phytoseiulus|amblyseius|orius|chrysoperla|stratiolaelaps|steinernema|heterorhabditis|tamarixia|cleruchoides|ageniaspis|diachasmimorpha"),
    ("Semioquímicos", r"ferom[oô]n|tetradecen|hexadecen|dodecen|octadecen|grandlure|cuelure|trimedlure|eugenol metil|semioqu"),
    ("Extratos e bioquímicos",
     r"extrato|azadiract|[oó]leo de|melaleuca|quillaja|saponina|terpeno|harpina|laminarin|quitosana|citrico|alho|canela"),
]
PADRAO_BIO = re.compile("|".join(p for _, p in GRUPOS), re.I)
CLASSE_BIO = re.compile(r"microbiol|biol[oó]gic|macrobiol|ferom[oô]n|semioqu", re.I)


def sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")


def limpo(t):
    return re.sub(r"\s+", " ", (t or "").replace("\x96", "–").replace("\x97", "—")).strip()


def empresa_curta(t):
    t = re.split(r"\s+[-–]\s+", limpo(t))[0]
    t = re.sub(r"\b(ltda|s\.?/?a\.?|eireli|me|epp)\b\.?", "", t, flags=re.I)
    t = re.sub(r"\b(ind[uú]stria|com[eé]rcio|e|de|do|da|distribui[cç][aã]o|importa[cç][aã]o|exporta[cç][aã]o)\b", " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" .,-")
    return " ".join(t.split()[:2])


def chave(nome):
    return re.sub(r"[^A-Z0-9]+", "_", sem_acento(nome).upper()).strip("_")


def baixar(url, tentativas=3):
    """Baixa o arquivo e confere se veio inteiro (tamanho declarado e última linha completa)."""
    import time
    erro = None
    for n in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=600) as r:
                esperado = r.headers.get("Content-Length")
                dados = r.read()
            if esperado and len(dados) != int(esperado):
                raise IOError(f"download incompleto: {len(dados)} de {esperado} bytes")
            if url.endswith(".csv") and not dados.rstrip(b" ").endswith((b"\n", b"\r")):
                raise IOError("download incompleto: última linha cortada")
            return dados
        except Exception as e:
            erro = e
            print(f"tentativa {n}: {e}", file=sys.stderr)
            time.sleep(20 * n)
    raise SystemExit(f"não consegui baixar o arquivo inteiro: {erro}")


def info_pacote():
    try:
        d = json.loads(baixar(PACOTE))["result"]
        for r in d["resources"]:
            if "formulado" in r["name"].lower():
                return r["url"], r.get("last_modified")
    except Exception as e:  # a falha aqui não impede a coleta
        print(f"aviso: não li os metadados do pacote ({e}); uso o link padrão", file=sys.stderr)
    return URL_PADRAO, None


def decodificar(b):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return b.decode("latin-1", errors="replace"), "latin-1"


def ler_csv(texto):
    amostra = texto[:20000]
    delim = ";" if amostra.count(";") > amostra.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delim)
    leitor.fieldnames = [chave(c) for c in leitor.fieldnames]
    return leitor, delim


def achar(campos, *opcoes):
    """Primeira coluna cujo nome contém uma das opções (já normalizadas)."""
    for op in opcoes:
        for c in campos:
            if op in c:
                return c
    return None


MARCA_MACRO = re.compile(r"[aá]caros vivos|nemat[oó]ides entomopatog|indiv[ií]duos|insetos vivos|parasit[oó]ide|pupa", re.I)
MARCA_SEMIO = re.compile(r"\((acetato|alde[ií]do|[aá]lcool|cetona|hidrocarboneto|[eé]ter|cetal|amida|[eé]steres)[^)]*\)", re.I)
BACT_EXTRA = re.compile(r"priestia|rhizobium|azotobacter|agrobacterium|xanthomonas|ensifer|enterobacter", re.I)


def grupo_de(texto):
    if MARCA_MACRO.search(texto):
        return "Macrobiológicos"
    if BACT_EXTRA.search(texto):
        return "Bactérias (Bacillus e outras)"
    if MARCA_SEMIO.search(texto) and not re.search(r"extrato|azadirac", texto, re.I):
        return "Semioquímicos"
    for nome, pad in GRUPOS:
        if re.search(pad, texto, re.I):
            return nome
    return "Outros"


def data_br(s):
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s[:26], fmt).strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s


def processar(texto):
    leitor, delim = ler_csv(texto)
    campos = leitor.fieldnames
    col = {
        "registro": achar(campos, "NR_REGISTRO", "NUMERO_REGISTRO", "REGISTRO"),
        "marca": achar(campos, "MARCA_COMERCIAL", "MARCA", "PRODUTO"),
        "ingrediente": achar(campos, "INGREDIENTE_ATIVO", "INGREDIENTE"),
        "titular": achar(campos, "TITULAR_DE_REGISTRO", "TITULAR", "EMPRESA_REGISTRANTE", "EMPRESA"),
        "classe": achar(campos, "CLASSE_AGRONOMICA", "CLASSE"),
        "cultura": achar(campos, "CULTURA"),
        "praga": achar(campos, "PRAGA_NOME_COMUM", "PRAGA_NOME_CIENTIFICO", "PRAGA"),
        "organico": achar(campos, "ORGANICO"),
        "biologico": achar(campos, "BIOLOGICO"),
        "formulacao": achar(campos, "FORMULACAO"),
    }
    if not col["registro"] or not col["marca"]:
        raise SystemExit(f"Colunas essenciais não encontradas. Colunas do arquivo: {campos}")

    produtos = {}
    linhas = 0
    for r in leitor:
        linhas += 1
        reg = (r.get(col["registro"]) or "").strip()
        if not reg:
            continue
        p = produtos.get(reg)
        if p is None:
            p = produtos[reg] = {"registro": reg, "marca": "", "ingrediente": "", "titular": "", "classe": "",
                                 "organico": "", "biologicoCol": "", "formulacao": "",
                                 "culturas": set(), "pragas": set()}
        for k in ("marca", "ingrediente", "titular", "classe", "organico", "formulacao"):
            if col[k] and not p[k]:
                p[k] = limpo(r.get(col[k]))
        if col["biologico"] and not p["biologicoCol"]:
            p["biologicoCol"] = (r.get(col["biologico"]) or "").strip()
        if col["cultura"] and r.get(col["cultura"]):
            p["culturas"].add(r[col["cultura"]].strip())
        if col["praga"] and r.get(col["praga"]):
            p["pragas"].add(r[col["praga"]].strip())

    def eh_bio(p):
        if col["biologico"]:
            return sem_acento(p["biologicoCol"]).lower() in ("sim", "s", "true", "1", "x")
        return bool(PADRAO_BIO.search(p["ingrediente"] + " " + p["marca"])
                    or CLASSE_BIO.search(p["classe"]))

    bios = [p for p in produtos.values() if eh_bio(p)]
    for p in bios:
        p["grupo"] = grupo_de(p["ingrediente"] + " " + p["marca"])

    por_grupo = Counter(p["grupo"] for p in bios)
    por_titular = Counter(p["titular"] for p in bios if p["titular"])
    por_empresa = Counter(empresa_curta(p["titular"]) for p in bios if p["titular"])
    por_cultura = Counter(c for p in bios for c in sorted(p["culturas"]))
    por_classe = Counter(c.strip() for p in bios for c in re.split(r"[;,/]| e ", p["classe"]) if c.strip())
    organicos = sum(1 for p in bios if sem_acento(p["organico"]).lower().startswith("s"))
    agentes = Counter()
    for p in bios:
        for a in re.split(r"\s*\+\s*|;", p["ingrediente"]):
            a = re.sub(r"\s*\(.*?\)", "", a).strip()
            m = re.match(r"([A-Z][a-z]+ [a-z]+)", a)
            if m and PADRAO_BIO.search(m.group(1)):
                agentes[m.group(1)] += 1

    return {
        "colunas": col,
        "delimitador": delim,
        "linhasLidas": linhas,
        "produtosFormulados": len(produtos),
        "biologicos": len(bios),
        "criterio": "coluna do arquivo" if col["biologico"] else "agente biológico no ingrediente ativo",
        "organicos": organicos,
        "grupos": por_grupo.most_common(),
        "classes": por_classe.most_common(10),
        "agentes": agentes.most_common(15),
        "titulares": por_titular.most_common(15),
        "empresas": por_empresa.most_common(15),
        "culturas": por_cultura.most_common(16),
        "produtos": sorted(
            [[p["registro"], p["marca"], p["ingrediente"][:120], p["titular"], p["grupo"],
              len(p["culturas"]), len(p["pragas"])] for p in bios],
            key=lambda x: x[1].lower()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arquivo")
    ap.add_argument("--saida", default="dados/agrofit_bio.json")
    a = ap.parse_args()

    if a.arquivo:
        bruto, url, atualizado = open(a.arquivo, "rb").read(), a.arquivo, None
    else:
        url, atualizado = info_pacote()
        bruto = baixar(url)
    texto, enc = decodificar(bruto)
    res = processar(texto)

    agora = datetime.now(BRT)
    saida = {
        "fonte": "MAPA · Agrofit, dados abertos (produtos formulados)",
        "url": url,
        "arquivoAtualizadoEm": data_br(atualizado) if atualizado else None,
        "lidoEm": agora.strftime("%d/%m/%Y %Hh%M"),
        "lidoIso": agora.isoformat(timespec="seconds"),
        "tamanhoMB": round(len(bruto) / 1e6, 1),
        "codificacao": enc,
        **res,
    }
    # checagem contra arquivo incompleto: compara com a leitura anterior
    anterior = None
    try:
        anterior = json.load(open(a.saida, encoding="utf-8"))
    except (OSError, ValueError):
        pass
    saida["alerta"] = None
    if anterior and anterior.get("produtosFormulados"):
        var = saida["produtosFormulados"] / anterior["produtosFormulados"] - 1
        saida["variacaoFormulados"] = round(var * 100, 1)
        if var < -0.15:
            saida["alerta"] = (f"Produtos formulados caíram {abs(var)*100:.0f}% em relação à leitura de "
                               f"{anterior.get('lidoEm')}; conferir antes de usar.")
    hist = __import__("os").path.join(__import__("os").path.dirname(a.saida) or ".", "historico.csv")
    novo = not __import__("os").path.exists(hist)
    with open(hist, "a", encoding="utf-8") as f:
        if novo:
            f.write("lido_em;arquivo_atualizado_em;tamanho_mb;linhas;produtos_formulados;biologicos;organicos\n")
        f.write(f"{saida['lidoEm']};{saida['arquivoAtualizadoEm'] or ''};{saida['tamanhoMB']};{saida['linhasLidas']};"
                f"{saida['produtosFormulados']};{saida['biologicos']};{saida['organicos']}\n")

    produtos = saida.pop("produtos")
    saida["arquivoProdutos"] = a.saida.replace(".json", "_produtos.json")
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    with open(saida["arquivoProdutos"], "w", encoding="utf-8") as f:
        json.dump({"colunas": ["registro", "marca", "ingrediente ativo", "titular", "grupo", "nº culturas", "nº pragas"],
                   "lidoEm": saida["lidoEm"], "produtos": produtos}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{saida['produtosFormulados']} produtos formulados, {saida['biologicos']} biológicos "
          f"({saida['criterio']}); {saida['linhasLidas']} linhas; {saida['tamanhoMB']} MB")


if __name__ == "__main__":
    main()
