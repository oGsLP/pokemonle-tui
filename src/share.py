from poketypes import GuessRecord


def format_share_result(
    guesses_with_hints: list[GuessRecord],
    max_guesses: int,
    target_name: str,
    target_name_en: str,
    target_id: int,
    won: bool,
    generation_label: str = "",
) -> str:
    guess_count = len(guesses_with_hints)

    if won:
        header = f"  Pokémonle #{target_id}  {guess_count}/{max_guesses}"
    else:
        header = f"  Pokémonle #{target_id}  X/{max_guesses}"

    all_labels: list[str] = []
    seen: set[str] = set()
    for _, hints in guesses_with_hints:
        for h in hints:
            label = h[0]
            if label not in seen:
                all_labels.append(label)
                seen.add(label)

    level_sym = {
        "exact": "●",
        "close": "◐",
        "partial": "◐",
        "far": "○",
        "miss": "○",
    }

    col_widths = []
    for label in all_labels:
        max_w = len(label) * 2  # CJK chars are ~2 width
        for _, hints in guesses_with_hints:
            hint_map = {h[0]: h for h in hints}
            if label in hint_map:
                w = len(hint_map[label][1]) * 2
                if w > max_w:
                    max_w = w
        col_widths.append(max(max_w + 2, 4))

    lines = [header]

    header_line = "  "
    for i, label in enumerate(all_labels):
        header_line += label.center(col_widths[i])
    lines.append(header_line)
    lines.append("  " + "─" * sum(col_widths))

    for row_idx, (_, hints) in enumerate(guesses_with_hints, 1):
        hint_map = {h[0]: h for h in hints}
        row = f"{row_idx:>2} "
        for i, label in enumerate(all_labels):
            if label in hint_map:
                h = hint_map[label]
                sym = level_sym.get(h[2], "○")
                cell = f"{sym} {h[1]}"
                row += cell.center(col_widths[i])
            else:
                row += "·".center(col_widths[i])
        lines.append(row)

    lines.append("─" * (sum(col_widths) + 4))

    detail = f"#{target_id:04d} {target_name} ({target_name_en})"
    if generation_label:
        detail += f"  [{generation_label}]"
    lines.append(detail)

    return "\n".join(lines)
