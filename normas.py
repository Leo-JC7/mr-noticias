# normas.py — coleta Portarias e Instruções Normativas do site oficial do INSS
# (gov.br) e complementa com o Google News (publicações no Diário Oficial).

import re
import urllib.request
from datetime import datetime
from html import unescape

from coletor import FUSO_BRASILIA, buscar_rss, titulo_contem

MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


def baixar_pagina(url: str) -> str:
    """Baixa o HTML de uma página (o gov.br exige User-Agent de navegador)."""
    pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(pedido, timeout=30) as resposta:
        return resposta.read().decode("utf-8", errors="replace")


def data_do_titulo(titulo: str) -> str:
    """Extrai a data de publicação do próprio título da norma.

    Ex.: 'PORTARIA PRES/INSS Nº 1.915, DE 20 DE JANEIRO DE 2026' -> '2026-01-20'
    """
    m = re.search(r"DE\s+(\d{1,2})º?\s+DE\s+([A-ZÇÃÉÊÍÓÚÂ]+)\s+DE\s+(\d{4})", titulo, re.IGNORECASE)
    if not m:
        return ""
    dia, mes_nome, ano = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    mes = MESES.get(mes_nome)
    if not mes:
        return ""
    try:
        return datetime(ano, mes, dia, tzinfo=FUSO_BRASILIA).isoformat()
    except ValueError:
        return ""


def numero_da_norma(titulo: str) -> str:
    """Identificador único da norma, ex.: 'portaria-1915' ou 'in-188'.

    Usado para não repetir a mesma norma vinda de fontes diferentes
    (site oficial e Google News). Devolve '' se não achar número.
    """
    t = titulo.lower()
    m = re.search(r"(portaria|instrução normativa)[^\d]{0,40}n[ºo°.]?\s*([\d.]+)", t)
    if not m:
        return ""
    tipo = "in" if "instrução" in m.group(1) else "portaria"
    numero = m.group(2).replace(".", "").strip(".")
    return f"{tipo}-{numero}"


def extrair_normas_oficiais(html: str) -> list[dict]:
    """Extrai as normas de uma página de listagem do gov.br.

    Cada norma vem num bloco <article class="entry"> com link,
    data de modificação e descrição.
    """
    normas = []
    for bloco in re.findall(r'<article class="entry">(.*?)</article>', html, re.DOTALL):
        m_link = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', bloco, re.DOTALL)
        if not m_link:
            continue
        link = m_link.group(1)
        titulo = unescape(re.sub(r"\s+", " ", m_link.group(2))).strip()

        # Descrição curta (o que a norma altera/institui), quando existir
        m_desc = re.search(r'<p class="description discreet">(.*?)</p>', bloco, re.DOTALL)
        descricao = ""
        if m_desc:
            descricao = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m_desc.group(1)))).strip()

        # Data: preferimos a do título; senão, a de modificação da página
        data = data_do_titulo(titulo)
        if not data:
            m_mod = re.search(r"última modificação\s*(\d{2})/(\d{2})/(\d{4})", bloco)
            if m_mod:
                d, mes, a = (int(x) for x in m_mod.groups())
                data = datetime(a, mes, d, tzinfo=FUSO_BRASILIA).isoformat()

        normas.append({
            "titulo": titulo,
            "link": link,
            "fonte": "INSS — gov.br (oficial)",
            "data": data,
            "descricao": descricao,
        })
    return normas


def coletar_normas(grupo: dict, max_noticias: int, bloqueio_global: list[str]) -> list[dict]:
    """Coleta as normas do ano atual no site do INSS + complemento do Google News."""
    ano = datetime.now(FUSO_BRASILIA).year
    resultado = []
    numeros_vistos = set()   # números de norma já incluídos (evita repetição)
    titulos_vistos = set()

    def adicionar(norma: dict) -> None:
        numero = numero_da_norma(norma["titulo"])
        chave = numero or norma["titulo"].lower()
        if chave in numeros_vistos or norma["titulo"].lower() in titulos_vistos:
            return
        numeros_vistos.add(chave)
        titulos_vistos.add(norma["titulo"].lower())
        resultado.append(norma)

    # 1) Fonte prioritária: páginas oficiais do INSS (ano atual; em começo de
    #    ano a lista é curta, então buscamos também o ano anterior)
    for base in grupo.get("paginas_oficiais", []):
        for ano_busca in (ano, ano - 1):
            url = f"{base.rstrip('/')}/{ano_busca}"
            try:
                html = baixar_pagina(url)
            except Exception as erro:
                print(f"  [aviso] falha ao acessar {url}: {erro}")
                continue
            for norma in extrair_normas_oficiais(html):
                adicionar(norma)

    # 2) Complemento: Google News (DOU costuma sair antes do site do INSS).
    #    Só aceitamos o que de fato menciona uma norma no título — o Google
    #    devolve junto notícias gerais do INSS, que não interessam aqui.
    bloqueadas = [p.lower() for p in bloqueio_global]
    exigidas = ["portaria", "instrução normativa", "portarias", "instruções normativas"]
    for consulta in grupo.get("consultas", []):
        try:
            noticias = buscar_rss(consulta)
        except Exception as erro:
            print(f"  [aviso] falha na consulta '{consulta}': {erro}")
            continue
        for n in noticias:
            chave = n["titulo"].lower()
            if not titulo_contem(chave, exigidas):
                continue
            if bloqueadas and titulo_contem(chave, bloqueadas):
                continue
            n["descricao"] = ""
            adicionar(n)

    # Mais recentes primeiro (normas sem data vão para o fim)
    resultado.sort(key=lambda n: n["data"], reverse=True)
    return resultado[:max_noticias]
