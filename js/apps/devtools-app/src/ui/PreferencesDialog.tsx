import React from "react";
import { Dialog, Classes, RadioGroup, Radio, Tabs, Tab, InputGroup, HTMLSelect } from "@blueprintjs/core";
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
  const { language, setLanguage, ai, setAiConfig } = usePreferencesStore();

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
          <Tab
            id="ai"
            title="AI"
            panel={
              <div style={{ padding: "0 20px" }}>
                <div style={{ marginBottom: 8, fontWeight: 600, fontSize: 16 }}>
                  {t('preferences.ai.title')}
                </div>
                <div style={{ marginBottom: 16, color: "#5c7080", fontSize: 13 }}>
                  {t('preferences.ai.description')}
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: "block", marginBottom: 4, fontWeight: 500, fontSize: 13 }}>
                    {t('preferences.ai.providerType')}
                  </label>
                  <HTMLSelect
                    value={ai.providerType}
                    onChange={(e) => setAiConfig({ providerType: e.currentTarget.value as typeof ai.providerType })}
                    style={{ width: "100%" }}
                  >
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="gemini">Gemini</option>
                  </HTMLSelect>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: "block", marginBottom: 4, fontWeight: 500, fontSize: 13 }}>
                    {t('preferences.ai.endpoint')}
                  </label>
                  <InputGroup
                    value={ai.endpoint}
                    onChange={(e) => setAiConfig({ endpoint: e.currentTarget.value })}
                    placeholder={t('preferences.ai.endpointPlaceholder')}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: "block", marginBottom: 4, fontWeight: 500, fontSize: 13 }}>
                    {t('preferences.ai.model')}
                  </label>
                  <InputGroup
                    value={ai.model}
                    onChange={(e) => setAiConfig({ model: e.currentTarget.value })}
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: "block", marginBottom: 4, fontWeight: 500, fontSize: 13 }}>
                    {t('preferences.ai.apiKey')}
                  </label>
                  <InputGroup
                    type="password"
                    value={ai.apiKey}
                    onChange={(e) => setAiConfig({ apiKey: e.currentTarget.value })}
                  />
                </div>
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
