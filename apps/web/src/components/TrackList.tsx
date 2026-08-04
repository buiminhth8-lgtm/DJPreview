import type { TrackSpec } from "../api/musicApi";

interface TrackListProps {
  tracks: TrackSpec[];
}

export default function TrackList({ tracks }: TrackListProps) {
  return (
    <table className="track-table">
      <thead>
        <tr>
          <th>id</th>
          <th>role</th>
          <th>instrument</th>
          <th>pattern</th>
          <th>register</th>
          <th>velocity</th>
          <th>enabled_sections</th>
        </tr>
      </thead>
      <tbody>
        {tracks.map((track) => (
          <tr key={track.id}>
            <td>{track.id}</td>
            <td>{track.role}</td>
            <td>{track.instrument}</td>
            <td>{track.pattern ?? "—"}</td>
            <td>{track.register ?? "—"}</td>
            <td>{track.velocity}</td>
            <td>{track.enabled_sections?.join(", ") ?? "全部"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
