import type { Item } from '@/types/item';
import { LinkArrowIcon } from '@/assets/icons';
import { resolveBrand, resolveThumbnail } from '@/utils/itemThumbnail';
import Spinner from '@/components/ui/Spinner';
import Thumbnail from './Thumbnail';
import MemoSkeleton from './MemoSkeleton';

/**
 * 카드 88px 정사각 안쪽 — 상태·타입에 따라 무엇을 그릴지 고르는 디스패처.
 *
 * 표시 조각(Spinner·MemoSkeleton·Thumbnail)은 각자 순수 UI 이고, 썸네일 소스
 * 해석은 resolveThumbnail 이 끝냈다. 여기서는 "어느 조각을 언제 쓸지"만 정한다.
 * 카드 껍데기(레이아웃·제목·라벨)와 책임을 나눠 SRP 를 지킨다.
 */
const ItemSquare = ({ item }: { item: Item }) => {
  if (item.status === 'PROCESSING') {
    return (
      <div className="grid h-full place-items-center">
        <Spinner className="h-[22px] w-[22px]" />
      </div>
    );
  }

  if (item.type === 'MEMO') return <MemoSkeleton />;

  return (
    <>
      <Thumbnail
        src={resolveThumbnail(item)}
        brand={resolveBrand(item)}
        seed={item.itemId}
        className="absolute inset-0"
      />
      {/* URL 은 항상 우상단 링크 배지 (목업 dashboard.html) */}
      {item.type === 'URL' && (
        <div className="absolute right-[7px] top-[7px] grid h-5 w-5 place-items-center rounded-md bg-space/70 [&>svg]:h-3 [&>svg]:w-3">
          <LinkArrowIcon className="text-text-1" />
        </div>
      )}
    </>
  );
};

export default ItemSquare;
