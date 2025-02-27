import { EditorOverlay, OverlayProps } from '../core/types';
import RectMask from '../RectMask';

const RectMaskComponent: React.FC<OverlayProps> = ({ editorState: [state], editorProps }) => {
  if (!editorProps.enableMask || editorProps.annotations.length === 0) {
    return null;
  }

  return (
    <RectMask
      rects={editorProps.annotations.map(anno => ({
        ...anno.data
      }))}
      alpha={editorProps.maskAlpha || 0.5}
      transition={true}
      scale={state.imageScale}
      transform={{
        x: state.imagePosition.x,
        y: state.imagePosition.y,
        width: editorProps.imageSize?.width || 0,
        height: editorProps.imageSize?.height || 0
      }}
    />
  );
};

export const RectMaskOverlay: EditorOverlay = {
  name: 'rectMask',
  zIndex: 10,
  component: RectMaskComponent
};

export default RectMaskOverlay;