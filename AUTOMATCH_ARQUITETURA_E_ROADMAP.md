# AutoMatch Career — Arquitetura & Roadmap

Documento de referência técnica do projeto. Cobre como o sistema é estruturado hoje, os contratos entre módulos, os problemas conhecidos, e a ordem de trabalho para sair de "MVP com dados fictícios" para "pipeline funcional de verdade".

---

## 1. Visão geral

O AutoMatch Career é um pipeline batch, disparado semanalmente via GitHub Actions, que:

1. Busca vagas tech em plataformas configuradas
2. Calcula compatibilidade contra um perfil declarado em `config.py`
3. Filtra vagas com match ≥ 40%
4. Persiste no Notion como dashboard central, evitando duplicatas

Não há servidor, API, nem interface — é um script Python que roda, produz efeito colateral (linhas no Notion) e termina. Isso é uma decisão de arquitetura válida para o escopo atual: simplicidade > infraestrutura.

## 2. Componentes e contratos

| Módulo | Responsabilidade | Depende de | Contrato de saída |
|---|---|---|---|
| `config.py` | Fonte única de verdade do perfil, pesos e plataformas | — | `Config` (classe com atributos estáticos) |
| `scrapers.py` | Busca vagas cruas | `config.py` | `list[dict]` com chaves `title, company, description, url, platform, date_posted` |
| `matcher.py` | Calcula score de compatibilidade 0–100 | `config.py` | `dict` com `score, matches, level` |
| `notion_client.py` | CRUD no Notion, dedup | env vars `NOTION_TOKEN`, `NOTION_DATABASE_ID` | `bool`/`int` (sucesso, contagem) |
| `main.py` | Orquestra o pipeline, aplica filtro de corte, gera relatório | todos acima | exit code 0/1 |

O acoplamento é por **dicionário posicional** (chaves de string, sem schema formal) — funciona, mas qualquer typo de chave falha silenciosamente em runtime em vez de na hora de escrever o código. Vale considerar um `dataclass` ou `TypedDict` para `Vaga` conforme o projeto cresce (ver §4).

## 3. Fluxo de execução

GitHub Actions (segunda, 9h) → `main.py` → testa conexão Notion → `scrapers.buscar_todas_vagas()` → `matcher.calculate_match()` por vaga → filtro de corte 40% → `notion.salvar_lote_vagas()` → relatório no log.

## 4. Problemas encontrados na leitura do código (bugs reais, não hipotéticos)

Estes não são melhorias — são coisas que quebram ou mentem sobre o que o sistema faz hoje:

1. **`notion_client.py` usa `time.sleep(0.5)` em `salvar_lote_vagas()` mas nunca importa `time`.** Isso vai lançar `NameError` na primeira execução em lote real (fora do happy path de 0 vagas). Bloqueador puro.
2. **`scrapers.buscar_vagas_linkedin_simplificado()` retorna 4 vagas fixas, hardcoded no código.** Não é scraping — é um mock permanente disfarçado de fonte de dados. O README chama isso de "Busca Automática - Vagas de múltiplas plataformas", o que não é verdade hoje.
3. **`scrapers.buscar_vagas_github()` chama `jobs.github.com/positions.json`.** Esse serviço (GitHub Jobs) foi descontinuado pelo GitHub em 2018. O endpoint não existe mais — a chamada sempre vai cair no `except` e retornar lista vazia, silenciosamente.
4. **Resultado direto de (2) + (3): o pipeline nunca encontra uma vaga real.** Toda execução salva as mesmas 4 vagas fictícias no Notion, sempre. Este é o problema mais importante do projeto — o resto do sistema (matching, Notion, agendamento) funciona sobre dados que não existem no mundo real.
5. **`config.py` lista `programathor` em `PLATAFORMAS_VAGAS`** mas não existe nenhum scraper para essa plataforma — configuração morta.
6. **`matcher.py`: os pesos em `SKILL_WEIGHTS` somam 1.0 exatamente, mas o bônus de keywords (`+0.05` por keyword) pode empurrar o score teórico acima de 100% antes do `min()` — funciona por causa do clamp, mas mascara que a escala não é bem calibrada.** Baixo risco, mas vale revisar quando o matcher for retrabalhado.

## 5. Funcionalidades ordenadas por importância para o AutoMatch **funcionar de fato**

Critério de ordenação: impacto no pipeline produzir um resultado real e confiável, não esforço de implementação.

1. **Corrigir o `NameError` do `time` em `notion_client.py`** — bloqueador literal, sem isso o salvamento em lote quebra.
2. **Substituir as fontes de vaga fictícias/mortas por fontes reais** — este é o item que mais importa. Sem vagas reais entrando, todo o resto (matching, Notion, agendamento) processa lixo. Fontes recomendadas, com API JSON pública, gratuita, sem necessidade de chave: RemoteOK (`remoteok.com/api`) e Arbeitnow (`arbeitnow.com/api/job-board-api`). Ambas cobrem vagas remotas tech, o que bate com `localizacao: remoto` no seu perfil.
3. **Validação de configuração e tratamento de erro no startup** — hoje, se `NOTION_TOKEN` não existir, o erro só aparece na tentativa de request. Falhar cedo, com mensagem clara, evita debugging perdido.
4. **Robustez do matcher** — hoje é correspondência literal de substring. Pelo menos stemming simples ou lista de sinônimos mais ampla (hoje só 4 skills têm `variations` mapeadas de 10 no `SKILL_WEIGHTS`) melhora a precisão do score sem mudar a arquitetura.
5. **Dedup e rate limit no Notion** — já existe verificação de duplicata por título+empresa, o que é razoável; vale revisar se falso-negativo (vaga reaparece com título ligeiramente diferente) é aceitável por ora.
6. **Plataformas adicionais reais** (Programathor, Indeed via API não-oficial, etc.) — só depois que a fonte principal for confiável.
7. **Funcionalidades do README "Próximas"** (notificações por email, dashboard de analytics, auto-aplicação) — valor real, mas dependem de tudo acima estar sólido primeiro.

## 6. Débito técnico não bloqueante (registrar, não agir agora)

- Sem testes automatizados apesar de `pytest` estar no `requirements.txt`.
- Sem logging estruturado — tudo é `print()`, o que dificulta debug em produção via GitHub Actions.
- Sem schema formal para o dicionário `vaga` (ver §2).

---

**Próximo passo combinado:** atacar os itens 1 e 2 da seção 5 agora — são o que torna o sistema funcional de verdade em vez de decorativo.
