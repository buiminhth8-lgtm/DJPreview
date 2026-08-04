"""编曲器模块。"""

from packages.music_core.composer.events import CompositionResult, NoteEvent, TrackEvents

__all__ = ["CompositionResult", "NoteEvent", "TrackEvents", "compose_music"]


def __getattr__(name):
    """惰性导出 compose_music，避免 melody_engine → composer.events → music_composer → melody_engine 循环。"""
    if name == "compose_music":
        from packages.music_core.composer.music_composer import compose_music

        return compose_music
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
