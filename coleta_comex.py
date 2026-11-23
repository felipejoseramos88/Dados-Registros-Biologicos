"""
Comex Stat (MDIC) · importação de fertilizantes (capítulo 31 da NCM) por estado e por mês.
Saída: dados/comex_fertilizantes.json
"""
import json, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

API = "https://api-comexstat.mdic.gov.br"
UA = {"User-Agent": "BioCAZ-inteligencia-de-mercado/1.0 (dados abertos)", "Content-Type": "application/json"}
BRT = timezone(timedelta(hours=-3))
SIGLA = {"Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF",
         "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG",
         "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ",
         "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC",
         "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"}


def call(path, body=None):
    for n in range(4):
        try:
            req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
            if not d.get("success", True):
                raise RuntimeError(d.get("message"))
            return d["data"]
        except Exception as e:
            print(f"tentativa {n+1}: {e}", file=sys.stderr)
            time.sleep(20 * (n + 1))
    raise SystemExit("Comex Stat indisponível")


def consulta(de, ate, detalhes, mensal):
    return call("/general?language=pt", {"flow": "import", "monthDetail": mensal, "period": {"from": de, "to": ate},
                                         "filters": [{"filter": "chapter", "values": ["31"]}],
                                         "details": detalhes, "metrics": ["metricFOB", "metricKG"]})["list"]


def main():
    upd = call("/general/dates/updated")
    ano, mes = int(upd["year"]), int(upd["monthNumber"])
    ate, ate_ant = f"{ano}-{mes:02d}", f"{ano-1}-{mes:02d}"
    uf = {SIGLA.get(r["state"], r["state"]): float(r["metricKG"]) / 1e9 for r in consulta(f"{ano}-01", ate, ["state"], False)}
    uf_ant = {SIGLA.get(r["state"], r["state"]): float(r["metricKG"]) / 1e9 for r in consulta(f"{ano-1}-01", ate_ant, ["state"], False)}
    mensal = {}
    # o Comex Stat aplica o intervalo de meses a cada ano; por isso o ano anterior completo vem em consulta própria
    for r in consulta(f"{ano-1}-01", f"{ano-1}-12", [], True) + consulta(f"{ano}-01", ate, [], True):
        mensal[f"{r['year']}-{int(r['monthNumber']):02d}"] = float(r["metricKG"]) / 1e9
    tot, tot_ant = sum(uf.values()), sum(uf_ant.values())
    agora = datetime.now(BRT)
    out = {
        "lidoEm": agora.strftime("%d/%m/%Y %Hh%M"), "atualizadoEm": datetime.strptime(upd["updated"], "%Y-%m-%d").strftime("%d/%m/%Y"),
        "ano": ano, "ateMes": mes, "totalMt": round(tot, 2), "totalAnteriorMt": round(tot_ant, 2),
        "variacao": round((tot / tot_ant - 1) * 100, 1) if tot_ant else None,
        "uf": sorted([[k, round(v, 3), round(uf_ant.get(k, 0), 3), round((v / uf_ant[k] - 1) * 100, 1) if uf_ant.get(k) else None]
                      for k, v in uf.items()], key=lambda x: -x[1]),
        "mensal": {"anoAnterior": [round(mensal.get(f"{ano-1}-{m:02d}", 0), 3) for m in range(1, 13)],
                   "ano": [round(mensal[f"{ano}-{m:02d}"], 3) for m in range(1, mes + 1) if f"{ano}-{m:02d}" in mensal]},
        "fonte": f"MDIC · Comex Stat, importação do capítulo 31 da NCM (adubos e fertilizantes), dados até {mes:02d}/{ano}",
    }
    with open("dados/comex_fertilizantes.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Importação jan–{mes:02d}/{ano}: {tot:.2f} Mt ({out['variacao']}% sobre {ano-1})")


if __name__ == "__main__":
    main()
