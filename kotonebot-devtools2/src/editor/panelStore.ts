import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type PanelId = 'left' | 'right';

export interface PanelTabConfig {
  id: string;
  panelId: PanelId;
  order: number;
}

interface PanelState {
  /** Mapping of viewId -> which panel it lives in + order */
  tabConfigs: Record<string, PanelTabConfig>;
  /** Active tab for each panel */
  activeTabIds: Record<PanelId, string | null>;
  /** Set which panel a tab belongs to (also updates order) */
  moveTab: (tabId: string, toPanelId: PanelId, toIndex: number) => void;
  /** Reorder tab within its panel */
  reorderTab: (tabId: string, toIndex: number) => void;
  /** Set active tab in a panel */
  setActiveTab: (panelId: PanelId, tabId: string) => void;
  /** Get ordered list of tab ids for a panel */
  getTabsForPanel: (panelId: PanelId) => string[];
}

const DEFAULT_TAB_CONFIGS: Record<string, PanelTabConfig> = {
  properties: { id: 'properties', panelId: 'right', order: 0 },
  hierarchy: { id: 'hierarchy', panelId: 'left', order: 0 },
  project: { id: 'project', panelId: 'right', order: 1 },
};

const DEFAULT_ACTIVE_TABS: Record<PanelId, string | null> = {
  left: 'hierarchy',
  right: 'properties',
};

export const usePanelStore = create<PanelState>()(
  persist(
    (set, get) => ({
      tabConfigs: DEFAULT_TAB_CONFIGS,
      activeTabIds: DEFAULT_ACTIVE_TABS,

      getTabsForPanel: (panelId: PanelId) => {
        const { tabConfigs } = get();
        return Object.values(tabConfigs)
          .filter((c) => c.panelId === panelId)
          .sort((a, b) => a.order - b.order)
          .map((c) => c.id);
      },

      setActiveTab: (panelId: PanelId, tabId: string) => {
        set((state) => ({
          activeTabIds: { ...state.activeTabIds, [panelId]: tabId },
        }));
      },

      reorderTab: (tabId: string, toIndex: number) => {
        set((state) => {
          const tab = state.tabConfigs[tabId];
          if (!tab) return state;

          const panelTabs = Object.values(state.tabConfigs)
            .filter((c) => c.panelId === tab.panelId)
            .sort((a, b) => a.order - b.order);

          // Remove from current position and insert at new position
          const without = panelTabs.filter((c) => c.id !== tabId);
          without.splice(toIndex, 0, tab);

          const newConfigs = { ...state.tabConfigs };
          without.forEach((c, i) => {
            newConfigs[c.id] = { ...newConfigs[c.id], order: i };
          });

          return { tabConfigs: newConfigs };
        });
      },

      moveTab: (tabId: string, toPanelId: PanelId, toIndex: number) => {
        set((state) => {
          const existingTab = state.tabConfigs[tabId];
          if (!existingTab) return state;

          const fromPanelId = existingTab.panelId;

          // Get destination panel's tabs excluding the moving tab
          const destTabs = Object.values(state.tabConfigs)
            .filter((c) => c.panelId === toPanelId && c.id !== tabId)
            .sort((a, b) => a.order - b.order);

          // Re-assign orders for destination panel
          destTabs.splice(toIndex, 0, { id: tabId, panelId: toPanelId, order: 0 });
          const newConfigs = { ...state.tabConfigs };
          destTabs.forEach((c, i) => {
            newConfigs[c.id] = { ...newConfigs[c.id], panelId: toPanelId, order: i };
          });

          // Re-assign orders for source panel if changed
          if (fromPanelId !== toPanelId) {
            const srcTabs = Object.values(newConfigs)
              .filter((c) => c.panelId === fromPanelId)
              .sort((a, b) => a.order - b.order);
            srcTabs.forEach((c, i) => {
              newConfigs[c.id] = { ...newConfigs[c.id], order: i };
            });
          }

          // Update active tab of destination
          const newActiveTabIds = { ...state.activeTabIds };
          newActiveTabIds[toPanelId] = tabId;

          // If source panel now empty, clear active
          const srcRemaining = Object.values(newConfigs).filter(
            (c) => c.panelId === fromPanelId,
          );
          if (srcRemaining.length === 0) {
            newActiveTabIds[fromPanelId] = null;
          } else if (state.activeTabIds[fromPanelId] === tabId) {
            newActiveTabIds[fromPanelId] = srcRemaining[0].id;
          }

          return { tabConfigs: newConfigs, activeTabIds: newActiveTabIds };
        });
      },
    }),
    {
      name: 'kotonebot-devtools2-panels',
    },
  ),
);
