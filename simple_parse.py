#!/usr/bin/env python3
import sys, json, re, pathlib

def load_html(path):
    # path is a string; convert to Path
    p = pathlib.Path(path)
    return p.read_text(encoding='utf-8')

html = load_html(sys.argv[1])

# 1) Extract all data-date values from <a class="semana-day">
dates = re.findall(r'<a[^>]*class="semana-day"[^>]*data-date="([^"]+)"', html)

# 2) Extract all <button class="event-chip">...</button> blocks
button_blocks = re.findall(r'<button[^>]*class="event-chip"[^>]*>(.*?)</button>', html, re.DOTALL)

events = []
for i, block in enumerate(button_blocks):
    if i >= len(dates):
        break
    date = dates[i]

    # Extract title from <span class="chip-title">
    title_match = re.search(r'<span class="chip-title">([^<]+)</span>', block)
    title = title_match.group(1).strip() if title_match else block.strip()

    # Extract tooltip as description
    desc_match = re.search(r'tooltip="([^"]*)"', block)
    desc = desc_match.group(1) if desc_match else ""

    events.append({
        "date": date,
        "title": title,
        "desc": desc,
    })

json.dump(events, sys.stdout, ensure_ascii=False, indent=2)
sys.stdout.write("\n")