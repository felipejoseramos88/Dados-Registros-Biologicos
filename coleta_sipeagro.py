"""
SIPEAGRO · estabelecimentos da área de fertilizantes, inoculantes e corretivos (dados abertos do MAPA).
Gera dados/sipeagro_bio.json com:
- fábricas e importadores de inoculantes e biofertilizantes por UF e por empresa;
- comerciantes registrados (revendas) por UF e nos municípios das regiões BioCAZ.
O CNPJ vem mascarado na fonte; contamos estabelecimentos pelo número de registro.
"""
import csv, io, json, re, sys, unicodedata, urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

URL = ("https://dados.agricultura.gov.br/dataset/52a01565-72d6-410e-b21b-64035831a7be/"
       "resource/e0bbc9d5-f161-448b-a6d4-c7beb312ec33/download/sipeagrofertilizante.csv")
PACOTE = "https://dados.agricultura.gov.br/api/3/action/package_show?id=52a01565-72d6-410e-b21b-64035831a7be"
UA = {"User-Agent": "BioCAZ-inteligencia-de-mercado/1.0 (dados abertos)"}
BRT = timezone(timedelta(hours=-3))
UFS_BIOCAZ = ["MT", "GO", "MG", "BA", "TO", "MA", "PI", "MS"]


def baixar(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        esperado = r.headers.get("Content-Length")
        b = r.read()
    if esperado and len(b) != int(esperado):
        raise SystemExit(f"download incompleto: {len(b)} de {esperado}")
    return b


def limpo(t):
    return re.sub(r"\s+", " ", (t or "").replace("\x96", "–")).strip()


def empresa_curta(t):
    t = re.split(r"\s+[-–]\s+", limpo(t))[0]
    t = re.sub(r"\b(ltda|s\.?/?a\.?|eireli|me|epp)\b\.?", "", t, flags=re.I)
    t = re.sub(r"\b(ind[uú]stria|com[eé]rcio|e|de|do|da|dos|das|distribui[cç][aã]o|importa[cç][aã]o|exporta[cç][aã]o)\b", " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" .,-")
    return " ".join(t.split()[:2]).title()


def data_br(s):
    try:
        return datetime.fromisoformat(s[:19]).strftime("%d/%m/%Y")
    except Exception:
        return s


def main(saida="dados/sipeagro_bio.json"):
    atualizado = None
    try:
        for r in json.loads(baixar(PACOTE))["result"]["resources"]:
            if r["name"].strip().lower() == "fertilizantes":
                atualizado = data_br(r.get("last_modified") or "")
    except Exception as e:
        print("aviso: metadados indisponíveis:", e, file=sys.stderr)

    b = baixar(URL)
    t = b.decode("utf-8-sig", "replace")
    rows = list(csv.DictReader(io.StringIO(t), delimiter=";"))
    need = {"UNIDADE_DA_FEDERACAO", "MUNICIPIO", "NUMERO_REGISTRO_ESTABELECIMENTO", "STATUS_DO_REGISTRO",
            "RAZAO_SOCIAL", "ATIVIDADE", "CLASSIFICACAO"}
    if not need.issubset(rows[0].keys()):
        raise SystemExit(f"colunas mudaram: {list(rows[0].keys())}")
    ativos = [r for r in rows if r["STATUS_DO_REGISTRO"].strip().lower() == "ativo"]

    # Fábricas/importadores de inoculante e biofertilizante (classificação do registro)
    bio = defaultdict(set)          # tipo -> registros
    bio_uf = defaultdict(Counter)   # tipo -> UF
    bio_emp = defaultdict(Counter)  # tipo -> empresa
    vistos = set()
    for r in ativos:
        cl = r["CLASSIFICACAO"].upper()
        tipo = "Inoculante" if "INOCULANTE" in cl else "Biofertilizante" if "BIOFERTILIZANTE" in cl else None
        if not tipo:
            continue
        chave = (tipo, r["NUMERO_REGISTRO_ESTABELECIMENTO"])
        if chave in vistos:
            continue
        vistos.add(chave)
        bio[tipo].add(r["NUMERO_REGISTRO_ESTABELECIMENTO"])
        bio_uf[tipo][r["UNIDADE_DA_FEDERACAO"]] += 1
        bio_emp[tipo][empresa_curta(r["RAZAO_SOCIAL"])] += 1

    # Comerciantes (revendas) registrados
    com = {}
    for r in ativos:
        if r["ATIVIDADE"].upper() == "COMERCIANTE":
            com.setdefault(r["NUMERO_REGISTRO_ESTABELECIMENTO"], r)
    com_uf = Counter(r["UNIDADE_DA_FEDERACAO"] for r in com.values())
    com_mun = Counter((r["UNIDADE_DA_FEDERACAO"], limpo(r["MUNICIPIO"])) for r in com.values()
                      if r["UNIDADE_DA_FEDERACAO"] in UFS_BIOCAZ)
    por_ativ = Counter()
    seen = set()
    for r in ativos:
        k = (r["NUMERO_REGISTRO_ESTABELECIMENTO"], r["ATIVIDADE"])
        if k not in seen:
            seen.add(k)
            por_ativ[r["ATIVIDADE"].title()] += 1

    agora = datetime.now(BRT)
    out = {
        "fonte": "MAPA · SIPEAGRO, dados abertos (estabelecimentos de fertilizantes, inoculantes e corretivos)",
        "url": URL, "arquivoAtualizadoEm": atualizado,
        "lidoEm": agora.strftime("%d/%m/%Y %Hh%M"), "lidoIso": agora.isoformat(timespec="seconds"),
        "linhas": len(rows), "registrosAtivos": len({r["NUMERO_REGISTRO_ESTABELECIMENTO"] for r in ativos}),
        "porAtividade": por_ativ.most_common(),
        "inoculante": {"estabelecimentos": len(bio["Inoculante"]), "uf": bio_uf["Inoculante"].most_common(),
                       "empresas": bio_emp["Inoculante"].most_common(15)},
        "biofertilizante": {"estabelecimentos": len(bio["Biofertilizante"]), "uf": bio_uf["Biofertilizante"].most_common(),
                            "empresas": bio_emp["Biofertilizante"].most_common(15)},
        "comerciantes": {"total": len(com), "uf": com_uf.most_common(),
                         "municipiosBioCAZ": [[uf, m, n] for (uf, m), n in com_mun.most_common(40)]},
        "nota": "Estabelecimentos com registro ativo no SIPEAGRO. Inoculante e biofertilizante = fábricas e importadores "
                "com essa classificação; comerciantes = revendas registradas para fertilizantes, inoculantes e corretivos.",
    }
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{out['registrosAtivos']} estabelecimentos ativos; inoculante {len(bio['Inoculante'])}, "
          f"biofertilizante {len(bio['Biofertilizante'])}, comerciantes {len(com)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
