#!/usr/bin/env python3
"""
Script de diagnóstico para descobrir o endpoint correto da API Bernoulli.
Testa várias combinações de URL e mostra qual responde 200 com JSON válido.
"""

import os
import sys
import json

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BERNOULLI_TOKEN", "").strip()
if not TOKEN:
    print("ERRO: defina BERNOULLI_TOKEN no .env")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "User-Agent": "HermesBot/2.0",
}

# Data fixa para teste (intervalo pequeno)
TEST_PARAMS = {
    "startDate": "2026-08-20",
    "endDate": "2026-08-21",
    "page": 1,
    "limit": 10,
    "range": "week",
    "status": "published",
    "grade": "12",
    "class": "109576",
    "profile": "13",
    "school": "1846",
    "ignoreAudience": "false",
    "sortBy": "startDate",
    "sortOrder": "asc",
}

# Variações de endpoint para testar
CANDIDATES = [
    # Base + /api/calendario/events
    "https://mb4.bernoulli.com.br/api/calendario/events",
    # Sem /api
    "https://mb4.bernoulli.com.br/calendario/events",
    # Com /v1/
    "https://mb4.bernoulli.com.br/api/v1/calendario/events",
    "https://mb4.bernoulli.com.br/v1/calendario/events",
    # Com /app/
    "https://mb4.bernoulli.com.br/app/api/calendario/events",
    "https://mb4.bernoulli.com.br/app/calendario/events",
    # Outros subdomínios comuns
    "https://api.bernoulli.com.br/api/calendario/events",
    "https://bernoulli.com.br/api/calendario/events",
    "https://lasalle.bernoulli.com.br/api/calendario/events",
    "https://portal.bernoulli.com.br/api/calendario/events",
]


def test_endpoint(url: str) -> dict:
    """Testa um endpoint e retorna resumo."""
    try:
        resp = requests.get(url, headers=HEADERS, params=TEST_PARAMS, timeout=15)
        status = resp.status_code
        content_type = resp.headers.get("Content-Type", "")

        # Tenta parsear JSON
        is_json = False
        has_data = False
        error_msg = ""
        if status == 200 and "json" in content_type:
            try:
                data = resp.json()
                is_json = True
                has_data = bool(data.get("data"))
            except Exception as e:
                error_msg = str(e)
        elif status != 200:
            error_msg = resp.text[:200]

        return {
            "url": url,
            "status": status,
            "is_json": is_json,
            "has_data": has_data,
            "error": error_msg,
        }
    except requests.RequestException as exc:
        return {
            "url": url,
            "status": 0,
            "is_json": False,
            "has_data": False,
            "error": str(exc),
        }


def main():
    print("=" * 70)
    print("DIAGNÓSTICO DE ENDPOINTS DA API BERNOULLI")
    print("=" * 70)
    print()

    results = []
    for url in CANDIDATES:
        print(f"Testando: {url}")
        result = test_endpoint(url)
        results.append(result)
        status_str = str(result["status"]) if result["status"] else "ERR"
        ok_str = "✅ FUNCIONA!" if result["has_data"] else "❌"
        print(f"  → Status: {status_str} | JSON: {result['is_json']} | Data: {result['has_data']} {ok_str}")
        if result["error"] and not result["has_data"]:
            print(f"     Erro: {result['error'][:120]}")
        print()

    # Resumo
    working = [r for r in results if r["has_data"]]
    print("=" * 70)
    print("RESUMO")
    print("=" * 70)
    if working:
        print(f"\n✅ Endpoint(s) que funcionaram:")
        for r in working:
            print(f"   {r['url']}")
    else:
        print("\n❌ Nenhum endpoint respondeu com dados.")
        print("\nPossíveis causas:")
        print("  1. O token (BERNOULLI_TOKEN) está expirado ou inválido → teste no Burp")
        print("  2. Falta algum header obrigatório (Referer, Origin, Cookie)")
        print("  3. A URL base é diferente de todas as testadas")
        print("  4. A API requer POST em vez de GET")
        print("\n👉 Cole aqui a URL EXATA do Burp (linha do GET) para eu ajustar.")


if __name__ == "__main__":
    main()
