// features/midi/editor/TrackSelector.tsx（T34.3）
// 轨道选择器：展示全部可编辑轨道，使用 canonical track.id。

import type { MidiEditorTrack } from "./midiEditorTypes";

export interface TrackSelectorProps {
  tracks: MidiEditorTrack[];
  selectedTrackId: string | null;
  onSelect: (trackId: string) => void;
}

export function TrackSelector({ tracks, selectedTrackId, onSelect }: TrackSelectorProps) {
  if (!tracks.length) return null;

  return (
    <div className="midi-editor__tracks" role="listbox" aria-label="选择轨道">
      {tracks.map((track) => {
        const label = track.role ? `${track.name} · ${track.role}` : track.name;
        const isSelected = track.id === selectedTrackId;
        return (
          <button
            key={track.id}
            type="button"
            role="option"
            aria-selected={isSelected}
            className={`midi-editor__track${isSelected ? " is-selected" : ""}`}
            onClick={() => onSelect(track.id)}
            title={label}
          >
            <span className="midi-editor__track-name">{track.name}</span>
            {track.role && <span className="midi-editor__track-role">{track.role}</span>}
            <span className="midi-editor__track-count">{track.notes.length}</span>
          </button>
        );
      })}
    </div>
  );
}
