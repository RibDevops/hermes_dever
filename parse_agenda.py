#!/usr/bin/env python3
"""
parse_agenda.py
    Extracts events from the saved agenda HTML and emits JSON.
    - Date   : taken from the nearest <a class="semana-day"> ancestor (data-date attribute)
    - Title  : text of the child span.chip-title (or the button's own text)
    - Desc   : tooltip attribute (often a longer description)
    The result is a list of dicts:
        [
            {"date": "2026-08-28", "title": "Gabarito - AV1 - Geografia", "desc": "..."},
            ...
        ]
"""

import sys
import json
from pathlib import Path
from bs4 import BeautifulSoup

def _load_html(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _extract_events(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    events = []

    # Cada evento está em um <button class="event-chip">               
    for btn in soup.select("button.event-chip"):
        # 1️⃣ Obter a data da semana que contém esse botão
        # O botão está dentro de <a.class="semana-day"> que tem data-date
        semana_day = btn.find_parent("a", class_="semana-day")
        date_str = semana_day["data-date"] if semana_day and semana_day.has_attr("data-date") else ""

        # 2️⃣ Título – prefere o <span class="chip-title">, senão o texto bruto do botão
        title_el = btn.select_one("span.chip-title")
        title = title_el.get_text(strip=True) if title_el else btn.get_text(strip=True)

        # 3️⃣ Descrição – atributo tooltip (geralmente mais detalhado)
        desc = btn.get("tooltip", "")

        events.append({
            "date":   date_str,
            "title":  title,
            "desc":   desc,
        })
    return events

def main():
    if len(sys.argv) < 2:
        print("Uso: parse_agenda.py <caminho/do/calendario.html> > agenda.json", file=sys.stderr)
        sys.exit(1)

    html_path = Path(sys.argv[1])
    if not html_path.is_file():
        print(f"Arquivo não encontrado: {html_path}", file=sys.stderr)
        sys.exit(2)

    html = _load_html(html_path)
    events = _extract_events(html)

    json.dump(events, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")

if __name__ == "__main__":
    main()