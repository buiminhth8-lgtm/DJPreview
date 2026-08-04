"""编曲器模块。"""

from packages.music_core.composer.events import CompositionResult, NoteEvent, TrackEvents
from packages.music_core.composer.music_composer import compose_music

__all__ = ["CompositionResult", "NoteEvent", "TrackEvents", "compose_music"]
