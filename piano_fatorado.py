# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║              PIANO FATORADO — Analisador Musical            ║
║      Sonificação por Fatoração Prima de Teclas do Piano     ║
╚══════════════════════════════════════════════════════════════╝

Uso:
    python piano_fatorado.py <arquivo.musicxml ou arquivo.mxl>
    python piano_fatorado.py   (sem argumentos = abre diálogo para selecionar arquivo)
"""

import xml.etree.ElementTree as ET
import zipfile
import sys
import os
import io
from datetime import datetime
from collections import Counter
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

# Tabela de Mapeamento: Tecla do Piano (1-88)
# Tecla 1 = Lá0 (A0) = MIDI 21
# Tecla 88 = Dó8 (C8) = MIDI 108

NOMES_NOTAS_PT: list[str] = [
    "Lá", "Lá#", "Si", "Dó", "Dó#", "Ré",
    "Ré#", "Mi", "Fá", "Fá#", "Sol", "Sol#"
]

# Offset de cada nota dentro da oitava (relativo a C)
STEP_TO_SEMITONE: dict[str, int] = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
}

# Superscripts Unicode para expoentes de fatoração
SUPERSCRIPTS: dict[str, str] = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
}

# Extensões suportadas na busca automática
SUPPORTED_EXTENSIONS: tuple[str, ...] = ('.musicxml', '.musicxml.xml', '.mxl')


def midi_from_pitch(step: str, alter: int, octave: int) -> int:
    """Converte pitch MusicXML (step, alter, octave) para número MIDI."""
    semitone: int = STEP_TO_SEMITONE.get(step, 0)
    return 12 * (octave + 1) + semitone + alter


def midi_to_piano_key(midi_number: int) -> Optional[int]:
    """Converte número MIDI para tecla do piano (1-88). Retorna None se fora do range."""
    key: int = midi_number - 20  # MIDI 21 = tecla 1
    if 1 <= key <= 88:
        return key
    return None


def piano_key_to_note_name(key: int) -> str:
    """Converte tecla do piano (1-88) para nome em português."""
    # Tecla 1 = A0, offset relativo: A=0, A#=1, B=2, C=3, ...
    # Dentro de um ciclo de 12: posições 0-11 mapeiam para NOMES_NOTAS_PT
    idx: int = (key - 1) % 12
    # Calcular oitava: Tecla 1=Lá0, Tecla 4=Dó1, Tecla 16=Dó2...
    # A0 é oitava 0. Após Si0 (tecla 3), vem Dó1 (tecla 4)
    # A oitava muda no Dó (idx=3)
    octave: int = (key - 1) // 12  # base octave group
    note_name: str = NOMES_NOTAS_PT[idx]
    # Ajustar oitava: notas Lá, Lá#, Si pertencem à oitava anterior do grupo
    if idx < 3:  # Lá, Lá#, Si
        real_octave = octave
    else:  # Dó em diante
        real_octave = octave + 1
    return f"{note_name}{real_octave}"


def is_prime(n: int) -> bool:
    """Verifica se n é primo."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i: int = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def prime_factorization(n: int) -> list[int]:
    """Retorna lista de fatores primos (com repetição). Ex: 12 → [2, 2, 3]"""
    if n <= 1:
        return [n]
    factors: list[int] = []
    d: int = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def classify_key(key: int) -> str:
    """Classifica tecla: 'unidade', 'primo' ou 'composto'."""
    if key == 1:
        return 'unidade'
    elif is_prime(key):
        return 'primo'
    else:
        return 'composto'


