import mainIcon from '@/assets/mainIcon.svg';
import LogoMiniText from '@/components/ui/LogoMiniText';
import { classNames } from '@/utils/classNames';

interface BrandMarkProps {
  /** 로고 한 변 (px) — 랜딩 헤더는 30, 사이드바는 28 */
  size?: number;
  className?: string;
}

/** 로고 + 서비스명 — 랜딩 헤더·로그인 화면이 함께 쓴다 */
const BrandMark = ({ size = 30, className }: BrandMarkProps) => (
  <div className={classNames('flex items-center gap-2.5', className)}>
    <img
      src={mainIcon}
      alt="우주인 로고"
      style={{ width: size, height: size }}
      className="block shrink-0 rounded-[9px]"
    />
    <LogoMiniText text="WooJuIn" />
  </div>
);

export default BrandMark;
