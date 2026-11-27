import PhotoPreview from "./PhotoPreview.jsx";

function Submission({ section, row, token }) {
  switch (section) {
    case "items": return <><strong>{row.name}</strong><small>{row.category}</small>{row.description}</>;
    case "item-prices": return <><strong>৳{row.price}</strong><small>{row.item_name} · Item {row.item_status}</small></>;
    case "reviews": return <><strong>{row.rating}/5</strong><p>{row.comment || "No written comment"}</p></>;
    case "photos": return <><PhotoPreview photo={row} token={token} /><small>{row.caption}</small></>;
  }
}

export default function AdminModerationRows({ section, rows, token, username, busy, onApprove, onReject, onRemove }) {
  return <><thead><tr><th>Place</th><th>Submission</th><th>Contributor</th><th>Submitted</th>
    <th>Status</th><th>Actions</th></tr></thead><tbody>
    {rows.map((row) => {
      const contributor = row.username || row.contributor;
      const own = contributor === username;
      const needsItem = section === "item-prices" && row.item_status !== "approved";
      return <tr key={row.id}>
        <td>{row.place_name}</td><td><Submission section={section} row={row} token={token} /></td>
        <td>{contributor}</td><td>{new Date(row.submitted_at || row.created_at).toLocaleString()}</td>
        <td><span className={"badge " + row.status}>{row.status}</span>
          {row.reviewer && <small>By {row.reviewer}</small>}{row.rejection_reason && <small>{row.rejection_reason}</small>}
        </td>
        <td><div className="actions">
          {row.status !== "approved" && <button disabled={busy || own || needsItem} onClick={() => onApprove(row)}>Approve</button>}
          {row.status !== "rejected" && <button disabled={busy || own} onClick={() => onReject(row)}>Reject</button>}
          {section === "photos" && row.can_delete && <button className="danger" disabled={busy} onClick={() => onRemove(row)}>Delete photo</button>}
        </div>{own && <small>Another administrator must review your submission.</small>}
          {needsItem && <small>Approve the item before its price.</small>}
        </td>
      </tr>;
    })}
  </tbody></>;
}