def parse_musicxml_from_string(xml_string: str) -> tuple[list[dict], str]:
    """Faz parsing do conteúdo MusicXML e retorna lista de notas."""
    root: ET.Element = ET.fromstring(xml_string)
    notes: list[dict] = []

    # Extrair metadados
    title: str = ""
    title_el: Optional[ET.Element] = root.find('.//movement-title')
    if title_el is not None and title_el.text:
        title = title_el.text

    # Iterar por todas as partes e compassos
    for part in root.findall('.//part'):
        part_id: str = part.get('id', '')
        for measure in part.findall('measure'):
            measure_num: str = measure.get('number', '?')
            for note in measure.findall('note'):
                # Pular pausas
                if note.find('rest') is not None:
                    continue

                # Detectar se é parte de um acorde (MusicXML <chord/>)
                is_chord_note: bool = note.find('chord') is not None

                # Verificar tie start/stop em um único loop
                is_tie_stop: bool = False
                is_tie_start: bool = False
                for tie in note.findall('tie'):
                    tie_type: str = tie.get('type', '')
                    if tie_type == 'stop':
                        is_tie_stop = True
                    elif tie_type == 'start':
                        is_tie_start = True

                # Se é APENAS tie stop (sem start), pular
                # Se é tie stop E start ao mesmo tempo, pular também (é nota do meio da ligadura)
                if is_tie_stop:
                    continue

                # Extrair pitch
                pitch: Optional[ET.Element] = note.find('pitch')
                if pitch is None:
                    continue

                step_el: Optional[ET.Element] = pitch.find('step')
                octave_el: Optional[ET.Element] = pitch.find('octave')
                alter_el: Optional[ET.Element] = pitch.find('alter')

                if step_el is None or octave_el is None:
                    continue

                step: str = step_el.text.strip()
                octave: int = int(octave_el.text.strip())
                alter: int = int(float(alter_el.text.strip())) if alter_el is not None else 0

                midi: int = midi_from_pitch(step, alter, octave)
                piano_key: Optional[int] = midi_to_piano_key(midi)

                if piano_key is not None:
                    notes.append({
                        'step': step,
                        'alter': alter,
                        'octave': octave,
                        'midi': midi,
                        'piano_key': piano_key,
                        'measure': measure_num,
                        'part': part_id,
                        'is_chord': is_chord_note
                    })

    return notes, title


def group_notes_into_events(notes: list[dict]) -> list[list[dict]]:
    """Agrupa notas em eventos musicais.

    Em MusicXML, notas com <chord/> são tocadas simultaneamente
    com a nota anterior. Esta função agrupa essas notas em eventos:
    - Evento de nota única: lista com 1 nota
    - Evento de acorde: lista com 2+ notas simultâneas
    """
    if not notes:
        return []
    events: list[list[dict]] = []
    current_event: list[dict] = []
    for note in notes:
        if note.get('is_chord', False):
            current_event.append(note)
        else:
            if current_event:
                events.append(current_event)
            current_event = [note]
    if current_event:
        events.append(current_event)
    return events


def load_musicxml(filepath: str) -> tuple[list[dict], str]:
    """Carrega arquivo .musicxml, .musicxml.xml ou .mxl e retorna notas + título."""
    ext: str = os.path.splitext(filepath)[1].lower()

    if ext == '.mxl':
        with zipfile.ZipFile(filepath, 'r') as zf:
            # Procurar o arquivo XML dentro do ZIP em um único loop
            xml_file: Optional[str] = None
            fallback_file: Optional[str] = None
            for name in zf.namelist():
                if 'META-INF' in name or name.endswith('/'):
                    continue
                if name.endswith('.xml'):
                    xml_file = name
                    break
                if fallback_file is None:
                    fallback_file = name

            if xml_file is None:
                xml_file = fallback_file
            if xml_file is None:
                raise ValueError(f"Nenhum arquivo XML encontrado dentro de {filepath}")

            with zf.open(xml_file) as f:
                xml_content: str = f.read().decode('utf-8')
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            xml_content = f.read()

    return parse_musicxml_from_string(xml_content)


def format_factorization(factors: list[int]) -> str:
    """Formata fatoração com expoentes unicode. Ex: [2,2,3] → '2² × 3'"""
    if not factors:
        return "1"

    counted: Counter = Counter(factors)
    parts: list[str] = []
    for prime in sorted(counted.keys()):
        exp: int = counted[prime]
        if exp == 1:
            parts.append(str(prime))
        else:
            exp_str: str = ''.join(SUPERSCRIPTS[c] for c in str(exp))
            parts.append(f"{prime}{exp_str}")
    return ' × '.join(parts)


def format_factorization_notes(factors: list[int]) -> str:
    """Formata fatoração como notas do piano. Ex: [2,2,3] → 'Lá#0, Lá#0, Si0'"""
    note_names: list[str] = [piano_key_to_note_name(f) for f in factors]
    return ', '.join(note_names)


