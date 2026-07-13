import React, { useEffect, useMemo, useState } from "react";
import { Button, Icon, InputGroup } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { DiagnosticItem } from "../model/symbolIndex";
import { useSymbolIndexStore } from "../editor/symbolIndexStore";
import { COMMAND_ID, executeCommand } from "../editor/commands";
import { useSettingsStore } from "../editor/settings";
import { useEditorDialogsContext } from "../editor/EditorDialogsContext";
import { useResize } from "./hooks/useResize";
import { normalizePath } from "../shared/normalizePath";

interface ProblemsPanelProps {
  visible: boolean;
  height: number;
  onToggleVisible: () => void;
  onClose: () => void;
  onHeightChange: (nextHeight: number) => void;
}

interface FlatDiagnosticItem {
  id: string;
  metaPath: string;
  item: DiagnosticItem;
}

const MIN_PANEL_HEIGHT = 140;

function getSeverityOrder(severity: DiagnosticItem["severity"]): number {
  if (severity === "error") {
    return 0;
  }
  if (severity === "warning") {
    return 1;
  }
  return 2;
}

export const ProblemsPanel: React.FC<ProblemsPanelProps> = ({
  visible,
  height,
  onToggleVisible,
  onClose,
  onHeightChange,
}) => {
  const { t } = useTranslation();
  const commandContext = useMemo(() => ({ ui: {} }), []);
  const {
    diagnosticsByFile,
    diagnosticStats,
    refetchDiagnostics,
    initialized,
    symbols,
  } = useSymbolIndexStore();
  const severityFilter = useSettingsStore((s) => s.problemsSeverityFilter);
  const setSeverityFilter = useSettingsStore((s) => s.setProblemsSeverityFilter);
  const query = useSettingsStore((s) => s.problemsQuery);
  const setQuery = useSettingsStore((s) => s.setProblemsQuery);
  const [selectedProblemId, setSelectedProblemId] = useState<string | null>(null);

  const { handleMouseDown: startResize } = useResize({
    direction: 'vertical',
    minSize: MIN_PANEL_HEIGHT,
    size: height,
    onSizeChange: onHeightChange,
    enabled: visible,
  });

  const flatItems = useMemo<FlatDiagnosticItem[]>(() => {
    const rows: FlatDiagnosticItem[] = [];
    for (const [metaPath, entries] of Object.entries(diagnosticsByFile)) {
      for (let i = 0; i < entries.length; i += 1) {
        const entry = entries[i];
        rows.push({
          id: `${normalizePath(metaPath)}::${entry.definition_id ?? ""}::${entry.code}::${i}`,
          metaPath,
          item: entry,
        });
      }
    }
    rows.sort((a, b) => {
      const severityDelta = getSeverityOrder(a.item.severity) - getSeverityOrder(b.item.severity);
      if (severityDelta !== 0) {
        return severityDelta;
      }
      const byPath = normalizePath(a.metaPath).localeCompare(normalizePath(b.metaPath));
      if (byPath !== 0) {
        return byPath;
      }
      return (a.item.definition_id ?? "").localeCompare(b.item.definition_id ?? "");
    });
    return rows;
  }, [diagnosticsByFile]);

  const filteredItems = useMemo<FlatDiagnosticItem[]>(() => {
    const q = query.trim().toLowerCase();
    return flatItems.filter((row) => {
      if (severityFilter !== "all" && row.item.severity !== severityFilter) {
        return false;
      }
      if (q === "") {
        return true;
      }
      const bucket = [
        row.item.code,
        row.item.message,
        row.item.meta_path,
        row.item.definition_id ?? "",
        row.item.field_path ?? "",
      ].join(" ").toLowerCase();
      return bucket.includes(q);
    });
  }, [flatItems, query, severityFilter]);

  useEffect(() => {
    if (selectedProblemId === null) {
      return;
    }
    const stillExists = filteredItems.some((row) => row.id === selectedProblemId);
    if (!stillExists) {
      setSelectedProblemId(null);
    }
  }, [filteredItems, selectedProblemId]);

  const symbolLabelByDiagKey = useMemo(() => {
    const map = new Map<string, string>();
    for (const symbol of symbols) {
      const key = `${normalizePath(symbol.metaPath)}::${symbol.definitionId}`;
      const displayName = symbol.displayName?.trim();
      const label = displayName && displayName.length > 0
        ? `${symbol.name} (${displayName})`
        : symbol.name;
      map.set(key, label);
    }
    return map;
  }, [symbols]);

  const renderSeverityIcon = (severity: DiagnosticItem["severity"]) => {
    if (severity === "error") {
      return <Icon icon="error" color="#db3737" />;
    }
    if (severity === "warning") {
      return <Icon icon="warning-sign" color="#d9822b" />;
    }
    return <Icon icon="info-sign" color="#2d72d2" />;
  };

  return (
    <div style={{ borderTop: "1px solid #c5d2db", background: "#eef3f7", flex: "0 0 auto" }}>
      <div
        style={{
          height: 32,
          display: "flex",
          alignItems: "center",
          padding: "0 8px",
          gap: 8,
          borderBottom: visible ? "1px solid #c5d2db" : "none",
          background: "#dde5ec",
        }}
      >
        <Button
          small
          minimal
          icon={visible ? "chevron-down" : "chevron-right"}
          onClick={onToggleVisible}
          title={visible ? t('problems.collapse') : t('problems.expand')}
        />
        <div style={{ fontSize: 13, fontWeight: 600, color: "#182026" }}>{t('problems.title')}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#5c7080", fontSize: 12 }}>
          <span>{diagnosticStats.total}</span>
          <span style={{ color: "#db3737" }}>E:{diagnosticStats.error}</span>
          <span style={{ color: "#d9822b" }}>W:{diagnosticStats.warning}</span>
          <span style={{ color: "#2d72d2" }}>I:{diagnosticStats.info}</span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
          <Button
            small
            minimal
            icon="refresh"
            title={t('problems.refresh')}
            disabled={!initialized}
            onClick={() => void refetchDiagnostics()}
          />
          <Button small minimal icon="cross" title={t('problems.close')} onClick={onClose} />
        </div>
      </div>

      {visible ? (
        <div style={{ height, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div
            onMouseDown={startResize}
            style={{ height: 4, cursor: "row-resize", background: "#d2dce5" }}
            title={t('problems.resizePanel')}
          />
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 8px", borderBottom: "1px solid #d8e1e8" }}>
            <InputGroup
              leftIcon="filter"
              placeholder={t('problems.filter')}
              value={query}
              onChange={(e) => setQuery((e.target as HTMLInputElement).value)}
              small
            />
            <Button small active={severityFilter === "all"} onClick={() => setSeverityFilter("all")}>{t('problems.all')}</Button>
            <Button small active={severityFilter === "error"} onClick={() => setSeverityFilter("error")}>{t('problems.error')}</Button>
            <Button small active={severityFilter === "warning"} onClick={() => setSeverityFilter("warning")}>{t('problems.warning')}</Button>
            <Button small active={severityFilter === "info"} onClick={() => setSeverityFilter("info")}>{t('problems.info')}</Button>
          </div>
          <div style={{ flex: 1, overflow: "auto", background: "#f5f8fa" }}>
            {filteredItems.length === 0 ? (
              <div style={{ padding: 12, color: "#738694", fontSize: 13 }}>{t('status.noProblems')}</div>
            ) : (
              filteredItems.map((row) => {
                const isSelected = selectedProblemId === row.id;
                const fileName = row.metaPath.split(/[\\/]/).pop() ?? row.metaPath;
                const symbolLabel = row.item.definition_id
                  ? symbolLabelByDiagKey.get(`${normalizePath(row.metaPath)}::${row.item.definition_id}`)
                  : undefined;
                const secondary = symbolLabel
                  ? `${fileName} • ${symbolLabel}`
                  : fileName;
                return (
                  <button
                    key={row.id}
                    type="button"
                    onClick={() => {
                      setSelectedProblemId(row.id);
                      void executeCommand(COMMAND_ID.NAVIGATION_JUMP_TO_DIAGNOSTIC, commandContext, { diag: { ...row.item, meta_path: row.metaPath } });
                    }}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      border: "none",
                      borderLeft: isSelected ? "3px solid #106ba3" : "3px solid transparent",
                      borderBottom: "1px solid #e1e8ed",
                      background: isSelected ? "#e6eff6" : "transparent",
                      padding: "8px 10px",
                      cursor: "pointer",
                      display: "flex",
                      gap: 8,
                    }}
                  >
                    <div style={{ marginTop: 1 }}>{renderSeverityIcon(row.item.severity)}</div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, color: "#182026", whiteSpace: "normal", wordBreak: "break-word" }}>
                        {row.item.message}
                      </div>
                      <div style={{ fontSize: 12, color: "#5c7080", marginTop: 2, whiteSpace: "normal", wordBreak: "break-word" }}>
                        {row.item.code} • {secondary}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};
