import { useEffect, useRef, useState } from 'react';
import {
  createUniverseScene,
  type LabelPosition,
  type ScreenPosition,
  type StarNode,
  type UniverseScene,
} from '@/utils/scene';
import type { Star, UniverseResponse } from '@/stores/mock/universe';
import ConstellationLabels from '@/components/domain/universe/ConstellationLabels';
import StarTooltip from '@/components/ui/StarTooltip';

interface UniverseCanvasProps {
  /**
   * 서버 응답. 생략하면 목업 데이터를 쓴다.
   * TODO: useUniverse(workspaceId) 로 받아 넘긴다
   */
  data?: UniverseResponse;
  /** 별자리 중심을 클릭 — 대시보드로 이동 */
  onSelectConstellation?: (categoryId: number) => void;
  /** URL 이 아닌 저장물을 클릭 — 상세 조회 API 호출 */
  onOpenItem?: (itemId: number) => void;
}

interface HoverState {
  node: StarNode;
  position: ScreenPosition;
}

/**
 * 성좌 뷰 — three.js 씬을 감싸는 얇은 래퍼.
 *
 * 씬은 자기 렌더 루프를 돌고, 여기서는 오버레이(라벨·툴팁) 위치만 상태로 받는다.
 * 별 자체는 React 가 그리지 않는다.
 */
const UniverseCanvas = ({ data, onSelectConstellation, onOpenItem }: UniverseCanvasProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<UniverseScene | null>(null);

  const [labels, setLabels] = useState<LabelPosition[]>([]);
  const [hover, setHover] = useState<HoverState | null>(null);

  /** 콜백이 매 렌더 바뀌어도 씬을 다시 만들지 않도록 ref 로 최신값만 넘긴다 */
  const handlersRef = useRef({ onSelectConstellation, onOpenItem });
  handlersRef.current = { onSelectConstellation, onOpenItem };

  /**
   * 클릭 분기 — url 이 있으면 바로 이동, 없으면 상세 조회.
   *
   * type 이 아니라 url 유무로 판단한다. type 이 URL 인데 url 이 비어 오는 경우
   * (크롤링 실패 등) 빈 탭이 열리는 대신 상세 화면으로 떨어진다.
   */
  const openStar = (star: Star) => {
    if (star.url) {
      window.open(star.url, '_blank', 'noopener,noreferrer');
      return;
    }
    handlersRef.current.onOpenItem?.(star.id);
  };

  const handleSelect = (node: StarNode) => {
    if (node.isHub && node.hub) {
      handlersRef.current.onSelectConstellation?.(node.hub.categoryId);
      return;
    }
    if (node.star) openStar(node.star);
  };

  const handleSelectRef = useRef(handleSelect);
  handleSelectRef.current = handleSelect;

  useEffect(() => {
    if (!canvasRef.current) return;

    const scene = createUniverseScene(
      canvasRef.current,
      {
        onLabels: setLabels,
        onHover: (node, position) => setHover(node && position ? { node, position } : null),
        onSelect: (node) => handleSelectRef.current(node),
      },
      data,
    );
    sceneRef.current = scene;

    return () => {
      scene.dispose();
      sceneRef.current = null;
    };
  }, [data]);

  return (
    <div className="relative h-full w-full overflow-hidden bg-space">
      <canvas ref={canvasRef} className="block h-full w-full" />

      <ConstellationLabels
        labels={labels}
        onSelect={(categoryId) => sceneRef.current?.focusOn(categoryId)}
      />

      {hover && (
        <StarTooltip
          node={hover.node}
          position={hover.position}
          onClick={() => handleSelectRef.current(hover.node)}
          onPointerOverChange={(over) => sceneRef.current?.setPointerOverTooltip(over)}
        />
      )}
    </div>
  );
};

export default UniverseCanvas;
