import type { TrackMixSpec } from "../api/musicApi";

interface TrackMixerStripProps {
  track: TrackMixSpec;
  onChange: (trackId: string, patch: Partial<TrackMixSpec>) => void;
}

export default function TrackMixerStrip({ track, onChange }: TrackMixerStripProps) {
  return (
    <div className="mixer-strip">
      <div className="mixer-strip-head">
        <span className="mixer-track-id">{track.track_id}</span>
        <span className="mixer-track-meta">
          {track.role} · {track.instrument ?? "—"}
        </span>
      </div>
      <label className="mixer-control">
        volume
        <input
          type="range"
          min={0}
          max={1.5}
          step={0.05}
          value={track.volume}
          onChange={(e) => onChange(track.track_id, { volume: Number(e.target.value) })}
        />
        <span>{track.volume.toFixed(2)}</span>
      </label>
      <label className="mixer-control">
        pan
        <input
          type="range"
          min={-1}
          max={1}
          step={0.05}
          value={track.pan}
          onChange={(e) => onChange(track.track_id, { pan: Number(e.target.value) })}
        />
        <span>{track.pan.toFixed(2)}</span>
      </label>
      <label className="mixer-control">
        velocity_scale
        <input
          type="range"
          min={0.1}
          max={2}
          step={0.05}
          value={track.velocity_scale}
          onChange={(e) => onChange(track.track_id, { velocity_scale: Number(e.target.value) })}
        />
        <span>{track.velocity_scale.toFixed(2)}</span>
      </label>
      <div className="mixer-checks">
        <label>
          <input
            type="checkbox"
            checked={track.mute}
            onChange={(e) => onChange(track.track_id, { mute: e.target.checked })}
          />
          mute
        </label>
        <label>
          <input
            type="checkbox"
            checked={track.solo}
            onChange={(e) => onChange(track.track_id, { solo: e.target.checked })}
          />
          solo
        </label>
        <label>
          <input
            type="checkbox"
            checked={track.enabled}
            onChange={(e) => onChange(track.track_id, { enabled: e.target.checked })}
          />
          enabled
        </label>
      </div>
    </div>
  );
}
