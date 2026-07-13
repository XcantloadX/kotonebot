import React from "react";
import { Dialog, Classes, RadioGroup, Radio, Tabs, Tab } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { usePreferencesStore } from "../preferences/preferencesStore";
import { LANGUAGE_OPTIONS } from "../i18n";
import { ShortcutButton } from "./components/ShortcutButton";

interface PreferencesDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PreferencesDialog: React.FC<PreferencesDialogProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const { language, setLanguage } = usePreferencesStore();

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={t('preferences.title')}
      style={{ width: 600 }}
      canOutsideClickClose={false}
    >
      <div className={Classes.DIALOG_BODY} style={{ padding: 0, minHeight: 280 }}>
        <Tabs
          id="preferences-tabs"
          vertical
          renderActiveTabPanelOnly
          defaultSelectedTabId="general"
        >
          <Tab
            id="general"
            title={t('preferences.general')}
            panel={
              <div style={{ padding: "0 20px" }}>
                <div style={{ marginBottom: 8, fontWeight: 600, fontSize: 16 }}>
                  {t('preferences.language')}
                </div>
                <div style={{ marginBottom: 16, color: "#5c7080", fontSize: 13 }}>
                  {t('preferences.languageDescription')}
                </div>
                <RadioGroup
                  selectedValue={language}
                  onChange={(e) => setLanguage(e.currentTarget.value as typeof language)}
                >
                  {LANGUAGE_OPTIONS.map((lang) => (
                    <Radio
                      key={lang}
                      label={
                        lang === 'system'
                          ? t('preferences.system')
                          : lang === 'zh-CN'
                            ? '中文'
                            : 'English'
                      }
                      value={lang}
                    />
                  ))}
                </RadioGroup>
              </div>
            }
          />
        </Tabs>
      </div>
      <div className={Classes.DIALOG_FOOTER}>
        <div className={Classes.DIALOG_FOOTER_ACTIONS}>
          <ShortcutButton onClick={onClose} shortcutText="Esc">
            {t('preferences.close')}
          </ShortcutButton>
        </div>
      </div>
    </Dialog>
  );
};
