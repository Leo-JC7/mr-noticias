# gerador.py — lê dados/noticias.json e gera a página site/index.html

import json
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

PASTA = Path(__file__).parent

# Fuso de Brasília (UTC-3) — as datas das notícias chegam em UTC
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# Modelo da página. Os marcadores <!--MENU-->, <!--SECOES--> e <!--ATUALIZADO-->
# são preenchidos pelo Python. O menu fica na lateral esquerda e o JavaScript
# no fim mostra apenas a seção clicada.
MODELO_PAGINA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MR Notícias — Resumo Diário</title>
<style>
  /* Estilo simples e legível */
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f4f6f8; color: #1a2733; }
  header { background: #14365c; color: #fff; padding: 20px 16px; text-align: center; }
  header h1 { margin: 0 0 4px; font-size: 1.5rem; }
  header p { margin: 0; opacity: 0.8; font-size: 0.9rem; }
  .layout { display: flex; max-width: 1080px; margin: 0 auto; padding: 16px; gap: 16px; align-items: flex-start; }

  /* Menu lateral */
  nav { flex: 0 0 230px; position: sticky; top: 16px; background: #fff; border-radius: 10px;
        padding: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  nav a { display: block; padding: 10px 12px; border-radius: 8px; color: #14365c;
          font-weight: 600; text-decoration: none; font-size: 0.95rem; }
  nav a:hover { background: #eef3f9; }
  nav a.ativo { background: #14365c; color: #fff; }

  /* Conteúdo */
  main { flex: 1; min-width: 0; }
  section { background: #fff; border-radius: 10px; padding: 18px 22px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  section h2 { margin: 0 0 12px; font-size: 1.2rem; border-bottom: 2px solid #14365c; padding-bottom: 8px; }
  ul { list-style: none; margin: 0; padding: 0; }
  li { padding: 10px 0; border-bottom: 1px solid #eef1f4; }
  li:last-child { border-bottom: none; }
  li a { color: #0b4f9e; text-decoration: none; font-weight: 500; }
  li a:hover { text-decoration: underline; }
  .descricao { font-size: 0.9rem; color: #3d4f60; margin-top: 3px; }
  .meta { font-size: 0.8rem; color: #6b7a89; margin-top: 3px; }
  .vazio { color: #6b7a89; font-style: italic; }
  footer { text-align: center; font-size: 0.8rem; color: #6b7a89; padding: 16px; }

  /* Em telas pequenas (celular), o menu vira uma faixa no topo */
  @media (max-width: 700px) {
    .layout { flex-direction: column; }
    nav { position: static; flex: none; width: auto; align-self: stretch;
          display: flex; overflow-x: auto; gap: 4px; }
    nav a { white-space: nowrap; font-size: 0.85rem; }
  }
</style>
</head>
<body>
<header>
  <h1>MR Notícias — Resumo Diário</h1>
  <p>Atualizado em <!--ATUALIZADO--></p>
</header>
<div class="layout">
<nav id="menu">
<!--MENU-->
</nav>
<main>
<!--SECOES-->
</main>
</div>
<footer>Fontes: Google News e gov.br/INSS · Gerado automaticamente</footer>
<script>
// Mostra apenas a seção escolhida e marca o item ativo no menu
function mostrar(id) {
  document.querySelectorAll('main section').forEach(function (s) {
    s.hidden = (s.id !== id);
  });
  document.querySelectorAll('#menu a').forEach(function (a) {
    a.classList.toggle('ativo', a.getAttribute('data-alvo') === id);
  });
  history.replaceState(null, '', '#' + id); // permite compartilhar o link da seção
}
document.querySelectorAll('#menu a').forEach(function (a) {
  a.addEventListener('click', function (evento) {
    evento.preventDefault();
    mostrar(a.getAttribute('data-alvo'));
  });
});
// Ao abrir: usa a seção do link (#secao), senão a primeira
var inicial = location.hash.replace('#', '');
if (!document.getElementById(inicial)) {
  inicial = document.querySelector('main section').id;
}
mostrar(inicial);
</script>
</body>
</html>
"""


def formatar_data(data_iso: str) -> str:
    """Converte data ISO para o formato brasileiro, no fuso de Brasília.

    Datas com horário viram 'dd/mm/aaaa hh:mm'; datas sem horário
    (caso das portarias), apenas 'dd/mm/aaaa'.
    """
    if not data_iso:
        return ""
    try:
        data = datetime.fromisoformat(data_iso)
        if data.tzinfo is not None:
            data = data.astimezone(FUSO_BRASILIA)
        if (data.hour, data.minute) == (0, 0):
            return data.strftime("%d/%m/%Y")
        return data.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return data_iso


def montar_secao(grupo: dict) -> str:
    """Monta o HTML de um grupo de notícias."""
    itens = []
    for n in grupo["noticias"]:
        # Linha extra com a descrição (usada nas portarias/INs)
        descricao = ""
        if n.get("descricao"):
            descricao = f'<div class="descricao">{escape(n["descricao"])}</div>'
        meta = " · ".join(p for p in [escape(n["fonte"]), formatar_data(n["data"])] if p)
        itens.append(
            f'<li><a href="{escape(n["link"])}" target="_blank" rel="noopener">'
            f'{escape(n["titulo"])}</a>{descricao}<div class="meta">{meta}</div></li>'
        )
    if not itens:
        lista = '<p class="vazio">Nenhuma notícia encontrada hoje.</p>'
    else:
        lista = "<ul>\n" + "\n".join(itens) + "\n</ul>"
    return f'<section id="{escape(grupo["id"])}">\n<h2>{escape(grupo["titulo"])}</h2>\n{lista}\n</section>'


def gerar_pagina() -> Path:
    """Gera site/index.html a partir de dados/noticias.json."""
    dados = json.loads((PASTA / "dados" / "noticias.json").read_text(encoding="utf-8"))

    # Itens do menu lateral (um por grupo)
    menu = "\n".join(
        f'<a href="#{escape(g["id"])}" data-alvo="{escape(g["id"])}">{escape(g["titulo"])}</a>'
        for g in dados["grupos"]
    )
    secoes = "\n".join(montar_secao(g) for g in dados["grupos"])
    atualizado = formatar_data(dados["atualizado_em"])

    html = (MODELO_PAGINA
            .replace("<!--ATUALIZADO-->", atualizado)
            .replace("<!--MENU-->", menu)
            .replace("<!--SECOES-->", secoes))

    pasta_site = PASTA / "site"
    pasta_site.mkdir(exist_ok=True)
    arquivo = pasta_site / "index.html"
    arquivo.write_text(html, encoding="utf-8")
    print(f"Página gerada em {arquivo}")
    return arquivo


if __name__ == "__main__":
    gerar_pagina()
