"use client";

export default function Pagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="pagination">
      <span>
        {total === 0 ? "0" : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
      </span>
      <button className="btn" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Previous
      </button>
      <span>
        Page {page} of {pages}
      </span>
      <button className="btn" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Next
      </button>
    </div>
  );
}
