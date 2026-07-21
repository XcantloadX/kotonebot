import React from "react";
import { Icon, MenuItem, MenuDivider } from "@blueprintjs/core";
import { registerTabKind } from "./registry";
import { useAppStore } from "../state";
import { closeDocumentWithChecks } from "../actions/close";
import type { ITab } from "./types";
import { COMMAND_ID, executeCommand } from "../commands";
import i18n from "../../i18n";
import { WelcomePanel } from "../../ui/WelcomePanel";
import { StageView } from "../konva/StageView";
import { ConversionResultPanel } from "../../ui/ConversionResultPanel";

const WelcomeTab: React.FC = () => <WelcomePanel />;

const DocumentTab: React.FC<{ tab: ITab }> = () => <StageView />;

const ConversionResultTab: React.FC<{ tab: ITab }> = ({ tab }) => (
  <ConversionResultPanel tab={tab} />
);

registerTabKind("welcome", {
  component: WelcomeTab,
  icon: <Icon icon="home" />,
  defaultClosable: false,
});

registerTabKind("document", {
  component: DocumentTab,
  defaultClosable: true,
  onClose: async (tab) => {
    const docId = tab.metadata?.docId as string | undefined;
    if (!docId) return true;
    return closeDocumentWithChecks(docId);
  },
  isDirty: (tab) => {
    const state = useAppStore.getState();
    const docId = tab.metadata?.docId as string | undefined;
    return docId ? (state.documents[docId]?.dirty ?? false) : false;
  },
  contextMenuItems: (tab, ctx) => {
    const docId = tab.metadata?.docId as string | undefined;
    if (!docId) return [];
    return [
      <React.Fragment key="reveal">
        <MenuDivider />
        <MenuItem
          text={i18n.t("tabBar.revealInExplorer")}
          onClick={() => {
            void executeCommand(COMMAND_ID.FILE_REVEAL_IN_EXPLORER, ctx, { path: docId });
          }}
        />
      </React.Fragment>,
    ];
  },
});

registerTabKind("conversion-result", {
  component: ConversionResultTab,
  defaultClosable: true,
});
