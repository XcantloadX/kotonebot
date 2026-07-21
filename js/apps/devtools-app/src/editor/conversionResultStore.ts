/** Conversion 扫描结果的 Zustand store。 */

import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { ConversionMatch, ScanProgress } from "../api/conversion";

export interface ConversionResultItem {
  /** 转换匹配数据。 */
  match: ConversionMatch;
  /** 用户勾选状态。 */
  selected: boolean;
}

export interface ConversionProgress {
  /** 待扫描总数。 */
  total: number;
  /** 已完成数量。 */
  current: number;
  /** 当前正在处理的文件名。 */
  currentFile: string;
}

interface ConversionResultState {
  /** 是否正在加载中（扫描进行中）。 */
  isLoading: boolean;
  /** 扫描进度。 */
  progress: ConversionProgress | null;
  /** 错误信息。 */
  error: string | null;
  /** 当前扫描任务 ID（用于轮询和取消）。 */
  taskId: string | null;
  /** 匹配结果列表。 */
  items: ConversionResultItem[];
  /** 进入 loading 状态。 */
  setLoading: () => void;
  /** 设置任务 ID（启动扫描后调用）。 */
  setTaskId: (taskId: string) => void;
  /** 设置扫描进度（轮询中调用）。 */
  setProgress: (progress: ScanProgress) => void;
  /** 扫描出错。 */
  setError: (error: string) => void;
  /** 设置结果列表（扫描完成后）。 */
  setItems: (matches: ConversionMatch[]) => void;
  /** 清除所有状态。 */
  clear: () => void;
  /** 切换指定索引项的勾选状态。 */
  toggleItem: (index: number) => void;
  /** 全选。 */
  selectAll: () => void;
  /** 全不选。 */
  deselectAll: () => void;
  /** 获取选中项数量。 */
  getSelectedCount: () => number;
  /** 获取所有选中的匹配项。 */
  getSelected: () => ConversionMatch[];
  /** 是否全部选中。 */
  isAllSelected: () => boolean;
}

export const useConversionResultStore = create<ConversionResultState>()(
  immer((set, get) => ({
    isLoading: false,
    progress: null,
    error: null,
    taskId: null,
    items: [],

    setLoading: () => set((state) => {
      state.isLoading = true;
      state.progress = null;
      state.error = null;
      state.items = [];
    }),

    setTaskId: (taskId) => set((state) => {
      state.taskId = taskId;
    }),

    setProgress: (progress) => set((state) => {
      state.isLoading = progress.state !== "completed" && progress.state !== "cancelled" && progress.state !== "error";
      if (progress.state === "completed" && progress.matches) {
        const seen = new Set<string>();
        state.items = progress.matches.map((m) => {
          const first = !seen.has(m.singleImagePath);
          seen.add(m.singleImagePath);
          return { match: m, selected: first };
        });
        state.isLoading = false;
      } else if (progress.state === "error") {
        state.error = progress.error || "Scan failed";
        state.isLoading = false;
      } else if (progress.state === "cancelled") {
        state.error = "Scan cancelled";
        state.isLoading = false;
      } else {
        state.progress = { total: progress.total, current: progress.current, currentFile: progress.currentFile };
      }
    }),

    setError: (error) => set((state) => {
      state.error = error;
      state.isLoading = false;
      state.progress = null;
    }),

    setItems: (matches) => set((state) => {
      state.isLoading = false;
      state.progress = null;
      state.error = null;
      const seen = new Set<string>();
      state.items = matches.map((m) => {
        const first = !seen.has(m.singleImagePath);
        seen.add(m.singleImagePath);
        return { match: m, selected: first };
      });
    }),

    clear: () => set((state) => {
      state.isLoading = false;
      state.progress = null;
      state.error = null;
      state.taskId = null;
      state.items = [];
    }),

    toggleItem: (index) => set((state) => {
      if (state.items[index]) {
        state.items[index].selected = !state.items[index].selected;
      }
    }),
    selectAll: () => set((state) => {
      for (const item of state.items) {
        item.selected = true;
      }
    }),
    deselectAll: () => set((state) => {
      for (const item of state.items) {
        item.selected = false;
      }
    }),
    getSelectedCount: () => get().items.filter((i) => i.selected).length,
    getSelected: () => {
      return get().items
        .filter((item) => item.selected)
        .map((item) => item.match);
    },
    isAllSelected: () => get().items.length > 0 && get().items.every((i) => i.selected),
  }))
);
