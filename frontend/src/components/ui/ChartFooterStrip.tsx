interface FooterColumn {
  index: string;
  title: string;
  body: string;
}

export function ChartFooterStrip({ columns }: { columns: FooterColumn[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-5 mt-5 border-t border-gray-200">
      {columns.map((col) => (
        <div key={col.index} className="space-y-1.5">
          <p className="font-mono text-[10px] text-ink-faint uppercase tracking-wide">{col.index}</p>
          <p className="text-sm font-semibold text-ink leading-snug">{col.title}</p>
          <p className="text-xs text-ink-muted leading-relaxed">{col.body}</p>
        </div>
      ))}
    </div>
  );
}
