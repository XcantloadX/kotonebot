import React from 'react';
import { Icon, Spinner } from '@blueprintjs/core';
import { useTranslation } from 'react-i18next';
import { editorActions } from '../editor/actions';
import { useAppStore } from '../editor/state';
import { useSymbolIndexStore } from '../editor/symbolIndexStore';
import {
  ProjectSymbolTreeGroupNode,
  ProjectSymbolTreeNode,
  ProjectSymbolTreeSymbolNode,
  ProjectSymbolTreeVariantNode,
} from '../model/symbolIndex';
import { toaster } from './toaster';

interface TreeRowProps {
  depth: number;
  label: string;
  icon: string;
  expanded?: boolean;
  onToggle?: () => void;
  onClick?: () => void;
}

const TreeRow: React.FC<TreeRowProps> = ({ depth, label, icon, expanded, onToggle, onClick }) => {
  return (
    <div
      role="treeitem"
      aria-expanded={typeof expanded === 'boolean' ? expanded : undefined}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 6px',
        paddingLeft: 0 + depth * 14,
        borderRadius: 4,
        minWidth: 0,
      }}
    >
      {typeof expanded === 'boolean' ? (
        <button
          type="button"
          onClick={onToggle}
          aria-label={expanded ? 'Collapse' : 'Expand'}
          style={{
            width: 20,
            minWidth: 20,
            height: 20,
            border: 'none',
            background: 'transparent',
            padding: 0,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon icon={expanded ? 'chevron-down' : 'chevron-right'} size={12} style={{ color: '#5c7080' }} />
        </button>
      ) : (
        <span style={{ width: 20 }} />
      )}
      <Icon icon={icon as any} size={12} style={{ color: '#5c7080', flexShrink: 0 }} />
      <button
        type="button"
        onClick={onClick}
        style={{
          flex: 1,
          textAlign: 'left',
          border: 'none',
          background: 'transparent',
          padding: 0,
          cursor: onClick ? 'pointer' : 'default',
          fontSize: 13,
          color: '#182026',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          minWidth: 0,
        }}
      >
        {label}
      </button>
    </div>
  );
};

function useExpandedState(nodes: ProjectSymbolTreeNode[]) {
  const defaultExpanded = React.useMemo(() => {
    const result = new Set<string>();
    for (const node of nodes) {
      if (node.kind === 'group') {
        result.add(`g:${node.label}`);
      }
    }
    return result;
  }, [nodes]);

  const [expanded, setExpanded] = React.useState<Set<string>>(defaultExpanded);

  React.useEffect(() => {
    setExpanded(defaultExpanded);
  }, [defaultExpanded]);

  const toggle = React.useCallback((key: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  return { expanded, toggle };
}

function normalizePath(path: string): string {
  return path.replace(/\\/g, '/').toLowerCase();
}

export const ProjectPanel: React.FC = () => {
  const { t } = useTranslation();
  const activeDocumentId = useAppStore((s) => s.activeDocumentId);
  const symbols = useSymbolIndexStore((s) => s.symbols);
  const tree = useSymbolIndexStore((s) => s.projectSymbolTree);
  const initialized = useSymbolIndexStore((s) => s.initialized);
  const { expanded, toggle } = useExpandedState(tree);

  const symbolMap = React.useMemo(() => {
    const map = new Map<string, (typeof symbols)[number]>();
    for (const symbol of symbols) {
      map.set(`${normalizePath(symbol.metaPath)}::${symbol.definitionId}`, symbol);
    }
    return map;
  }, [symbols]);

  const handleOpenVariantNode = React.useCallback(async (node: ProjectSymbolTreeVariantNode) => {
    const candidates = node.children
      .map((child) => symbolMap.get(`${normalizePath(child.metaPath)}::${child.definitionId}`))
      .filter((item): item is NonNullable<typeof item> => !!item);
    if (candidates.length === 0) {
      toaster.show({ message: t('projectPanel.symbolNotFound'), intent: 'warning' as any });
      return;
    }
    const preferred = activeDocumentId
      ? candidates.find((item) => normalizePath(item.imagePath) === normalizePath(activeDocumentId))
      : undefined;
    const symbol = preferred ?? candidates[0];
    if (candidates.length > 1 && !preferred) {
      toaster.show({ message: t('projectPanel.variantHasMultipleTargets'), intent: 'none' as any });
    }
    await editorActions.navigation.jumpToSymbol(symbol);
  }, [activeDocumentId, symbolMap, t]);

  const renderVariantNode = React.useCallback((node: ProjectSymbolTreeVariantNode, depth: number, symbolFullName: string) => {
    const variantKey = `v:${symbolFullName}:${node.label}`;
    const label = node.children.length > 1
      ? t('projectPanel.variantLabelWithCount', { variant: node.label, count: node.children.length })
      : t('projectPanel.variantLabel', { variant: node.label });
    return (
      <TreeRow
        key={variantKey}
        depth={depth}
        label={label}
        icon="layers"
        onClick={() => void handleOpenVariantNode(node)}
      />
    );
  }, [handleOpenVariantNode, t]);

  const renderSymbolNode = React.useCallback((node: ProjectSymbolTreeSymbolNode, depth: number) => {
    const symbolKey = `s:${node.fullName}`;
    const open = expanded.has(symbolKey);
    const label = node.displayName ? `${node.label} (${node.displayName})` : node.label;
    return (
      <React.Fragment key={symbolKey}>
        <TreeRow
          depth={depth}
          label={label}
          icon="symbol-triangle-up"
          expanded={open}
          onToggle={() => toggle(symbolKey)}
          onClick={() => toggle(symbolKey)}
        />
        {open ? node.children.map((variantNode) => renderVariantNode(variantNode, depth + 1, node.fullName)) : null}
      </React.Fragment>
    );
  }, [expanded, renderVariantNode, toggle]);

  const renderGroupNode = React.useCallback((node: ProjectSymbolTreeGroupNode, depth: number, parentPath: string) => {
    const path = parentPath ? `${parentPath}.${node.label}` : node.label;
    const groupKey = `g:${path}`;
    const open = expanded.has(groupKey);
    return (
      <React.Fragment key={groupKey}>
        <TreeRow
          depth={depth}
          label={node.label}
          icon="folder-close"
          expanded={open}
          onToggle={() => toggle(groupKey)}
          onClick={() => toggle(groupKey)}
        />
        {open
          ? node.children.map((child) => {
              if (child.kind === 'group') {
                return renderGroupNode(child, depth + 1, path);
              }
              return renderSymbolNode(child, depth + 1);
            })
          : null}
      </React.Fragment>
    );
  }, [expanded, renderSymbolNode, toggle]);

  if (!initialized) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spinner size={18} />
      </div>
    );
  }

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }} role="tree">
      {tree.length === 0 ? (
        <div style={{ color: '#5c7080', fontSize: 13, textAlign: 'center' }}>{t('projectPanel.empty')}</div>
      ) : (
        tree.map((node) => {
          if (node.kind === 'group') {
            return renderGroupNode(node, 0, '');
          }
          return renderSymbolNode(node, 0);
        })
      )}
    </div>
  );
};
