"""Shared factual report prompt and output guard."""
def build_prompt(series_name, factual_context, macro_context_text=""):
    system=("Você é analista de renda fixa. Escreva em português brasileiro. "
            "Não invente notícias, dados macro, posicionamento, consenso institucional ou causalidade. "
            "Separe fatos fornecidos, interpretação e cenários hipotéticos. Cite a data dos dados.")
    user=f"""Relatório executivo diário — {series_name}
Use somente os dados abaixo. Se uma informação não estiver presente, declare indisponibilidade.
Organize: (1) leitura factual, (2) movimento e curva, (3) fatores que os dados permitem inferir,
(4) riscos/limitações, (5) cenários hipotéticos, (6) conclusão executiva.

DADOS:
{factual_context}

CONTEXTO:
{macro_context_text}"""
    return system,user

def validate_report(text):
    if not isinstance(text,str) or len(text.strip())<150:
        raise ValueError("LLM report is empty or suspiciously short")
    return text.strip()
