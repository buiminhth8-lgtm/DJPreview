// useStyles：风格模板列表 / 选中风格。

import { useCallback, useEffect, useState } from "react";

import { getStyle, listStyles } from "../api/styleApi";
import type { StyleTemplateSpec } from "../api/types";
import { getErrorMessage } from "./error";

export function useStyles() {
  const [styles, setStyles] = useState<StyleTemplateSpec[]>([]);
  const [selectedStyleId, setSelectedStyleId] = useState<string>("");
  const [selectedStyle, setSelectedStyle] = useState<StyleTemplateSpec | null>(null);
  const [loadingStyles, setLoadingStyles] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStyles = useCallback(async (): Promise<StyleTemplateSpec[] | null> => {
    setLoadingStyles(true);
    setError(null);
    try {
      const result = await listStyles();
      setStyles(result);
      return result;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoadingStyles(false);
    }
  }, []);

  const loadStyle = useCallback(
    async (styleId: string): Promise<StyleTemplateSpec | null> => {
      if (!styleId) {
        setSelectedStyle(null);
        return null;
      }
      try {
        const template = await getStyle(styleId);
        setSelectedStyle(template);
        return template;
      } catch (e) {
        setError(getErrorMessage(e));
        return null;
      }
    },
    [],
  );

  useEffect(() => {
    if (selectedStyleId) {
      void loadStyle(selectedStyleId);
    } else {
      setSelectedStyle(null);
    }
  }, [selectedStyleId, loadStyle]);

  return {
    styles,
    selectedStyleId,
    setSelectedStyleId,
    selectedStyle,
    loadingStyles,
    error,
    setError,
    loadStyles,
    loadStyle,
  };
}
