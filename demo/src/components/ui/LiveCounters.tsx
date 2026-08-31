import { useEffect, useState } from "react";

export function LiveCounters({
  customers,
  events,
  totalCustomers = 2400,
}: {
  customers?: number;
  events?: number;
  totalCustomers?: number;
}) {
  const [display, setDisplay] = useState({ customers: 0, events: 0 });

  useEffect(() => {
    if (customers != null) setDisplay((d) => ({ ...d, customers }));
    if (events != null) setDisplay((d) => ({ ...d, events }));
  }, [customers, events]);

  return (
    <div className="flex gap-4 text-[13px] tnum" data-demo="live-counters">
      <div>
        <span className="text-ink-faint">Customers </span>
        <span className="font-medium text-ink">
          {display.customers.toLocaleString()} / {totalCustomers.toLocaleString()}
        </span>
      </div>
      {display.events > 0 ? (
        <div>
          <span className="text-ink-faint">Events </span>
          <span className="font-medium text-ink">{display.events.toLocaleString()}</span>
        </div>
      ) : null}
    </div>
  );
}
