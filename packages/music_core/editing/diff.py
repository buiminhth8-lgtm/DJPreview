"""MusicSpec 差异对比：反映主要变化。"""

from __future__ import annotations

from services.api.schemas.music_spec import MusicSpec


def _add(changes: list[dict], field: str, old_value, new_value) -> None:
    if old_value != new_value:
        changes.append({"field": field, "old": old_value, "new": new_value})


def diff_music_specs(old: MusicSpec, new: MusicSpec) -> list[dict]:
    """对比两个 MusicSpec，返回主要变化列表 [{field, old, new}]。"""
    changes: list[dict] = []

    _add(changes, "tempo.bpm", old.tempo.bpm, new.tempo.bpm)
    _add(changes, "tempo.feel", old.tempo.feel, new.tempo.feel)
    _add(changes, "tonality.key", old.tonality.key, new.tonality.key)
    _add(changes, "tonality.mode", old.tonality.mode, new.tonality.mode)
    _add(changes, "tonality.scale", old.tonality.scale, new.tonality.scale)
    _add(changes, "length.bars", old.length.bars, new.length.bars)
    _add(changes, "meter", (old.meter.numerator, old.meter.denominator), (new.meter.numerator, new.meter.denominator))

    old_style, new_style = set(old.style), set(new.style)
    if old_style != new_style:
        _add(changes, "style", sorted(old_style), sorted(new_style))
    old_mood, new_mood = set(old.mood), set(new.mood)
    if old_mood != new_mood:
        _add(changes, "mood", sorted(old_mood), sorted(new_mood))

    old_tracks = {t.id: t for t in old.tracks}
    new_tracks = {t.id: t for t in new.tracks}
    for track_id in sorted(new_tracks.keys() - old_tracks.keys()):
        changes.append({"field": "tracks.added", "old": None, "new": track_id})
    for track_id in sorted(old_tracks.keys() - new_tracks.keys()):
        changes.append({"field": "tracks.removed", "old": track_id, "new": None})
    for track_id in sorted(old_tracks.keys() & new_tracks.keys()):
        ot, nt = old_tracks[track_id], new_tracks[track_id]
        _add(changes, f"tracks.{track_id}.velocity", ot.velocity, nt.velocity)
        _add(changes, f"tracks.{track_id}.instrument", ot.instrument, nt.instrument)
        _add(changes, f"tracks.{track_id}.role", ot.role, nt.role)
        _add(changes, f"tracks.{track_id}.enabled_sections", ot.enabled_sections, nt.enabled_sections)

    old_sections = {s.id: s for s in old.form}
    new_sections = {s.id: s for s in new.form}
    for section_id in sorted(old_sections.keys() & new_sections.keys()):
        os_, ns = old_sections[section_id], new_sections[section_id]
        _add(changes, f"form.{section_id}.energy", os_.energy, ns.energy)
        _add(changes, f"form.{section_id}.name", os_.name, ns.name)
        _add(changes, f"form.{section_id}.bars", os_.bars, ns.bars)
    for section_id in sorted(new_sections.keys() - old_sections.keys()):
        changes.append({"field": "form.added", "old": None, "new": section_id})
    for section_id in sorted(old_sections.keys() - new_sections.keys()):
        changes.append({"field": "form.removed", "old": section_id, "new": None})

    old_harmony = {h.section: h.progression for h in old.harmony}
    new_harmony = {h.section: h.progression for h in new.harmony}
    for section in sorted(old_harmony.keys() | new_harmony.keys()):
        _add(changes, f"harmony.{section}", old_harmony.get(section), new_harmony.get(section))

    _add(changes, "notes", old.notes, new.notes)
    return changes
