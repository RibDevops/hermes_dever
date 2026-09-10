#!/usr/bin/env python3
"""
Script Playwright para extrair agenda do portal mb4.bernoulli.com.br
- Faz login no portal
- Encontra botões <button class="event-chip">
- Extrai tooltip/description
- Clica em cada botão para abrir popup
- Captura primeiro link contendo "pdf" ou "download"
- Salva como agenda_details.json com: date, title, description, download_url
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

from playwright.sync_api import sync_playwright


# ===================== CONFIGURAÇÕES =====================

# URLs
PORTAL_URL = "https://mb4.bernoulli.com.br/comunicacao/calendario"
LOGIN_URL = "https://mb4.bernoulli.com.br/login"

# Seletores (robustos - matching parcial/contém)
LOGIN_INPUT_XPATH = "//input[contains(@placeholder, 'Login')]"
LOGIN_PASSWORD_XPATH = "//input[contains(@placeholder, 'Senha')]"
LOGIN_BUTTON_SELECTOR = "button.IButton.fill--bernoulli.pill"
EVENT_CHIP_SELECTOR = "//button[contains(@class, 'event-chip')]"
TOOLTIP_ATTRIBUTE = "title"
POSSIBLE_POPUP_SELECTORS = [
    "//div[contains(@class, 'popup')]",
    "//div[contains(@class, 'modal')]",
    "//div[contains(@class, 'event-detail')]",
]
PDF_DOWNLOAD_PATTERN = r"(?:pdf|download)[^\s]{0,200}"


# ===================== BUSINESS LOGIC =====================

def extract_download_link_from_page(page):
    """Procurar primeiro link com pdf/download na página atual."""
    try:
        links = page.query_selector_all("a[href]")
        for link in links:
            href = link.get_attribute("href") or ""
            text = (link.inner_text() or "").lower()
            if re.search(PDF_DOWNLOAD_PATTERN, href, re.IGNORECASE) or re.search(
                PDF_DOWNLOAD_PATTERN, text, re.IGNORECASE
            ):
                if href.startswith("/"):
                    href = f"https://mb4.bernoulli.com.br{href}"
                elif not href.startswith("http"):
                    continue
                return href
        return None
    except Exception as e:
        print(f"   ⚠️ Erro ao extrair link: {e}")
        return None


def find_popup_container(page):
    """Tentar encontrar container do popup após clicar em event-chip."""
    for sel in POSSIBLE_POPUP_SELECTORS:
        try:
            containers = page.query_selector_all(sel)
            if containers:
                return containers[0]
        except Exception:
            continue
    return None


def extract_event_info(button):
    """Extrair texto e tooltip de um botão event-chip."""
    info = {"text": "", "tooltip": ""}

    try:
        # Texto do botão
        info["text"] = button.inner_text() or ""
    except Exception:
        pass

    try:
        # Tooltip (atributo title)
        info["tooltip"] = button.get_attribute(TOOLTIP_ATTRIBUTE) or ""
    except Exception:
        pass

    return info


def try_close_popup(page):
    """Tentar fechar popup aberto."""
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    try:
        page.click("body", button="right")
    except Exception:
        pass


def main():
    resultados = []

    # Credenciais - tentar .env primeiro, depois stdin
    login = os.getenv("MB4_LOGIN") or os.getenv("BERNOULLI_LOGIN") or ""
    senha = os.getenv("MB4_SENHA") or os.getenv("BERNOULLI_SENHA") or ""

    if not login or not senha:
        print("⚠️  Credenciais não encontradas em variáveis de ambiente.")
        print("   Defina MB4_LOGIN/MB4_SENHA ou BERNOULLI_LOGIN/BERNOULLI_SENHA")
        print("   Ou edite o script e preencha LOGIN_AQUI / SENAHA_AQUI")
        # Fallback: pedir input (não ideal para cron, mas OK para debug)
        login = input("🔑 Login: ") or login
        senha = input("🔒 Senha: ") or senha

    print("=" * 60)
    print("Extração de Agenda - mb4.bernoulli.com.br")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headful para debug inicial
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        try:
            # --- Etapa 1: Acessar login ---
            print("\n🔐 Etapa 1: Acessando página de login...")
            page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)

            # --- Etapa 2: Preencher formulário de login ---
            print("   Preenchendo login e senha...")
            page.locator(LOGIN_INPUT_XPATH).fill(login)
            page.locator(LOGIN_PASSWORD_XPATH).fill(senha)

            # --- Etapa 3: Clicar em login (via JS para contornar disabled) ---
            print("   Clicando em login...")
            page.wait_for_timeout(2000)
            page.evaluate(
                """() => {
                    const btn = document.querySelector('button.IButton.fill--bernoulli.pill');
                    if (btn) btn.click();
                }"""
            )
            page.wait_for_load_state("networkidle", timeout=60000)

            # --- Etapa 4: Navegar para calendário ---
            print("\n📅 Etapa 2: Acessando calendário...")
            page.goto(PORTAL_URL, wait_until="networkidle", timeout=60000)

            # --- Etapa 5: Encontrar botões event-chip ---
            print("🔍 Etapa 3: Procurando botões event-chip...")
            buttons = page.query_selector_all(EVENT_CHIP_SELECTOR)

            print(f"   ✅ Encontrados {len(buttons)} botões event-chip")

            if len(buttons) == 0:
                print("   ⚠️ Nenhum botão event-chip encontrado.")
                print("   📋 Mostrando todos os buttons da página:")
                all_buttons = page.query_selector_all("button")
                for i, btn in enumerate(all_buttons[:10]):
                    text = btn.inner_text()[:50] if btn.inner_text() else ""
                    cls = btn.get_attribute("class") or ""
                    print(f"     {i+1}. text='{text}' class='{cls[:50]}'")
                browser.close()
                return

            # --- Etapa 6: Processar cada botão ---
            for idx, button in enumerate(buttons, 1):
                try:
                    # Extrair info do botão
                    info = extract_event_info(button)
                    button_text = info["text"].strip()
                    tooltip = info["tooltip"].strip()

                    if not button_text and not tooltip:
                        print(f"   {idx}. ⚠️ Botão {idx} sem texto/description - pulando")
                        try_close_popup(page)
                        continue

                    print(
                        f"   {idx}. Processando: text='{button_text[:50]}' tooltip='{tooltip[:50]}'"
                    )

                    # --- Clicar no botão ---
                    print(f"   {idx}. Clicando em event-chip...")
                    button.click()
                    page.wait_for_timeout(2000)  # Wait popup aparecer

                    # --- Procurar popup ---
                    popup_container = find_popup_container(page)
                    popup_found = popup_container is not None

                    if not popup_found:
                        print(f"   {idx}. ⚠️ Popup não encontrado - tentando URL atual")
                        download_url = extract_download_link_from_page(page)
                        resultado = {
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "title": button_text or f"Evento {idx}",
                            "description": tooltip or "",
                            "download_url": download_url or "",
                        }
                        resultados.append(resultado)
                        try_close_popup(page)
                        page.wait_for_timeout(500)
                        continue

                    # --- Extrair link PDF/download do popup ---
                    download_url = None

                    # Método 1: Links dentro do popup
                    if popup_container:
                        links_no_popup = popup_container.query_selector_all("a[href]")
                        for link in links_no_popup:
                            href = link.get_attribute("href") or ""
                            text = (link.inner_text() or "").lower()
                            if re.search(PDF_DOWNLOAD_PATTERN, href, re.IGNORECASE) or re.search(
                                PDF_DOWNLOAD_PATTERN, text, re.IGNORECASE
                            ):
                                if href.startswith("/"):
                                    href = f"https://mb4.bernoulli.com.br{href}"
                                elif not href.startswith("http"):
                                    continue
                                download_url = href
                                print(
                                    f"   {idx}. ✅ Link PDF/download encontrado no popup"
                                )
                                break

                    # Método 2: Procurar na página toda
                    if not download_url:
                        download_url = extract_download_link_from_page(page)

                    # --- Salvar resultado ---
                    resultado = {
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "title": button_text or f"Evento {idx}",
                        "description": tooltip or "",
                        "download_url": download_url or "",
                    }
                    resultados.append(resultado)

                    # Fechar popup
                    print(f"   {idx}. Fechando popup...")
                    try_close_popup(page)
                    page.wait_for_timeout(500)

                except Exception as e:
                    print(f"   {idx}. ❌ Erro ao processar botão {idx}: {e}")
                    try_close_popup(page)
                    continue

        except Exception as e:
            print(f"\n❌ Erro crítico durante execução: {e}")
            import traceback

            traceback.print_exc()
        finally:
            # --- Etapa 7: Salvar resultados ---
            print(f"\n💾 Salvando {len(resultados)} eventos em: agenda_details.json...")
            with open("agenda_details.json", "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2)

            print(f"✅ Concluído! Arquivo salvo em: agenda_details.json")
            print(f"   Total de eventos extraídos: {len(resultados)}")

            # Fechar navegador
            browser.close()


if __name__ == "__main__":
    main()