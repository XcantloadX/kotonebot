/** Conversion 扫描结果展示面板，包含匹配表格、确认/标记状态、进度显示及执行入口。 */

import React from "react";
import { Button, ButtonGroup, NonIdealState, ProgressBar, Spinner, Intent as BPIntent } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { useConversionResultStore, type ConversionStatus } from "../editor/conversionResultStore";
import { editorActions } from "../editor/actions";

const STATUS_LABELS: Record<ConversionStatus, { label: string; color: string; bg: string }> = {
  "pending": { label: "conversion.statusPending", color: "#5c7080", bg: "#f5f8fa" },
  "confirmed": { label: "conversion.statusConfirmed", color: "#0f9960", bg: "#f0fff8" },
  "false-positive": { label: "conversion.statusFalsePositive", color: "#c23030", bg: "#fff5f5" },
};

/** Conversion 扫描结果展示面板。 */
export const ConversionResultPanel: React.FC = () => {
  const { t } = useTranslation();
  const isLoading = useConversionResultStore((s) => s.isLoading);
  const progress = useConversionResultStore((s) => s.progress);
  const error = useConversionResultStore((s) => s.error);
  const items = useConversionResultStore((s) => s.items);
  const tabLabel = useConversionResultStore((s) => s.tabLabel);
  const setItemStatus = useConversionResultStore((s) => s.setItemStatus);
  const setAllStatus = useConversionResultStore((s) => s.setAllStatus);
  const getPendingCount = useConversionResultStore((s) => s.getPendingCount);
  const getConfirmedCount = useConversionResultStore((s) => s.getConfirmedCount);
  const getFalsePositiveCount = useConversionResultStore((s) => s.getFalsePositiveCount);

  const pendingCount = getPendingCount();
  const confirmedCount = getConfirmedCount();
  const falsePositiveCount = getFalsePositiveCount();

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
          {t("conversion.totalCount", { count: items.length })}&nbsp;
          {pendingCount > 0 ? <span style={{ color: "#5c7080" }}>{t("conversion.pendingCount", { count: pendingCount })}</span> : null}
          {confirmedCount > 0 ? <span style={{ color: "#0f9960", marginLeft: 4 }}>{t("conversion.confirmedCount", { count: confirmedCount })}</span> : null}
          {falsePositiveCount > 0 ? <span style={{ color: "#c23030", marginLeft: 4 }}>{t("conversion.falsePositiveCount", { count: falsePositiveCount })}</span> : null}
        </span>
        <div style={{ flex: 1 }} />
        <ButtonGroup minimal>
          <Button
            text={t("conversion.confirmSelected")}
            icon="tick"
            onClick={() => setAllStatus("confirmed")}
          />
          <Button
            text={t("conversion.markFalsePositive")}
            icon="cross"
            onClick={() => setAllStatus("false-positive")}
          />
        </ButtonGroup>
        <Button
          intent="primary"
          text={t("conversion.execute")}
          onClick={handleExecute}
          disabled={confirmedCount === 0}
        />
      </div>

      {/* 表格 */}
      <div style={{ flex: 1, overflow: "auto" }}>
        <table style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: 12,
          tableLayout: "fixed",
        }}>
          <thead>
            <tr style={{ background: "#e1e8ed", position: "sticky", top: 0 }}>
              <th style={{ width: 32, padding: "6px 4px", textAlign: "center" }}>☐</th>
              <th style={{ padding: "6px 8px", textAlign: "left" }}>{t("conversion.singlePath")}</th>
              <th style={{ width: 120, padding: "6px 8px", textAlign: "left" }}>{t("conversion.singleImage")}</th>
              <th style={{ width: 120, padding: "6px 8px", textAlign: "left" }}>{t("conversion.matchCrop")}</th>
              <th style={{ width: 60, padding: "6px 8px", textAlign: "right" }}>{t("conversion.matchScore")}</th>
              <th style={{ width: 70, padding: "6px 8px", textAlign: "center" }}>{t("conversion.status")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => {
              const statusInfo = STATUS_LABELS[item.status];
              return (
                <tr
                  key={index}
                  style={{
                    background: index % 2 === 0 ? "#ffffff" : "#fafbfc",
                    borderBottom: "1px solid #e7edf2",
                  }}
                >
                  <td style={{ textAlign: "center", padding: "4px" }}>
                    <input
                      type="checkbox"
                      checked={item.status === "confirmed"}
                      onChange={(e) => {
                        setItemStatus(index, e.target.checked ? "confirmed" : "pending");
                      }}
                    />
                  </td>
                  <td style={{ padding: "4px 8px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.match.singleImagePath}
                  </td>
                  <td style={{ padding: "4px 8px" }}>
                    <img
                      src={`/api/image/thumbnail?path=${encodeURIComponent(item.match.singleImagePath)}&size=80`}
                      alt=""
                      style={{ width: 80, height: 60, objectFit: "contain", border: "1px solid #d1d8e0", borderRadius: 2 }}
                    />
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
                  <td style={{ textAlign: "center", padding: "4px 8px" }}>
                    <span style={{
                      display: "inline-block",
                      padding: "2px 6px",
                      borderRadius: 3,
                      fontSize: 11,
                      color: statusInfo.color,
                      background: statusInfo.bg,
                      border: `1px solid ${statusInfo.color}22`,
                    }}>
                      {t(statusInfo.label)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
