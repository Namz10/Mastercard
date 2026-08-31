interface FooterColumn {
  index: string;
  title: string;
  body: string;
}

export function ChartFooterStrip({ columns }: { columns: FooterColumn[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 mt-3 border-t border-border">
      {columns.map((col) => (
        <div key={col.index} className="space-y-1">
          <p className="font-mono text-[10px] text-ink-faint uppercase tracking-wide">{col.index}</p>
          <p className="text-[13px] font-semibold text-ink leading-snug">{col.title}</p>
          <p className="text-[11px] text-ink-muted leading-relaxed">{col.body}</p>
        </div>
      ))}
    </div>
  );
}
