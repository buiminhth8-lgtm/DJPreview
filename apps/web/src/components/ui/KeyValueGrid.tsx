// KeyValueGrid：键值网格（项目概览 / Provider 信息 / debug metadata）。

import type { ReactNode } from "react";

export interface KeyValueItem {
  label: string;
  value: ReactNode;
}

export interface KeyValueGridProps {
  items: KeyValueItem[];
  columns?: 2 | 3 | 4;
  emptyValue?: string;
}

export function KeyValueGrid({ items, columns = 2, emptyValue = "—" }: KeyValueGridProps) {
  const columnsClass = columns === 4 ? " ui-key-value-grid--4" : columns === 3 ? " ui-key-value-grid--3" : "";
  return (
    <div className={`ui-key-value-grid${columnsClass}`}>
      {items.map(({ label, value }) => {
        const isEmpty = value === null || value === undefined || value === "";
        return (
          <div className="ui-key-value-grid__item" key={label}>
            <span className="ui-key-value-grid__label">{label}</span>
            <span className={`ui-key-value-grid__value${isEmpty ? " ui-key-value-grid__value--empty" : ""}`}>
              {isEmpty ? emptyValue : value}
            </span>
          </div>
        );
      })}
    </div>
  );
}
