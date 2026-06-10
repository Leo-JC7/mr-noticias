# MR Notícias — Agregador Diário

**Página da equipe: https://leo-jc7.github.io/mr-noticias/**
(atualiza sozinha todo dia às ~7h, horário de Brasília)

Busca notícias no Google News (via RSS, sem precisar de chave de API) e gera uma
página HTML com 3 grupos:

1. **INSS**
2. **Pessoas com Deficiência — Brasil**
3. **Pessoas com Deficiência — Cotia e Região** (cidades num raio de ~30km)

## Como usar

**Jeito fácil:** dê dois cliques no atalho **"MR Notícias"** na Área de Trabalho
(ou no arquivo `abrir.bat`). Ele busca as notícias mais recentes e abre a página
já atualizada. Sem internet, ele abre a última versão salva.

Pelo terminal, se preferir:

```powershell
python atualizar.py
```

e depois abra `site\index.html` no navegador.

> **Por que não atualiza no F5?** A página é um arquivo estático — o navegador
> não consegue executar Python ao recarregar. Por isso o atalho faz os dois
> passos (atualizar + abrir) num clique só.

## Estrutura do projeto

| Arquivo | O que faz |
|---|---|
| `config.json` | Define os grupos, os termos de busca e o limite de notícias |
| `coletor.py` | Busca as notícias no Google News e salva em `dados/noticias.json` |
| `gerador.py` | Lê o JSON e gera a página `site/index.html` |
| `atualizar.py` | Script principal — roda a coleta e a geração de uma vez |
| `abrir.bat` | Atalho de clique duplo: atualiza e abre a página no navegador |

## Personalizando buscas e filtros (config.json)

O objetivo é trazer só notícia que **afeta a vida das pessoas com deficiência**
(leis, inclusão, acessibilidade, emprego PCD, benefícios) e descartar menções
de passagem (eventos gerais, vagas genéricas) e clickbait.

Buscas (por grupo):

- **`consultas`**: termos pesquisados no Google News. Dicas:
  - Aspas buscam a frase exata: `"pessoa com deficiência"`
  - `OR` busca alternativas: `(Cotia OR Itapevi OR Barueri)`
  - `when:2d` limita aos últimos 2 dias (`when:7d` = 7 dias, `when:30d` = 30 dias)

Filtros (aplicados ao **título** da notícia, sempre como palavra inteira):

- **`palavras_relevantes`** (por grupo): a notícia só entra se o título tiver
  pelo menos um destes termos de impacto PCD. É o filtro principal de
  relevância — se notícia boa estiver sendo descartada, adicione termos aqui
- **`filtro_titulo`** (por grupo): exige uma destas palavras no título — usado
  no grupo regional com os nomes das cidades (~30km de Cotia)
- **`bloquear_titulo`** (por grupo) e **`bloquear_titulo_global`**: lixeira —
  título com qualquer um destes termos é descartado (clickbait, entretenimento)
- **`bloquear_fontes`** (global): bloqueia portais inteiros pelo nome da fonte
  (como aparece na página). Útil para sites caça-clique recorrentes
- **`max_por_grupo`**: máximo de notícias exibidas por grupo

O coletor também descarta automaticamente notícias **quase repetidas**
(mesma matéria publicada por fontes diferentes com 70%+ das palavras iguais).

Após editar, rode `python atualizar.py` (ou o atalho) e veja o resultado.

## Publicação automática (GitHub Pages)

A página da equipe é publicada pelo GitHub Actions — definido em
`.github/workflows/atualizar.yml`:

- **Todo dia às 10:00 UTC (~7h de Brasília)** o GitHub roda a coleta na nuvem
  e republica a página. Não depende de nenhum computador ligado.
- **A cada `git push`** na branch `main` ela também é republicada — ou seja,
  mudou um filtro no `config.json`, é só commitar e enviar que o site atualiza.
- **Atualização manual**: em github.com/Leo-JC7/mr-noticias → aba *Actions* →
  *Atualizar notícias* → botão *Run workflow*.

Para mudar o horário, edite a linha `cron:` do workflow (sempre em UTC).

Fluxo para publicar uma alteração:

```powershell
git add -A
git commit -m "Descreva a mudança aqui"
git push
```

## Observações

- O computador precisa estar conectado à internet na hora da coleta.
- Os links levam ao Google News, que redireciona para o site original da notícia.
- Notícias locais são mais raras — é normal o grupo regional variar de tamanho.
- Cidades do grupo regional (~30km de Cotia): Cotia, Caucaia do Alto, Vargem
  Grande Paulista, Itapevi, Jandira, Barueri, Carapicuíba, Osasco, Embu das
  Artes, Embu-Guaçu, Taboão da Serra, Itapecerica da Serra, Santana de
  Parnaíba, Pirapora do Bom Jesus, São Roque e Ibiúna.