def generate_report(notes: list[dict], filename: str, title: str = "") -> str:
    """Gera o relatório de análise do Piano Fatorado."""
    lines: list[str] = []

    def add(text: str = "") -> None:
        lines.append(text)

    now: str = datetime.now().strftime("%Y-%m-%d %H:%M")
    basename: str = os.path.basename(filename)

    add("═" * 65)
    add("  PIANO FATORADO — Relatório de Análise")
    if title:
        add(f"  Título: {title}")
    add(f"  Arquivo: {basename}")
    add(f"  Data: {now}")
    add("═" * 65)
    add()

    total: int = len(notes)
    if total == 0:
        add("  ⚠ Nenhuma nota com pitch encontrada no arquivo.")
        add("═" * 65)
        return '\n'.join(lines)

    # ── Cache de fatoração: calcula uma única vez por tecla ──
    keys: list[int] = [n['piano_key'] for n in notes]
    unique_keys: set[int] = set(keys)

    key_cache: dict[int, dict] = {}
    for k in unique_keys:
        cls: str = classify_key(k)
        factors: list[int] = prime_factorization(k) if cls == 'composto' else []
        key_cache[k] = {
            'classification': cls,
            'factors': factors,
        }

    # Classificar cada nota usando cache
    classifications: list[str] = [key_cache[k]['classification'] for k in keys]

    primos: int = classifications.count('primo')
    compostos: int = classifications.count('composto')
    unidades: int = classifications.count('unidade')

    pares: int = sum(1 for k in keys if k % 2 == 0)
    impares: int = sum(1 for k in keys if k % 2 != 0)

    pct = lambda v: f"{v/total*100:.2f}%"

    # Resumo Geral
    add("── RESUMO GERAL " + "─" * 49)
    add(f"  Total de notas analisadas:         {total}")
    add()

    # Range
    key_min: int = min(keys)
    key_max: int = max(keys)
    add("── EXTENSÃO (RANGE) " + "─" * 45)
    add(f"  Tecla mais grave:   {key_min:>3} ({piano_key_to_note_name(key_min)})")
    add(f"  Tecla mais aguda:   {key_max:>3} ({piano_key_to_note_name(key_max)})")
    add(f"  Amplitude:          {key_max - key_min:>3} semitons")
    add()

    # Análise Piano Fatorado
    add("── ANÁLISE PIANO FATORADO " + "─" * 40)
    add(f"  Notas PRIMAS:       {primos:>5}  ({pct(primos):>7})")
    add(f"  Notas COMPOSTAS:    {compostos:>5}  ({pct(compostos):>7})")
    add(f"  Notas UNIDADE (1):  {unidades:>5}  ({pct(unidades):>7})")
    add()

    # Paridade
    add("── PARIDADE " + "─" * 53)
    add(f"  Teclas PARES:       {pares:>5}  ({pct(pares):>7})")
    add(f"  Teclas ÍMPARES:     {impares:>5}  ({pct(impares):>7})")
    add()

    # Distribuição por tecla
    key_counter: Counter = Counter(keys)
    sorted_keys: list[int] = sorted(key_counter.keys())

    add("── DETALHAMENTO POR TECLA " + "─" * 40)
    add(f"  {'Tecla':>5}  {'Nota':<8}  {'Tipo':<10}  {'Fatoração':<30}  {'Qtd':>4}")
    add("  " + "─" * 62)

    for k in sorted_keys:
        nota: str = piano_key_to_note_name(k)
        cached: dict = key_cache[k]
        tipo: str = cached['classification']
        count: int = key_counter[k]

        if tipo == 'unidade':
            fat: str = "1 (silêncio)"
        elif tipo == 'primo':
            fat = f"{k} (primo)"
        else:
            fat = format_factorization(cached['factors'])

        tipo_display: str = tipo.upper()
        add(f"  {k:>5}  {nota:<8}  {tipo_display:<10}  {fat:<30}  {count:>4}×")

    add()

    # Mapa de fatoração em notas
    add("── MAPA DE FATORAÇÃO EM NOTAS " + "─" * 36)

    for k in sorted_keys:
        nota = piano_key_to_note_name(k)
        cached = key_cache[k]
        tipo = cached['classification']
        count = key_counter[k]

        if tipo == 'unidade':
            add(f"  Tecla {k:>2} ({nota:<8}) → SILÊNCIO                          [{count}×]")
        elif tipo == 'primo':
            add(f"  Tecla {k:>2} ({nota:<8}) → toca normalmente (PRIMO)          [{count}×]")
        else:
            notas_fat: str = format_factorization_notes(cached['factors'])
            add(f"  Tecla {k:>2} ({nota:<8}) → {notas_fat:<40} [{count}×]")

    add()

    # Lista cronológica das primeiras 50 notas
    add("── SEQUÊNCIA DE NOTAS (primeiras 50) " + "─" * 28)
    limit: int = min(50, total)
    for i in range(limit):
        n: dict = notes[i]
        k = n['piano_key']
        nota = piano_key_to_note_name(k)
        cached = key_cache[k]
        tipo = cached['classification']

        if tipo == 'primo':
            desc: str = "PRIMO"
        elif tipo == 'unidade':
            desc = "SILÊNCIO"
        else:
            desc = format_factorization(cached['factors'])

        add(f"  {i+1:>3}. Compasso {n['measure']:>3} | Tecla {k:>2} ({nota:<8}) | {desc}")

    if total > limit:
        add(f"  ... e mais {total - limit} notas")

    add()
    add("═" * 65)
    add(f"  Gerado por Piano Fatorado | {now}")
    add("═" * 65)

    return '\n'.join(lines)


