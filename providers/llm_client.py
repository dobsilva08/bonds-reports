#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente unificado de LLM com fallback:
- PIAPI (padrão)
- Groq
- OpenAI
- DeepSeek

Uso típico:
    from providers.llm_client import LLMClient

    llm = LLMClient()  # ou LLMClient(provider="groq")
    texto = llm.generate(
        system_prompt="Você é um analista...",
        user_prompt="Faça um relatório...",
        temperature=0.3,
        max_tokens=1600,
    )
"""

import os
import json
import time
from typing import List, Dict, Any, Optional

import requests

# Imports opcionais (só usados se as libs estiverem instaladas)
try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None

try:
    from openai import OpenAI as OpenAIClient
except Exception:  # pragma: no cover
    OpenAIClient = None


class LLMClient:
    """
    Abstrai o uso de múltiplos provedores (PIAPI, Groq, OpenAI, DeepSeek)
    com retry simples e fallback configurável via variáveis de ambiente.

    Variáveis importantes:
      - LLM_PROVIDER          -> provider primário (piapi | groq | openai | deepseek)
      - LLM_FALLBACK_ORDER    -> ordem de fallback, ex: "piapi,groq,openai,deepseek"
      - PIAPI_API_KEY, PIAPI_MODEL
      - GROQ_API_KEY, GROQ_MODEL
      - OPENAI_API_KEY, OPENAI_MODEL
      - DEEPSEEK_API_KEY, DEEPSEEK_MODEL
    """

    def __init__(self, provider: Optional[str] = None):
        self.env_provider = (provider or os.environ.get("LLM_PROVIDER") or "piapi").strip().lower()

        fallback_env = os.environ.get("LLM_FALLBACK_ORDER", "piapi,groq,openai,deepseek")
        self.fallback_order: List[str] = [
            p.strip().lower() for p in fallback_env.split(",") if p.strip()
        ]

        # garante que o provider principal vem primeiro
        if self.env_provider in self.fallback_order:
            self.fallback_order.remove(self.env_provider)
        self.fallback_order.insert(0, self.env_provider)

        self.active_provider: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Interface pública
    # ------------------------------------------------------------------ #
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1600,
    ) -> str:
        """
        Gera texto usando o provider principal + fallback.

        Retorna:
          - texto (string)
        Lança RuntimeError se todos os providers falharem.
        """
        last_error: Optional[Exception] = None

        for provider in self.fallback_order:
            provider = provider.strip().lower()
            if not provider:
                continue

            try:
                if provider == "piapi":
                    out = self._call_piapi(system_prompt, user_prompt, temperature, max_tokens)
                elif provider == "groq":
                    out = self._call_groq(system_prompt, user_prompt, temperature, max_tokens)
                elif provider == "openai":
                    out = self._call_openai(system_prompt, user_prompt, temperature, max_tokens)
                elif provider == "deepseek":
                    out = self._call_deepseek(system_prompt, user_prompt, temperature, max_tokens)
                else:
                    continue

                self.active_provider = provider
                return out

            except Exception as e:  # pragma: no cover
                last_error = e
                print(f"[LLMClient] Erro ao usar provider '{provider}': {e}")
                # tenta o próximo

        raise RuntimeError(f"Todos os providers falharam. Último erro: {last_error}")

    # ------------------------------------------------------------------ #
    # Providers individuais
    # ------------------------------------------------------------------ #
    def _build_messages(self, system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _call_piapi(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        api_key = os.environ.get("PIAPI_API_KEY")
        if not api_key:
            raise RuntimeError("PIAPI_API_KEY não configurada.")

        model = os.environ.get("PIAPI_MODEL", "gpt-4o-mini")
        base_url = os.environ.get("PIAPI_BASE_URL", "https://api.piapi.ai/v1/chat/completions")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": self._build_messages(system_prompt, user_prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(base_url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # assume formato OpenAI-like
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Resposta inesperada da PIAPI: {data}") from e

    def _call_groq(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if Groq is None:
            raise RuntimeError("Biblioteca 'groq' não instalada.")

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY não configurada.")

        model = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")

        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=self._build_messages(system_prompt, user_prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            return resp.choices[0].message.content
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Resposta inesperada do Groq: {resp}") from e

    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if OpenAIClient is None:
            raise RuntimeError("Biblioteca 'openai' não instalada (OpenAI v1).")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não configurada.")

        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

        client = OpenAIClient(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=self._build_messages(system_prompt, user_prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            return resp.choices[0].message.content
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Resposta inesperada do OpenAI: {resp}") from e

    def _call_deepseek(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        DeepSeek usa um endpoint compatível com OpenAI em muitos setups.
        Aqui usamos uma chamada HTTP estilo OpenAI; ajuste se sua conta exigir outro formato.
        """
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY não configurada.")

        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": self._build_messages(system_prompt, user_prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(base_url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Resposta inesperada do DeepSeek: {data}") from e
