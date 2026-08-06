// LoadingState：加载占位（CSS spinner，不引入 spinner 库）。

export interface LoadingStateProps {
  title?: string;
  description?: string;
  compact?: boolean;
}

export function LoadingState({ title, description, compact }: LoadingStateProps) {
  return (
    <div className={`ui-loading-state${compact ? " ui-loading-state--compact" : ""}`} role="status">
      <span className="ui-loading-state__spinner" aria-hidden="true" />
      <div className="ui-loading-state__text">
        {title && <div className="ui-loading-state__title">{title}</div>}
        {description && <div className="ui-loading-state__description">{description}</div>}
        {!title && !description && <span>加载中…</span>}
      </div>
    </div>
  );
}
