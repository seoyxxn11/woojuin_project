import { classNames } from '@/utils/classNames';
import type { Brand } from '@/utils/itemThumbnail';

/** src·brand 둘 다 없을 때 까는 그라디언트 폴백 — seed 로 골라 카드마다 색이 다르게 */
const GRADIENTS = [
  'linear-gradient(135deg,#26314a,#151d33)',
  'linear-gradient(135deg,#3a2f4a,#1e1830)',
  'linear-gradient(135deg,#1f3a35,#122019)',
  'linear-gradient(135deg,#4a3226,#241812)',
  'linear-gradient(135deg,#443d1e,#221e10)',
];

interface ThumbnailProps {
  /** 이미 해석된 이미지 URL. 없으면 브랜드 타일 → 그라디언트 순으로 폴백 */
  src: string | null;
  /** 폴백 색을 고르는 씨앗 (보통 itemId) */
  seed: number;
  /** 이미지가 없을 때 쓸 브랜드 타일(쿠팡 등). 없으면 그라디언트 */
  brand?: Brand | null;
  className?: string;
}

/**
 * 썸네일 — 이미 정해진 src·brand 만 받는 순수 UI. Item·s3Key 를 모른다.
 * 그 해석은 utils/itemThumbnail 이 하고, 여기서는 "무엇이 있으면 무엇을 그릴지"만 정한다.
 *
 * 폴백이 2단인 이유: 랜덤 그라디언트는 예쁘지만 정보량이 0이다. 크롤링이 구조적으로 막혀
 * 썸네일을 영구히 못 얻는 쇼핑몰 링크는 최소한 "어느 쇼핑몰인지"는 알려주는 편이 낫다.
 */
const Thumbnail = ({ src, seed, brand, className }: ThumbnailProps) => {
  if (src) {
    return (
      <div
        className={classNames('bg-cover bg-center', className)}
        style={{ backgroundImage: `url(${src})` }}
      />
    );
  }

  if (brand) {
    return (
      <div
        className={classNames('grid place-items-center', className)}
        style={{ background: brand.background }}
      >
        <span className="px-1 text-center text-[11px] font-bold leading-tight text-white/95">
          {brand.label}
        </span>
      </div>
    );
  }

  return (
    <div
      className={classNames(className)}
      style={{ background: GRADIENTS[seed % GRADIENTS.length] }}
    />
  );
};

export default Thumbnail;
