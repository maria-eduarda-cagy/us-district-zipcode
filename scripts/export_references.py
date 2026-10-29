"""Writes docs/references.md and docs/references.pt-BR.md: every source the
project's data comes from, with its exact URL. Rows in `sources` (ballots,
results, calendars, polling places, precinct registration) and
`district_layers` (boundary layers) are read from the database, so the list
can't drift from what is loaded; sources used only as validation gates or
services (candidate lists, geocoders) are listed in CURATED below.

Re-run after any loader. Needs psql and the SUPABASE_DB_* variables:
    set -a; source .env; set +a
    python3 scripts/export_references.py
"""
import datetime
import os
import subprocess

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

SOURCE_TYPES = {
    "certified_ballot_pdf": ("Certified ballots (Maryland, MSBE)", "Cédulas certificadas (Maryland, MSBE)"),
    "sample_ballot_pdf": ("Sample ballots (Virginia localities)", "Cédulas de amostra (localidades da Virginia)"),
    "election_results_csv": ("Official results", "Resultados oficiais"),
    "election_calendar": ("Election calendar", "Calendário eleitoral"),
    "early_voting_centers_pdf": ("Early voting centers", "Locais de votação antecipada"),
    "precinct_reference_xlsx": ("Registered voters per precinct", "Eleitores registrados por precinto"),
}

# (EN description, PT description, URL) -- used by loaders or functions but
# not stored as a `sources` row.
CURATED = {
    "validation": [
        ("MSBE official general candidate list, statewide (gate: the MD loader aborts on any mismatch)",
         "Lista oficial de candidatos do MSBE, estadual (trava: o loader de MD aborta em qualquer divergência)",
         "https://elections.maryland.gov/elections/2026/general_candidates/2026_GG_statewide_candidatelist.csv"),
        ("MSBE official general candidate list, all counties (same gate)",
         "Lista oficial de candidatos do MSBE, todos os counties (mesma trava)",
         "https://elections.maryland.gov/elections/2026/general_candidates/2026_GG_all_counties_candidatelist.csv"),
        ("MSBE number of precincts and polling places (confirms which precinct polygons are obsolete)",
         "Número de precintos e locais de votação do MSBE (confirma quais polígonos estão obsoletos)",
         "https://elections.maryland.gov/elections/2026/Number_of_Precincts_and_Polling_Places.pdf"),
        ("Virginia ELECT candidate lists (Virginia ballots validated against them)",
         "Listas de candidatos do Virginia ELECT (cédulas da Virginia validadas contra elas)",
         "https://www.elections.virginia.gov/casting-a-ballot/candidate-list/"),
        ("Fairfax County precinct descriptions (precinct -> congressional district)",
         "Descrições de precintos de Fairfax (precinto -> distrito congressional)",
         "https://www.fairfaxcounty.gov/elections/precincts"),
        ("Virginia constitutional amendment explanations (question 1)",
         "Explicações das emendas constitucionais da Virginia (questão 1)",
         "https://www.elections.virginia.gov/election-law/proposed-constitutional-amendment-question-1/"),
        ("Virginia constitutional amendment explanations (question 2)",
         "Explicações das emendas constitucionais da Virginia (questão 2)",
         "https://www.elections.virginia.gov/election-law/proposed-constitutional-amendment-question-2/"),
        ("Virginia constitutional amendment explanations (question 3)",
         "Explicações das emendas constitucionais da Virginia (questão 3)",
         "https://www.elections.virginia.gov/election-law/proposed-constitutional-amendment-question-3/"),
        ("Fairfax County bond plain-language statement (community health and human services)",
         "Declaração em linguagem simples do bond de Fairfax (saúde e serviços humanos)",
         "https://www.fairfaxcounty.gov/bond/sites/bond/files/Assets/Documents/2026%20Plain%20Language%20Statements/CHHS%20PLS%20Web%20English.pdf"),
        ("Fairfax County bond plain-language statement (parks)",
         "Declaração em linguagem simples do bond de Fairfax (parques)",
         "https://www.fairfaxcounty.gov/bond/sites/bond/files/Assets/Documents/2026%20Plain%20Language%20Statements/Parks%20PLS%20Web%20English.pdf"),
    ],
    "services": [
        ("Census geocoder (address -> point; first choice in the search and sample-ballot functions)",
         "Geocoder do Census (endereço -> ponto; primeira opção nas funções search e sample-ballot)",
         "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"),
        ("ArcGIS World geocoder (fallback when the Census geocoder fails)",
         "Geocoder ArcGIS World (alternativa quando o do Census falha)",
         "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"),
        ("Maryland iMAP locator (geocodes polling places in MD loaders)",
         "Localizador do Maryland iMAP (geocodifica locais de votação nos loaders de MD)",
         "https://mdgeodata.md.gov/imap/rest/services/GeocodeServices/MD_MultiroleLocator/GeocodeServer/findAddressCandidates"),
        ("Virginia VGIN locator (geocodes in VA loaders)",
         "Localizador VGIN da Virginia (geocodifica nos loaders da VA)",
         "https://gismaps.vdem.virginia.gov/arcgis/rest/services/Geocoding/VGIN_Composite_Locator/GeocodeServer/findAddressCandidates"),
        ("DC Master Address Repository locator",
         "Localizador do Master Address Repository de DC",
         "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_APPS/DCGIS_MAR/GeocodeServer/findAddressCandidates"),
        ("Census TIGER/Line downloads (congressional, state legislative, county, place, school districts)",
         "Downloads do Census TIGER/Line (congressional, legislativo estadual, county, place, distritos escolares)",
         "https://www2.census.gov/geo/tiger/TIGER2026/"),
    ],
    "measurement": [
        ("Census 2020 blocks with population (estimate of residents in obsolete precinct polygons)",
         "Quarteirões do Censo 2020 com população (estimativa de moradores em polígonos de precintos obsoletos)",
         "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/10"),
    ],
}

