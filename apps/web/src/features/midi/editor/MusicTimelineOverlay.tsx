import type { MidiEditorChordMarker, MidiEditorSectionMarker } from "./midiEditorMusicContext";

export interface MusicTimelineOverlayProps {
  sections: readonly MidiEditorSectionMarker[];
  chords: readonly MidiEditorChordMarker[];
  pixelsPerTick: number;
  showSections: boolean;
  showChords: boolean;
  onSeek?: (tick: number) => void;
}

export function MusicTimelineOverlay({
  sections,
  chords,
  pixelsPerTick,
  showSections,
  showChords,
  onSeek,
}: MusicTimelineOverlayProps) {
  return (
    <>
      {showSections && sections.length > 0 && (
        <div className="midi-editor__semantic-row midi-editor__section-row" data-testid="section-overlay">
          {sections.map((section) => (
            <button
              key={`${section.id}-${section.startTick}`}
              type="button"
              className="midi-editor__section-marker"
              data-section-id={section.id}
              data-start-tick={section.startTick}
              title={`${section.name} · bar ${section.startBar}–${section.startBar + section.bars - 1}`}
              style={{
                left: section.startTick * pixelsPerTick,
                width: Math.max(1, (section.endTick - section.startTick) * pixelsPerTick),
                opacity: 0.62 + Math.max(0, Math.min(1, section.energy)) * 0.32,
              }}
              onClick={(event) => {
                event.stopPropagation();
                onSeek?.(section.startTick);
              }}
            >
              {section.name}
            </button>
          ))}
        </div>
      )}
      {showChords && chords.length > 0 && (
        <div className="midi-editor__semantic-row midi-editor__chord-row" data-testid="chord-overlay">
          {chords.map((chord) => (
            <div
              key={`${chord.sectionId}-${chord.bar}-${chord.startTick}`}
              className="midi-editor__chord-marker"
              data-chord={chord.symbol}
              data-start-tick={chord.startTick}
              title={`${chord.symbol} · bar ${chord.bar}`}
              style={{
                left: chord.startTick * pixelsPerTick,
                width: Math.max(1, (chord.endTick - chord.startTick) * pixelsPerTick),
              }}
            >
              {chord.symbol}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
