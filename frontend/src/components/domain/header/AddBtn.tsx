import GlassButton from '@/components/ui/GlassButton';
import HeaderPopover from '@/components/ui/HeaderPopover';
import { PlusIcon } from '@/assets/icons';
import AddModal from '@/components/domain/header/AddModal';

/**
 * 헤더의 "새로 만들기" 버튼 — 누르면 아래로 팝오버가 뜬다.
 *
 * HeaderPopover 가 여닫기·바깥클릭·ESC 를, AddModal 이 내용물을 맡는다.
 * 저장이 끝나면 close 로 팝오버를 닫는다.
 */
const AddBtn = () => (
  <HeaderPopover trigger={<GlassButton icon={<PlusIcon />} aria-label="새로 만들기" />}>
    {(close) => <AddModal onDone={close} />}
  </HeaderPopover>
);

export default AddBtn;