TEXT = {
    "en": {
        "title": "References",
        "intro": "Every source the data in this project comes from, with its exact URL. Generated by "
                 "`scripts/export_references.py` from the database (`sources`, `district_layers`) plus the "
                 "validation sources and services the loaders and functions call. Last generated: {date}. "
                 "Versão em português: [references.pt-BR.md](references.pt-BR.md). What each source is used for "
                 "and its status: [data-sources.md](data-sources.md).",
        "loaded": "Loaded documents (`sources` table)",
        "cols": "| Document | Published | Loaded |\n|---|---|---|",
        "layers": "Boundary layers (`district_layers` table)",
        "layer_cols": "| Layer | Type | Source |\n|---|---|---|",
        "tiger_gap": "TIGER/Line (legacy table, URL and vintage not recorded; see gaps below)",
        "validation": "Validation sources (gates and official explanations, not stored as rows)",
        "services": "Services and downloads",
        "measurement": "Sources used only to measure coverage",
        "gaps": "Known traceability gaps",
        "gap_items": [
            "The TIGER/Line layers (`cd119`, `sldu`, `sldl`, `county`, `place`, `unsd`) were loaded before this "
            "project tracked sources: no URL or vintage is stored. Checked 2026-10-28: Maryland's state "
            "legislative districts in the database match TIGER 2026 (`tl_2026_24_sldl`) to within 0.19 km² per "
            "district, i.e. the 2022 plan in force. The other TIGER layers have not been compared yet.",
            "Hand-transcribed loaders (Montgomery primary ballot style 125) point at the certified PDF, not at a "
            "page number.",
        ],
    },
    "pt": {
        "title": "Referências",
        "intro": "Todas as fontes de onde vêm os dados do projeto, com a URL exata. Gerado por "
                 "`scripts/export_references.py` a partir do banco (`sources`, `district_layers`) mais as fontes "
                 "de validação e os serviços que os loaders e as funções chamam. Última geração: {date}. "
                 "English version: [references.md](references.md). Para que serve cada fonte e o status: "
                 "[data-sources.md](data-sources.md).",
        "loaded": "Documentos carregados (tabela `sources`)",
        "cols": "| Documento | Publicado | Carregado |\n|---|---|---|",
        "layers": "Camadas de fronteiras (tabela `district_layers`)",
        "layer_cols": "| Camada | Tipo | Fonte |\n|---|---|---|",
        "tiger_gap": "TIGER/Line (tabela legada, URL e versão não registradas; veja as lacunas abaixo)",
        "validation": "Fontes de validação (travas e explicações oficiais, não guardadas como linhas)",
        "services": "Serviços e downloads",
        "measurement": "Fontes usadas só para medir a cobertura",
        "gaps": "Lacunas de rastreabilidade conhecidas",
        "gap_items": [
            "As camadas TIGER/Line (`cd119`, `sldu`, `sldl`, `county`, `place`, `unsd`) foram carregadas antes de "
            "o projeto registrar fontes: não há URL nem versão guardadas. Conferido em 2026-10-28: os distritos "
            "legislativos estaduais de Maryland no banco batem com o TIGER 2026 (`tl_2026_24_sldl`) com diferença "
            "máxima de 0,19 km² por distrito, ou seja, o mapa de 2022 em vigor. As outras camadas TIGER ainda não "
            "foram comparadas.",
            "Loaders transcritos à mão (estilo de cédula 125 da primária de Montgomery) apontam para o PDF "
            "certificado, não para um número de página.",
        ],
    },
}


