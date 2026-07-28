import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeftIcon } from '@/assets/icons';
import { classNames } from '@/utils/classNames';

interface BackButtonProps {
  /** 되돌아갈 곳이 없을 때 갈 경로 */
  fallback?: string;
  className?: string;
}

/**
 * 뒤로 가기.
 *
 * 히스토리가 있으면 한 칸 뒤로, 없으면 fallback 으로 간다.
 * 링크를 직접 열었거나 설치된 PWA 로 바로 진입한 경우 navigate(-1) 은
 * 앱 밖으로 나가버리거나 아무 일도 일어나지 않는다.
 * location.key 가 'default' 면 라우터 기준 첫 화면이라는 뜻이다.
 */
const BackButton = ({ fallback = '/', className }: BackButtonProps) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isFirstEntry = location.key === 'default';

  return (
    <button
      type="button"
      aria-label="뒤로 가기"
      onClick={() => (isFirstEntry ? navigate(fallback) : navigate(-1))}
      className={classNames(
        'grid h-10 w-10 cursor-pointer place-items-center rounded-md text-text-3',
        'transition-colors hover:bg-surface-2 hover:text-text-1',
        '[&>svg]:h-5 [&>svg]:w-5',
        className,
      )}
    >
      <ArrowLeftIcon />
    </button>
  );
};

export default BackButton;
