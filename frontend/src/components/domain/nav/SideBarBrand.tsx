import mainIcon from '@/assets/mainIcon.svg';
import LogoMiniText from '@/components/ui/LogoMiniText';
import { classNames } from '@/utils/classNames';
import { useSideBar } from '@/stores/context/SideBarContext';

/** 로고 + 사이드바 열고 닫기 버튼 */
const SideBarBrand = () => {
  const { sideBarClosed, toggleSideBar } = useSideBar();

  return (
    <section
      className={classNames(
        'flex items-center gap-2.5',
        sideBarClosed ? 'flex-col justify-center pt-1 pb-4' : 'px-2.5 pt-1 pb-5',
      )}
    >
      <img className="w-7 h-7 rounded-sm block shrink-0" src={mainIcon} alt="우주인 로고" />
      {!sideBarClosed && <LogoMiniText text="WooJuIn" />}
      <button
        type="button"
        onClick={toggleSideBar}
        aria-label={sideBarClosed ? '사이드바 펼치기' : '사이드바 접기'}
        className={classNames(
          'grid place-items-center w-[26px] h-[26px] rounded-sm text-[13px] cursor-pointer',
          'border border-border text-text-3 hover:text-text-1 hover:border-accent transition-colors',
          !sideBarClosed && 'ml-auto',
        )}
      >
        {sideBarClosed ? '»' : '«'}
      </button>
    </section>
  );
};

export default SideBarBrand;