def query(sql):
    env = dict(os.environ, PGPASSWORD=os.environ["SUPABASE_DB_PASSWORD"], PGHOST=os.environ["SUPABASE_DB_HOST"],
               PGPORT=os.environ["SUPABASE_DB_PORT"], PGUSER=os.environ["SUPABASE_DB_USER"],
               PGDATABASE=os.environ["SUPABASE_DB_NAME"])
    out = subprocess.run(["psql", "-X", "-A", "-t", "-F", "\t", "-c", sql], env=env, capture_output=True, text=True,
                         check=True).stdout
    return [line.split("\t") for line in out.splitlines() if line]


def link(url):
    return f"[{url.rstrip('/').split('/')[-1] or url}]({url})"


def render(lang, sources, layers, today):
    t = TEXT[lang]
    i = 0 if lang == "en" else 1
    lines = [f"# {t['title']}", "", t["intro"].format(date=today), "", f"## {t['loaded']}", ""]
    for source_type in sorted({s[0] for s in sources}):
        lines += [f"### {SOURCE_TYPES.get(source_type, (source_type, source_type))[i]}", "", t["cols"]]
        lines += [f"| {link(url)} | {published or '—'} | {fetched} |"
                  for st, url, published, fetched in sources if st == source_type]
        lines.append("")
    lines += [f"## {t['layers']}", "", t["layer_cols"]]
    lines += [f"| {name} (`{layer_id}`) | {layer_type} | {f'<{url}>' if url else t['tiger_gap']} |"
              for layer_id, layer_type, name, url in layers]
    lines.append("")
    for key in ("validation", "services", "measurement"):
        lines += [f"## {t[key]}", ""]
        lines += [f"- {item[i]}: <{item[2]}>" for item in CURATED[key]]
        lines.append("")
    lines += [f"## {t['gaps']}", ""] + [f"- {g}" for g in t["gap_items"]] + [""]
    return "\n".join(lines)


def main():
    sources = query("select source_type, source_url, coalesce(effective_date::text, ''), fetched_at::date "
                    "from sources order by source_type, source_url")
    layers = query("select layer_id, layer_type, name, coalesce(source_url, '') from district_layers "
                   "order by state nulls first, layer_id")
    today = datetime.date.today().isoformat()
    for lang, name in (("en", "references.md"), ("pt", "references.pt-BR.md")):
        with open(os.path.join(DOCS, name), "w") as f:
            f.write(render(lang, sources, layers, today))
    print(f"{len(sources)} sources, {len(layers)} layers written to docs/references*.md")


if __name__ == "__main__":
    main()
