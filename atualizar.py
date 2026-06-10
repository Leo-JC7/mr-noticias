# atualizar.py — script principal: coleta as notícias e gera a página.
# Uso: python atualizar.py

from coletor import coletar_tudo
from gerador import gerar_pagina

if __name__ == "__main__":
    coletar_tudo()      # 1. busca as notícias e salva em dados/noticias.json
    arquivo = gerar_pagina()  # 2. gera a página site/index.html
    print(f"\nPronto! Abra no navegador: {arquivo}")
