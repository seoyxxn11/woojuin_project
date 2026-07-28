import StagePlaceholder from '@/components/domain/stage/StagePlaceholder';

/**
 * 휴지통 — 삭제한 항목 복구·영구 삭제.
 *
 * 지금은 워크스페이스와 무관한 최상위 경로다. 삭제 항목이 워크스페이스별로
 * 나뉘어야 한다면 /workspace/:id/trash 로 옮긴다.
 * TODO: 목업 v3.5/trash-view.html 이식
 */
const TrashPage = () => <StagePlaceholder label="휴지통" />;

export default TrashPage;
