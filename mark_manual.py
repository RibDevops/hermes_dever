#!/usr/bin/env python3
"""
Script auxiliar para marcar/desmarcar eventos manualmente via terminal.
Útil se quiser limpar o banco ou marcar algo sem usar o botão do Telegram.
"""

import sys
import json
import database


def show_pending():
    """Mostra eventos pendentes lendo o JSON gerado."""
    try:
        with open("agenda_events_by_date.json", "r", encoding="utf-8") as f:
            agenda = json.load(f)
    except FileNotFoundError:
        print("agenda_events_by_date.json não encontrado. Rode extract_details.py primeiro.")
        return

    idx = 1
    mapping = {}
    for date_str in sorted(agenda.keys()):
        for ev in agenda[date_str]:
            print(f"{idx:3d}. [{date_str}] {ev['time']} — {ev['title']}")
            mapping[idx] = ev["id"]
            idx += 1
    return mapping


def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python3 mark_manual.py list          → lista pendentes")
        print("  python3 mark_manual.py done <n>      → marca como concluído pelo número")
        print("  python3 mark_manual.py undo <id>     → desfaz conclusão pelo UUID")
        print("  python3 mark_manual.py completed     → mostra últimos concluídos")
        return

    cmd = sys.argv[1]

    if cmd == "list":
        mapping = show_pending()
        if mapping:
            print(f"\nTotal: {len(mapping)} pendentes.")

    elif cmd == "done":
        if len(sys.argv) < 3:
            print("Informe o número do evento. Use 'list' primeiro.")
            return
        mapping = show_pending()
        if not mapping:
            return
        try:
            n = int(sys.argv[2])
            eid = mapping.get(n)
        except ValueError:
            # pode ser UUID direto
            eid = sys.argv[2]

        if database.mark_completed(eid):
            print(f"✅ Concluído: {eid}")
        else:
            print(f"Já estava concluído: {eid}")

    elif cmd == "undo":
        if len(sys.argv) < 3:
            print("Informe o UUID do evento.")
            return
        eid = sys.argv[2]
        if database.uncomplete(eid):
            print(f"↩️  Desfeito: {eid}")
        else:
            print(f"Não estava concluído: {eid}")

    elif cmd == "completed":
        rows = database.list_completed(20)
        if not rows:
            print("Nenhum evento concluído ainda.")
            return
        for r in rows:
            print(f"{r['completed_at']} — {r['event_id']}")

    else:
        print("Comando desconhecido.")


if __name__ == "__main__":
    main()
