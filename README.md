# Bonds Desk — US2Y • US10Y • US30Y  
### *Visão institucional — Chief Investment Office (CIO)*

Este repositório contém o pipeline oficial do **Bonds Desk**, responsável por coletar diariamente as séries de Treasuries dos EUA (2 anos, 10 anos e 30 anos), gerar relatórios institucionais via LLM e produzir gráficos completos da curva de juros para uso em decisões de portfólio, risk management e comunicação interna.

O tom deste documento é operacional, direto e alinhado à visão do **CIO (Chief Investment Office)**.

---

## 📌 Objetivo

O objetivo central é manter um **stream contínuo e automatizado** de:

- Coleta e atualização de séries de juros (2Y, 10Y, 30Y)
- Relatórios diários com análise macro (LLM com fallback)
- Gráficos FULL e últimos 12 meses (12M)
- Indicadores institucionais de curva:
  - Spreads (10–2, 30–2, 30–10)
  - Volatilidade realizada
  - Z-Score rolling
  - Butterfly (curvatura)
- Entrega automatizada via Telegram

Tudo isso com **trava diária**, **contadores persistentes** e **logs rastreáveis**, garantindo estabilidade operacional.

---

## 📁 Estrutura do Projeto

```txt
scripts/
  bonds/
    us2y_daily.py
    us10y_daily.py
    us30y_daily.py
    us2y_daily_llm.py
    us10y_daily_llm.py
    us30y_daily_llm.py
    plot_yields_separate.py
    plot_spreads.py
    plot_volatility.py
    plot_zscore.py
    plot_butterfly.py
pipelines/
  bonds/
    us2y_daily.csv
    us10y_daily.csv
    us30y_daily.csv
    yields_full.png
    yields_full_12m.png
    spreads.png
    spreads_12m.png
    volatility_30d.png
    zscore_252d.png
    butterfly.png
data/
  sentinels/
    us2y_daily.sent
    us10y_daily.sent
    us30y_daily.sent
.github/
  workflows/
    bonds_daily.yml
requirements.txt
