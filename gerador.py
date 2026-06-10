# gerador.py — lê dados/noticias.json e gera a página site/index.html

import json
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

PASTA = Path(__file__).parent

# Fuso de Brasília (UTC-3) — as datas das notícias chegam em UTC
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# Modelo da página. Os {marcadores} são preenchidos pelo Python.
MODELO_PAGINA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MR Notícias — Resumo Diário</title>
<style>
  /* Estilo simples e legível */
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f4f6f8; color: #1a2733; }}
  header {{ background: #14365c; color: #fff; padding: 24px 16px; text-align: center; }}
  header h1 {{ margin: 0 0 4px; font-size: 1.6rem; }}
  header p {{ margin: 0; opacity: 0.8; font-size: 0.9rem; }}
  main {{ max-width: 860px; margin: 0 auto; padding: 16px; }}
  nav {{ text-align: center; margin: 12px 0 4px; }}
  nav a {{ color: #14365c; font-weight: 600; text-decoration: none; margin: 0 10px; }}
  nav a:hover {{ text-decoration: underline; }}
  section {{ background: #fff; border-radius: 10px; padding: 18px 22px; margin: 18px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  section h2 {{ margin: 0 0 12px; font-size: 1.2rem; border-bottom: 2px solid #14365c; padding-bottom: 8px; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li {{ padding: 10px 0; border-bottom: 1px solid #eef1f4; }}
  li:last-child {{ border-bottom: none; }}
  li a {{ color: #0b4f9e; text-decoration: none; font-weight: 500; }}
  li a:hover {{ text-decoration: underline; }}
  .meta {{ font-size: 0.8rem; color: #6b7a89; margin-top: 3px; }}
  .vazio {{ color: #6b7a89; font-style: italic; }}
  footer {{ text-align: center; font-size: 0.8rem; color: #6b7a89; padding: 16px; }}
</style>
</head>
<body>
<header>
  <h1>MR Notícias — Resumo Diário</h1>
  <p>Atualizado em {atualizado_em}</p>
</header>
<main>
<nav>{navegacao}</nav>
{secoes}
</main>
<footer>Fonte: Google News · Gerado automaticamente</footer>
</body>
</html>
"""


def formatar_data(data_iso: str) -> str:
    """Converte data ISO para o formato brasileiro (dd/mm/aaaa hh:mm), no fuso de Brasília."""
    if not data_iso:
        return ""
    try:
        data = datetime.fromisoformat(data_iso)
        if data.tzinfo is not None:
            data = data.astimezone(FUSO_BRASILIA)
        return data.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return data_iso


def montar_secao(grupo: dict) -> str:
    """Monta o HTML de um grupo de notícias."""
    itens = []
    for n in grupo["noticias"]:
        meta = " · ".join(p for p in [escape(n["fonte"]), formatar_data(n["data"])] if p)
        itens.append(
            f'<li><a href="{escape(n["link"])}" target="_blank" rel="noopener">'
            f'{escape(n["titulo"])}</a><div class="meta">{meta}</div></li>'
        )
    if not itens:
        lista = '<p class="vazio">Nenhuma notícia encontrada hoje.</p>'
    else:
        lista = "<ul>\n" + "\n".join(itens) + "\n</ul>"
    return f'<section id="{escape(grupo["id"])}">\n<h2>{escape(grupo["titulo"])}</h2>\n{lista}\n</section>'


def gerar_pagina() -> Path:
    """Gera site/index.html a partir de dados/noticias.json."""
    dados = json.loads((PASTA / "dados" / "noticias.json").read_text(encoding="utf-8"))

    # Links de navegação no topo (um por grupo)
    navegacao = " | ".join(
        f'<a href="#{escape(g["id"])}">{escape(g["titulo"])}</a>' for g in dados["grupos"]
    )
    secoes = "\n".join(montar_secao(g) for g in dados["grupos"])
    atualizado = formatar_data(dados["atualizado_em"])

    html = MODELO_PAGINA.format(atualizado_em=atualizado, navegacao=navegacao, secoes=secoes)

    pasta_site = PASTA / "site"
    pasta_site.mkdir(exist_ok=True)
    arquivo = pasta_site / "index.html"
    arquivo.write_text(html, encoding="utf-8")
    print(f"Página gerada em {arquivo}")
    return arquivo


if __name__ == "__main__":
    gerar_pagina()
