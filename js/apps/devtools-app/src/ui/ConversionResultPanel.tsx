/** Conversion 扫描结果展示面板，包含匹配表格、全选/全不选、进度显示及执行入口。 */

import React from "react";
import { Button, Checkbox, NonIdealState, ProgressBar, Spinner, Tooltip, Intent as BPIntent } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { useConversionResultStore } from "../editor/conversionResultStore";
import { editorActions } from "../editor/actions";
import type { ITab } from "../editor/tabSystem/types";

/** Conversion 扫描结果展示面板。 */
export const ConversionResultPanel: React.FC<{ tab: ITab }> = ({ tab }) => {
  const { t } = useTranslation();
  const isLoading = useConversionResultStore((s) => s.isLoading);
  const progress = useConversionResultStore((s) => s.progress);
  const error = useConversionResultStore((s) => s.error);
  const items = useConversionResultStore((s) => s.items);
  const tabLabel = tab.label;
  const toggleItem = useConversionResultStore((s) => s.toggleItem);
  const selectAll = useConversionResultStore((s) => s.selectAll);
  const deselectAll = useConversionResultStore((s) => s.deselectAll);
  const getSelectedCount = useConversionResultStore((s) => s.getSelectedCount);
  const isAllSelected = useConversionResultStore((s) => s.isAllSelected);

  const selectedCount = getSelectedCount();
  const allSelected = isAllSelected();

  const handleExecute = async () => {
    await editorActions.conversion.executeConversion();
  };

  const handleCancel = async () => {
    await editorActions.conversion.cancelScan();
  };

  // loading/进度态
  if (isLoading) {
    const progressValue = progress && progress.total > 0
      ? progress.current / progress.total
      : undefined;
    const progressLabel = progress
      ? t("conversion.scanningProgress", {
          current: progress.current,
          total: progress.total,
          file: progress.currentFile,
        })
      : t("conversion.scanningClassify");
    return (
      <div style={{
        height: "100%", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: 16, padding: 40,
      }}>
        <Spinner size={40} />
        <div style={{ fontSize: 14, fontWeight: 600, color: "#394b59" }}>{tabLabel}</div>
        <div style={{ width: 320 }}>
          <ProgressBar
            value={progressValue}
            intent={BPIntent.PRIMARY}
            animate={progressValue === undefined}
          />
        </div>
        <div style={{ fontSize: 12, color: "#5c7080", textAlign: "center" }}>
          {progressLabel}
        </div>
        <Button
          text={t("conversion.cancelScan")}
          icon="disable"
          onClick={handleCancel}
          minimal
        />
      </div>
    );
  }

  // 错误态
  if (error) {
    return (
      <div style={{ padding: 20, height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <NonIdealState
          icon="error"
          title={t("conversion.scanError")}
          description={error}
          action={<Button text={t("conversion.retryScan")} icon="refresh" onClick={() => editorActions.conversion.scanAllDocuments()} />}
        />
      </div>
    );
  }

  // 空结果
  if (items.length === 0) {
    return (
      <div style={{ padding: 20, height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <NonIdealState icon="search" title={t("conversion.emptyResult")} />
      </div>
    );
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: 0 }}>
      {/* 顶部工具栏 */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 12px",
        borderBottom: "1px solid #d1d8e0",
        background: "#f5f8fa",
        flexWrap: "wrap",
      }}>
        <span style={{ fontWeight: 600, fontSize: 13, marginRight: 8 }}>
          {tabLabel}
        </span>
        <span style={{ fontSize: 12, color: "#5c7080" }}>
          {t("conversion.totalCount", { count: items.length })}
          {selectedCount > 0 ? <span style={{ color: "#137cbd", marginLeft: 4 }}>{t("conversion.selectedCount", { count: selectedCount })}</span> : null}
        </span>
        <div style={{ flex: 1 }} />
        <Button
          text={t("conversion.selectAll")}
          icon="tick"
          onClick={selectAll}
          disabled={allSelected}
          minimal
        />
        <Button
          text={t("conversion.deselectAll")}
          icon="cross"
          onClick={deselectAll}
          disabled={selectedCount === 0}
          minimal
        />
        <Button
          intent="primary"
          text={t("conversion.execute")}
          onClick={handleExecute}
          disabled={selectedCount === 0}
        />
      </div>

      {/* 表格 */}
      <div style={{ flex: 1, overflow: "auto" }}>
        <table style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: 12,
        }}>
          <thead>
            <tr style={{ background: "#e1e8ed", position: "sticky", top: 0 }}>
              <th style={{ padding: "6px 4px", textAlign: "center" }}></th>
              <th style={{ padding: "6px 8px", textAlign: "left" }}>{t("conversion.singlePath")}</th>
              <th style={{ padding: "6px 8px", textAlign: "left" }}>{t("conversion.singleImage")}</th>
              <th style={{ padding: "6px 8px", textAlign: "left" }}>{t("conversion.matchedPath")}</th>
              <th style={{ padding: "6px 8px", textAlign: "left" }}>{t("conversion.matchCrop")}</th>
              <th style={{ padding: "6px 8px", textAlign: "right" }}>{t("conversion.matchScore")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <tr
                key={index}
                onClick={() => toggleItem(index)}
                style={{
                  background: item.selected
                    ? "#d3e8f7"
                    : index % 2 === 0
                      ? "#ffffff"
                      : "#fafbfc",
                  borderBottom: "1px solid #e7edf2",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  if (!item.selected) e.currentTarget.style.background = "#eaf4fb";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = item.selected
                    ? "#d3e8f7"
                    : index % 2 === 0
                      ? "#ffffff"
                      : "#fafbfc";
                }}
              >
                <td style={{ textAlign: "center", padding: "4px" }}>
                  <Checkbox
                    checked={item.selected}
                    onChange={() => toggleItem(index)}
                    onClick={(e) => e.stopPropagation()}
                    inline
                  />
                </td>
                <td style={{ padding: "4px 8px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  <span title={item.match.singleImagePath}>
                    {item.match.singleImagePath.split("/").pop()}
                  </span>
                </td>
                <td style={{ padding: "4px 8px" }}>
                  <img
                    src={`/api/image/thumbnail?path=${encodeURIComponent(item.match.singleImagePath)}&size=80`}
                    alt=""
                    style={{ width: 80, height: 60, objectFit: "contain", border: "1px solid #d1d8e0", borderRadius: 2 }}
                  />
                </td>
                <td style={{ padding: "4px 8px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  <Tooltip
                    content={
                      <img
                        src={`/api/image/thumbnail?path=${encodeURIComponent(item.match.matchedImagePath)}&size=240`}
                        alt=""
                        style={{ maxWidth: 240, maxHeight: 180, borderRadius: 2 }}
                      />
                    }
                    placement="left"
                    hoverOpenDelay={300}
                  >
                    <a
                      href="#"
                      title={item.match.matchedImagePath}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        void editorActions.image.openWithMeta(item.match.matchedImagePath);
                      }}
                      style={{ color: "#137cbd", textDecoration: "none" }}
                    >
                      {item.match.matchedImagePath.split("/").pop()}
                    </a>
                  </Tooltip>
                </td>
                <td style={{ padding: "4px 8px" }}>
                  <img
                    src={`/api/image/thumbnail?path=${encodeURIComponent(item.match.matchedImagePath)}&size=80&x1=${item.match.matchX}&y1=${item.match.matchY}&x2=${item.match.matchX + item.match.matchW}&y2=${item.match.matchY + item.match.matchH}`}
                    alt=""
                    style={{ width: 80, height: 60, objectFit: "contain", border: "1px solid #d1d8e0", borderRadius: 2 }}
                  />
                </td>
                <td style={{ textAlign: "right", padding: "4px 8px", fontVariantNumeric: "tabular-nums" }}>
                  {item.match.matchScore.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
