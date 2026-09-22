#!/usr/bin/env python3
"""Test script para usar Scrapling DynamicFetcher no portal Bernoulli."""
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Credenciais - verificar no .env ou ambiente
BERNOULLI_USER = os.getenv("BERNOULLI_USER", "")
BERNOULLI_PASS = os.getenv("BERNOULLI_PASS", "")

try:
    from scrapling.fetchers import DynamicFetcher, DynamicSession
except ImportError:  # Dependência opcional para teste manual com navegador.
    DynamicFetcher = DynamicSession = None

def test_login_and_extract():
    """Testa login e extração no portal mb4.bernoulli.com.br"""
    if DynamicSession is None:
        raise RuntimeError(
            "Instale a dependência opcional 'scrapling' para executar este teste"
        )
    
    # Usar DynamicSession para manter cookies e estado entre requests
    with DynamicSession(
        headless=False,  # headful para debug inicial
        solve_cloudflare=True,  # Essential para Cloudflare
        viewport={"width": 1920, "height": 1080},
    ) as session:
        
        print("🌐 Navegando para página de login...")
        # Acessar página de calendário
        page = session.fetch(
            "https://mb4.bernoulli.com.br/comunicacao/calendario",
            timeout=60000,
        )
        
        print(f"✅ Título da página: {page.title()[:80]}")
        
        # Procurar botões event-chip
        print("\n🔍 Procurando botões event-chip...")
        buttons = page.css(".event-chip", adaptive=True)
        
        print(f"   Encontrados {len(buttons)} botões event-chip")
        
        # Extrair informações de cada botão
        events = []
        for i, button in enumerate(buttons[:3], 1):  # Testar com os 3 primeiros
            try:
                # Texto do botão
                text = button.text_content()
                # Tooltip/description (atribut title ou aria-label)
                tooltip = button.get("title", "") or button.get("aria-label", "")
                # Tentar clicar e capturar link
                # button.click()  # Descomentar para testar click real
                
                events.append({
                    "index": i,
                    "text": text[:50] if text else "N/A",
                    "tooltip": tooltip[:80] if tooltip else "N/A",
                })
                print(f"   {i}. Texto: '{text[:50]}' | Tooltip: '{tooltip[:60]}'")
                
            except Exception as e:
                print(f"   {i}. Erro: {e}")
        
        # Salvar resultados
        result = {
            "page_title": page.title(),
            "events_sample": events,
            "url": "https://mb4.bernoulli.com.br/comunicacao/calendario",
        }
        
        with open("agenda_details_test.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Resultados salvos em: agenda_details_test.json")
        return result

if __name__ == "__main__":
    result = test_login_and_extract()
    print("\n✅ Teste concluído!")
