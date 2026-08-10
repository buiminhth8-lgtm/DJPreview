// features/midi/editor/PianoKeyboard.tsx（T34.3）
// 左侧琴键参考：只标注 C/octave，减少视觉噪音。

import { rowToY } from "./midiEditorLayout";
import { GM_DRUM_LABELS } from "./midiEditorMusicContext";

export interface PianoKeyboardProps {
  minPitch: number;
  maxPitch: number;
  rowHeight: number;
  isDrum?: boolean;
}

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

function isBlackKey(pitch: number): boolean {
  return [1, 3, 6, 8, 10].includes(pitch % 12);
}

function pitchLabel(pitch: number): string {
  const name = NOTE_NAMES[pitch % 12];
  const octave = Math.floor(pitch / 12) - 1;
  return `${name}${octave}`;
}

export function PianoKeyboard({ minPitch, maxPitch, rowHeight, isDrum = false }: PianoKeyboardProps) {
  const rows: number[] = [];
  // The roll maps maxPitch to its top row, so the keyboard must use the same order.
  for (let pitch = maxPitch; pitch >= minPitch; pitch -= 1) {
    rows.push(pitch);
  }

  return (
    <div className="midi-editor__keyboard" aria-hidden="true">
      {rows.map((pitch) => {
        const black = isBlackKey(pitch);
        const isC = pitch % 12 === 0;
        return (
          <div
            key={pitch}
            className={`midi-editor__key${black && !isDrum ? " is-black" : ""}${isDrum ? " is-drum" : ""}`}
            style={{ height: rowHeight }}
            data-midi-pitch={pitch}
          >
            {isDrum ? (
              <span className={`midi-editor__key-label${GM_DRUM_LABELS.has(pitch) ? " is-semantic" : ""}`}>
                {GM_DRUM_LABELS.get(pitch) ?? `MIDI ${pitch}`}
              </span>
            ) : (
              isC && <span className="midi-editor__key-label">{pitchLabel(pitch)}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

export { rowToY };