def generate_report_chords(events: list[list[dict]], filename: str, title: str = "") -> str:
    """Gera o relatório de análise do Piano Fatorado com tratamento de acordes."""
    lines: list[str] = []

    def add(text: str = "") -> None:
        lines.append(text)

    now: str = datetime.now().strftime("%Y-%m-%d %H:%M")
    basename: str = os.path.basename(filename)

    add("═" * 65)
    add("  PIANO FATORADO — Relatório com Tratamento de Acordes")
    if title:
        add(f"  Título: {title}")
    add(f"  Arquivo: {basename}")
    add(f"  Data: {now}")
    add("═" * 65)
    add()

    total_events: int = len(events)
    if total_events == 0:
        add("  ⚠ Nenhum evento musical encontrado no arquivo.")
        add("═" * 65)
        return '\n'.join(lines)

    # Achatar para contagem total de notas
    all_notes: list[dict] = [n for ev in events for n in ev]
    total_notes: int = len(all_notes)

    solo_events: list[list[dict]] = [ev for ev in events if len(ev) == 1]
    chord_events: list[list[dict]] = [ev for ev in events if len(ev) > 1]

    # ── Cache de fatoração ──
    keys: list[int] = [n['piano_key'] for n in all_notes]
    unique_keys: set[int] = set(keys)

    key_cache: dict[int, dict] = {}
    for k in unique_keys:
        cls: str = classify_key(k)
        factors: list[int] = prime_factorization(k) if cls == 'composto' else []
        key_cache[k] = {
            'classification': cls,
            'factors': factors,
        }

    pct_ev = lambda v: f"{v/total_events*100:.1f}%"
    pct_nt = lambda v: f"{v/total_notes*100:.2f}%"

    # ── RESUMO GERAL ──
    add("── RESUMO GERAL " + "─" * 49)
    add(f"  Total de eventos musicais:     {total_events}")
    add(f"  Total de notas individuais:    {total_notes}")
    add()
    add(f"  Eventos de nota única:         {len(solo_events):>5}  ({pct_ev(len(solo_events)):>6})")
    add(f"  Eventos de acorde:             {len(chord_events):>5}  ({pct_ev(len(chord_events)):>6})")
    if chord_events:
        sizes: list[int] = [len(ev) for ev in chord_events]
        add(f"  Notas em acordes:              {sum(sizes):>5}")
        add(f"  Tamanho médio dos acordes:     {sum(sizes)/len(sizes):>5.1f} notas")
        add(f"  Maior acorde:                  {max(sizes):>5} notas")
    add()

    # ── DISTRIBUIÇÃO POR TAMANHO DE EVENTO ──
    add("── DISTRIBUIÇÃO POR TAMANHO DE EVENTO " + "─" * 28)
    size_counter: Counter = Counter(len(ev) for ev in events)
    for size in sorted(size_counter.keys()):
        count: int = size_counter[size]
        label: str = "nota única" if size == 1 else f"acorde de {size} notas"
        add(f"  {label:<25}  {count:>5}  ({pct_ev(count):>6})")
    add()

    # ── EXTENSÃO ──
    key_min: int = min(keys)
    key_max: int = max(keys)
    add("── EXTENSÃO (RANGE) " + "─" * 45)
    add(f"  Tecla mais grave:   {key_min:>3} ({piano_key_to_note_name(key_min)})")
    add(f"  Tecla mais aguda:   {key_max:>3} ({piano_key_to_note_name(key_max)})")
    add(f"  Amplitude:          {key_max - key_min:>3} semitons")
    add()

    # ── ANÁLISE PIANO FATORADO ──
    classifications: list[str] = [key_cache[k]['classification'] for k in keys]
    primos: int = classifications.count('primo')
    compostos: int = classifications.count('composto')
    unidades: int = classifications.count('unidade')

    add("── ANÁLISE PIANO FATORADO (por nota) " + "─" * 28)
    add(f"  Notas PRIMAS:       {primos:>5}  ({pct_nt(primos):>7})")
    add(f"  Notas COMPOSTAS:    {compostos:>5}  ({pct_nt(compostos):>7})")
    add(f"  Notas UNIDADE (1):  {unidades:>5}  ({pct_nt(unidades):>7})")
    add()

    # ── PARIDADE ──
    pares: int = sum(1 for k in keys if k % 2 == 0)
    impares: int = sum(1 for k in keys if k % 2 != 0)
    add("── PARIDADE " + "─" * 53)
    add(f"  Teclas PARES:       {pares:>5}  ({pct_nt(pares):>7})")
    add(f"  Teclas ÍMPARES:     {impares:>5}  ({pct_nt(impares):>7})")
    add()

    # ── DETALHAMENTO POR TECLA ──
    key_counter: Counter = Counter(keys)
    sorted_keys: list[int] = sorted(key_counter.keys())

    add("── DETALHAMENTO POR TECLA " + "─" * 40)
    add(f"  {'Tecla':>5}  {'Nota':<8}  {'Tipo':<10}  {'Fatoração':<30}  {'Qtd':>4}")
    add("  " + "─" * 62)

    for k in sorted_keys:
        nota: str = piano_key_to_note_name(k)
        cached: dict = key_cache[k]
        tipo: str = cached['classification']
        count = key_counter[k]

        if tipo == 'unidade':
            fat: str = "1 (silêncio)"
        elif tipo == 'primo':
            fat = f"{k} (primo)"
        else:
            fat = format_factorization(cached['factors'])

        add(f"  {k:>5}  {nota:<8}  {tipo.upper():<10}  {fat:<30}  {count:>4}×")
    add()

    # ── MAPA DE FATORAÇÃO EM NOTAS ──
    add("── MAPA DE FATORAÇÃO EM NOTAS " + "─" * 36)
    for k in sorted_keys:
        nota = piano_key_to_note_name(k)
        cached = key_cache[k]
        tipo = cached['classification']
        count = key_counter[k]

        if tipo == 'unidade':
            add(f"  Tecla {k:>2} ({nota:<8}) → SILÊNCIO                          [{count}×]")
        elif tipo == 'primo':
            add(f"  Tecla {k:>2} ({nota:<8}) → toca normalmente (PRIMO)          [{count}×]")
        else:
            notas_fat: str = format_factorization_notes(cached['factors'])
            add(f"  Tecla {k:>2} ({nota:<8}) → {notas_fat:<40} [{count}×]")
    add()

    # ── SEQUÊNCIA DE EVENTOS ──
    add("── SEQUÊNCIA DE EVENTOS (primeiros 50) " + "─" * 27)
    limit: int = min(50, total_events)
    for i in range(limit):
        ev: list[dict] = events[i]
        measure: str = ev[0]['measure']

        if len(ev) == 1:
            # Nota única
            n: dict = ev[0]
            k = n['piano_key']
            nota = piano_key_to_note_name(k)
            cached = key_cache[k]
            tipo = cached['classification']
            if tipo == 'primo':
                desc: str = "PRIMO"
            elif tipo == 'unidade':
                desc = "SILÊNCIO"
            else:
                desc = format_factorization(cached['factors'])
            add(f"  {i+1:>3}. Compasso {measure:>3} | Tecla {k:>2} ({nota:<8}) | {desc}")
        else:
            # Acorde
            add(f"  {i+1:>3}. Compasso {measure:>3} | ♫ ACORDE ({len(ev)} notas):")
            sonified: list[str] = []
            for n in ev:
                k = n['piano_key']
                nota = piano_key_to_note_name(k)
                cached = key_cache[k]
                tipo = cached['classification']

                if tipo == 'primo':
                    desc = "PRIMO"
                    sonified.append(piano_key_to_note_name(k))
                elif tipo == 'unidade':
                    desc = "SILÊNCIO"
                    sonified.append("∅")
                else:
                    desc = format_factorization(cached['factors'])
                    factor_notes = [piano_key_to_note_name(f) for f in cached['factors']]
                    sonified.extend(factor_notes)

                add(f"       │  Tecla {k:>2} ({nota:<8}) | {desc}")
            add(f"       └→ Sonificação: {{{', '.join(sonified)}}}")

    if total_events > limit:
        add(f"  ... e mais {total_events - limit} eventos")

    add()
    add("═" * 65)
    add(f"  Gerado por Piano Fatorado (Acordes) | {now}")
    add("═" * 65)

    return '\n'.join(lines)


