// features/midi/editor/PianoKeyboard.tsx（T34.3）
// 左侧琴键参考：只标注 C/octave，减少视觉噪音。

import { rowToY } from "./midiEditorLayout";

export interface PianoKeyboardProps {
  minPitch: number;
  maxPitch: number;
  rowHeight: number;
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

export function PianoKeyboard({ minPitch, maxPitch, rowHeight }: PianoKeyboardProps) {
  const rows: number[] = [];
  for (let pitch = minPitch; pitch <= maxPitch; pitch += 1) {
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
            className={`midi-editor__key${black ? " is-black" : ""}`}
            style={{ height: rowHeight }}
          >
            {isC && <span className="midi-editor__key-label">{pitchLabel(pitch)}</span>}
          </div>
        );
      })}
    </div>
  );
}

export { rowToY };
