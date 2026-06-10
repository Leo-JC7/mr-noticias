# coletor.py — busca notícias no Google News (RSS) e salva em dados/noticias.json
# Usa apenas a biblioteca padrão do Python (não precisa instalar nada).

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

# Pasta onde este arquivo está (para os caminhos funcionarem de qualquer lugar)
PASTA = Path(__file__).parent

# Fuso de Brasília (UTC-3). Fixo no código porque o script roda na nuvem do
# GitHub, cujo relógio é UTC — sem isso a hora sairia 3h adiantada.
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# Endereço base da busca RSS do Google News (em português do Brasil)
URL_BASE = "https://news.google.com/rss/search?q={consulta}&hl=pt-BR&gl=BR&ceid=BR:pt-419"


def buscar_rss(consulta: str) -> list[dict]:
    """Busca uma consulta no Google News e devolve a lista de notícias."""
    url = URL_BASE.format(consulta=urllib.parse.quote(consulta))
    # User-Agent evita que o servidor recuse a requisição
    pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        xml_texto = resposta.read()

    raiz = ET.fromstring(xml_texto)
    noticias = []
    # Cada <item> do RSS é uma notícia
    for item in raiz.iter("item"):
        titulo = item.findtext("title", default="")
        link = item.findtext("link", default="")
        data_texto = item.findtext("pubDate", default="")
        fonte = item.findtext("source", default="")

        # Converte a data do formato RSS para ISO (mais fácil de ordenar)
        try:
            data = parsedate_to_datetime(data_texto).astimezone(timezone.utc)
            data_iso = data.isoformat()
        except (ValueError, TypeError):
            data_iso = ""

        # O Google coloca " - Fonte" no fim do título; removemos para ficar limpo
        if fonte and titulo.endswith(f" - {fonte}"):
            titulo = titulo[: -len(f" - {fonte}")]

        noticias.append({
            "titulo": titulo.strip(),
            "link": link,
            "fonte": fonte,
            "data": data_iso,
        })
    return noticias


def titulo_contem(titulo: str, termos: list[str]) -> bool:
    """True se o título contém algum dos termos como palavra inteira.

    Usar 'palavra inteira' evita falsos positivos: ex. o termo 'tea' não
    deve casar com 'teatro'. Tudo é comparado em minúsculas.
    """
    for termo in termos:
        padrao = re.escape(termo)
        # \b marca o limite da palavra, mas só funciona junto de letra/número
        # (termos como 'urgente:' terminam em ':' e dispensam o \b no fim)
        if termo[0].isalnum():
            padrao = r"\b" + padrao
        if termo[-1].isalnum():
            padrao = padrao + r"\b"
        if re.search(padrao, titulo):
            return True
    return False


def palavras_significativas(titulo: str) -> set[str]:
    """Conjunto das palavras do título com 4+ letras (ignora 'de', 'em', 'que'...)."""
    return {p for p in re.findall(r"\w+", titulo) if len(p) >= 4}


def eh_quase_repetida(palavras: set[str], aceitas: list[set[str]]) -> bool:
    """True se já aceitamos uma notícia com título muito parecido.

    Fontes diferentes publicam a mesma notícia com pequenas variações;
    consideramos repetida se 70%+ das palavras coincidem.
    """
    for outras in aceitas:
        menor = min(len(palavras), len(outras))
        if menor and len(palavras & outras) / menor >= 0.7:
            return True
    return False


def coletar_grupo(grupo: dict, max_noticias: int, bloqueio_global: list[str],
                  fontes_bloqueadas: set[str]) -> list[dict]:
    """Roda todas as consultas de um grupo, aplica os filtros e ordena por data.

    Filtros (todos opcionais, definidos no config.json):
    - filtro_titulo: o título PRECISA ter uma destas palavras (ex.: cidades da região)
    - palavras_relevantes: o título PRECISA ter um destes termos de impacto PCD
    - bloquear_titulo (+ lista global): se o título tiver um destes termos, descarta
    - bloquear_fontes (global): descarta tudo que vier destes portais
    """
    vistas = set()        # títulos já vistos (para não repetir)
    aceitas_palavras = [] # palavras dos títulos aceitos (detecta quase-repetidas)
    filtro = [p.lower() for p in grupo.get("filtro_titulo", [])]
    relevantes = [p.lower() for p in grupo.get("palavras_relevantes", [])]
    bloqueadas = [p.lower() for p in bloqueio_global + grupo.get("bloquear_titulo", [])]
    resultado = []
    descartadas = 0
    for consulta in grupo["consultas"]:
        try:
            noticias = buscar_rss(consulta)
        except Exception as erro:
            print(f"  [aviso] falha na consulta '{consulta}': {erro}")
            continue
        for n in noticias:
            chave = n["titulo"].lower()
            if not chave or chave in vistas:
                continue
            vistas.add(chave)
            # Aplica os filtros na ordem: fonte -> região -> relevância -> bloqueio
            if n["fonte"].lower() in fontes_bloqueadas:
                descartadas += 1
                continue
            if filtro and not titulo_contem(chave, filtro):
                descartadas += 1
                continue
            if relevantes and not titulo_contem(chave, relevantes):
                descartadas += 1
                continue
            if bloqueadas and titulo_contem(chave, bloqueadas):
                descartadas += 1
                continue
            # Mesma notícia publicada por fontes diferentes conta como repetida
            palavras = palavras_significativas(chave)
            if eh_quase_repetida(palavras, aceitas_palavras):
                descartadas += 1
                continue
            aceitas_palavras.append(palavras)
            resultado.append(n)
    if descartadas:
        print(f"  {descartadas} notícias descartadas pelos filtros")

    # Mais recentes primeiro
    resultado.sort(key=lambda n: n["data"], reverse=True)
    return resultado[:max_noticias]


def coletar_tudo() -> dict:
    """Coleta todos os grupos definidos no config.json e salva em dados/noticias.json."""
    config = json.loads((PASTA / "config.json").read_text(encoding="utf-8"))
    max_por_grupo = config.get("max_por_grupo", 15)
    bloqueio_global = config.get("bloquear_titulo_global", [])
    fontes_bloqueadas = {f.lower() for f in config.get("bloquear_fontes", [])}

    dados = {
        "atualizado_em": datetime.now(FUSO_BRASILIA).isoformat(timespec="seconds"),
        "grupos": [],
    }
    for grupo in config["grupos"]:
        print(f"Coletando: {grupo['titulo']}...")
        noticias = coletar_grupo(grupo, max_por_grupo, bloqueio_global, fontes_bloqueadas)
        print(f"  {len(noticias)} notícias encontradas")
        dados["grupos"].append({
            "id": grupo["id"],
            "titulo": grupo["titulo"],
            "noticias": noticias,
        })

    # Salva o resultado em JSON (a página HTML é gerada a partir dele)
    pasta_dados = PASTA / "dados"
    pasta_dados.mkdir(exist_ok=True)
    arquivo = pasta_dados / "noticias.json"
    arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dados salvos em {arquivo}")
    return dados


if __name__ == "__main__":
    coletar_tudo()