def process_file(filepath: str) -> Optional[str]:
    """Processa um arquivo MusicXML/MXL e salva o relatório .txt.

    Retorna o caminho do relatório gerado, ou None em caso de erro.
    """
    if not os.path.exists(filepath):
        print(f"  ✗ Arquivo não encontrado: {filepath}")
        return None

    print(f"  ▶ Processando: {os.path.basename(filepath)}...")

    try:
        notes, title = load_musicxml(filepath)
    except Exception as e:
        print(f"  ✗ Erro ao ler arquivo: {e}")
        return None

    report: str = generate_report(notes, filepath, title)

    # Gerar relatório com tratamento de acordes
    events: list[list[dict]] = group_notes_into_events(notes)
    report_chords: str = generate_report_chords(events, filepath, title)

    # Exibir no terminal
    print()
    print(report)
    print()
    print(report_chords)
    print()

    # Salvar arquivos de log
    base: str = os.path.splitext(filepath)[0]
    # Se o arquivo tem extensão dupla (.musicxml.xml), remover ambas
    if base.endswith('.musicxml'):
        base = base[:-len('.musicxml')]

    log_path: str = base + "_piano_fatorado.txt"
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  ✓ Relatório salvo em: {os.path.basename(log_path)}")

    log_path_chords: str = base + "_piano_fatorado_acordes.txt"
    with open(log_path_chords, 'w', encoding='utf-8') as f:
        f.write(report_chords)
    print(f"  ✓ Relatório (acordes) salvo em: {os.path.basename(log_path_chords)}")

    print()
    return log_path


