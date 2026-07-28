import UniverseCanvas from '@/components/domain/universe/UniverseCanvas';
import { useStageMeta } from '@/hooks/useStageMeta';
import { MOCK_UNIVERSE } from '@/stores/mock/universe';

/**
 * 성좌 뷰.
 *
 * TODO: 별 데이터는 useUniverse(workspaceId) 로 교체한다.
 * 지금은 목업을 페이지에서 들고 있어야 헤더의 개수와 캔버스가 어긋나지 않는다.
 */
const UniversePage = () => {
  const universe = MOCK_UNIVERSE;

  const memories =
    universe.constellations.reduce((sum, c) => sum + c.items.length, 0) +
    universe.unclassified.length;

  useStageMeta(`${memories} memories · ${universe.constellations.length} constellations`);

  return <UniverseCanvas data={universe} />;
};

export default UniversePage;