def selecionar_e_analisar() -> Optional[str]:
    """Abre diálogo tkinter para selecionar arquivo e processa.

    Retorna o caminho do relatório gerado, ou None se cancelado/erro.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print("  ✗ tkinter não disponível. Instale o Python com suporte a tkinter.")
        print("  Uso alternativo: python piano_fatorado.py <arquivo.musicxml>")
        return None

    # Criar janela raiz oculta
    root: tk.Tk = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    filepath: str = filedialog.askopenfilename(
        title="Piano Fatorado — Selecione o arquivo MusicXML",
        filetypes=[
            ("MusicXML", "*.musicxml *.musicxml.xml *.mxl"),
            ("MusicXML descompactado", "*.musicxml *.xml"),
            ("MusicXML compactado", "*.mxl"),
            ("Todos os arquivos", "*.*"),
        ],
        initialdir=os.path.dirname(os.path.abspath(__file__))
    )

    root.destroy()

    if not filepath:
        print("  ⚠ Nenhum arquivo selecionado.")
        return None

    return process_file(filepath)


def main() -> None:
    """Função principal."""
    # Forçar UTF-8 no console do Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              PIANO FATORADO — Analisador Musical            ║")
    print("║      Sonificação por Fatoração Prima de Teclas do Piano     ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    if len(sys.argv) > 1:
        # Modo CLI: processar arquivos passados como argumentos
        for filepath in sys.argv[1:]:
            process_file(filepath)
    else:
        # Sem argumentos: abrir diálogo GUI
        selecionar_e_analisar()


if __name__ == '__main__':
    main()
