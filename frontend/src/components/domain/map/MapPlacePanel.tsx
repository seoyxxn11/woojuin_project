import { useRef } from 'react';
import { MAP_CATEGORIES, MAP_ITEM_TYPE_LABEL } from '@/stores/mock/map';
import type { MapCategoryId, MapPlace } from '@/types/map';
import { classNames } from '@/utils/classNames';

interface MapPlacePanelProps {
  places: MapPlace[];
  activeCategories: Set<MapCategoryId>;
  collapsed: boolean;
  selectedPlaceId: number | null;
  onCollapsedChange: (collapsed: boolean) => void;
  onToggleCategory: (categoryId: MapCategoryId | 'all') => void;
  onSelectPlace: (placeId: number) => void;
}

const categoryById = new Map(MAP_CATEGORIES.map((category) => [category.id, category]));

const MapPlacePanel = ({
  places,
  activeCategories,
  collapsed,
  selectedPlaceId,
  onCollapsedChange,
  onToggleCategory,
  onSelectPlace,
}: MapPlacePanelProps) => {
  const dragStartYRef = useRef<number | null>(null);
  const ignoreClickRef = useRef(false);
  const allSelected = activeCategories.size === MAP_CATEGORIES.length;

  const handlePointerDown = (event: React.PointerEvent<HTMLButtonElement>) => {
    dragStartYRef.current = event.clientY;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLButtonElement>) => {
    const startY = dragStartYRef.current;
    dragStartYRef.current = null;
    if (startY === null) return;

    const distance = event.clientY - startY;
    if (Math.abs(distance) < 24) return;

    ignoreClickRef.current = true;
    onCollapsedChange(distance > 0);
  };

  const handleToggle = () => {
    if (ignoreClickRef.current) {
      ignoreClickRef.current = false;
      return;
    }
    onCollapsedChange(!collapsed);
  };

  return (
    <aside
      aria-label="저장한 장소"
      data-testid="map-place-panel"
      className={classNames(
        'absolute z-[9] flex flex-col overflow-hidden border border-border/55 shadow-float',
        'bg-sidebar/84 backdrop-blur-[14px] desktop:bg-sidebar/42 desktop:backdrop-blur-[8px]',
        'inset-x-3 bottom-[calc(88px+env(safe-area-inset-bottom))] rounded-lg transition-[height] duration-200 ease-out',
        collapsed ? 'h-[112px]' : 'h-[50%]',
        'desktop:inset-x-auto desktop:bottom-[26px] desktop:right-[26px] desktop:top-[84px] desktop:h-auto desktop:max-h-none desktop:w-[320px] desktop:rounded-lg',
      )}
    >
      <button
        type="button"
        aria-expanded={!collapsed}
        aria-label={collapsed ? '장소 목록 펼치기' : '장소 목록 접기'}
        onClick={handleToggle}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerCancel={() => {
          dragStartYRef.current = null;
          ignoreClickRef.current = false;
        }}
        className="flex h-7 shrink-0 touch-none items-center justify-center desktop:hidden"
      >
        <span
          aria-hidden="true"
          className="h-1 w-10 rounded-pill bg-text-3/70 transition-colors hover:bg-text-2"
        />
      </button>

      <header className="flex items-center bg-gradient-to-b from-sidebar/35 to-transparent px-4 pb-2 pt-3.5">
        <h2 className="text-sm font-extrabold text-text-1">저장한 장소</h2>
        <span className="ml-1.5 text-xs font-semibold text-text-3">{places.length}곳</span>
      </header>

      <div
        aria-label="장소 카테고리"
        className="scrollbar-none flex shrink-0 gap-1.5 overflow-x-auto px-3.5 pb-3 desktop:flex-wrap desktop:overflow-visible"
      >
        <button
          type="button"
          aria-pressed={allSelected}
          onClick={() => onToggleCategory('all')}
          className={classNames(
            'inline-flex shrink-0 items-center gap-1.5 rounded-pill border px-3 py-1.5 text-xs font-bold transition-colors',
            allSelected
              ? 'border-surface-3/90 bg-surface-3/90 text-text-1'
              : 'border-border/80 bg-surface/55 text-text-3 hover:bg-surface-2/75 hover:text-text-1',
          )}
        >
          <span aria-hidden="true" className="h-[7px] w-[7px] rounded-full bg-text-2" />
          전체
        </button>

        {MAP_CATEGORIES.map((category) => {
          const active = activeCategories.has(category.id);

          return (
            <button
              key={category.id}
              type="button"
              aria-pressed={active}
              onClick={() => onToggleCategory(category.id)}
              className={classNames(
                'inline-flex shrink-0 items-center gap-1.5 rounded-pill border px-3 py-1.5 text-xs font-bold transition-colors',
                active
                  ? 'border-surface-3/90 bg-surface-3/90 text-text-1'
                  : 'border-border/80 bg-surface/55 text-text-3 hover:bg-surface-2/75 hover:text-text-1',
              )}
            >
              <span
                aria-hidden="true"
                className={classNames(
                  'h-[7px] w-[7px] rounded-full transition-opacity',
                  active ? 'opacity-100' : 'opacity-35',
                )}
                style={{ backgroundColor: category.color }}
              />
              {category.label}
            </button>
          );
        })}
      </div>

      <div
        className={classNames(
          'min-h-0 flex-1 overflow-y-auto px-2 pb-3',
          collapsed && 'hidden desktop:block',
        )}
      >
        {places.length === 0 ? (
          <div className="grid h-full min-h-24 place-items-center px-5 text-center text-xs text-text-3">
            표시할 카테고리를 선택해 주세요.
          </div>
        ) : (
          places.map((place) => {
            const category = categoryById.get(place.categoryId);
            const selected = place.id === selectedPlaceId;

            return (
              <button
                key={place.id}
                type="button"
                onClick={() => onSelectPlace(place.id)}
                aria-pressed={selected}
                className={classNames(
                  'flex w-full cursor-pointer items-center gap-3 rounded-[11px] border px-2.5 py-2.5 text-left transition-colors',
                  selected
                    ? 'border-border/90 bg-surface-2/90'
                    : 'border-transparent bg-sidebar/10 hover:border-border/60 hover:bg-surface-2/65',
                )}
              >
                <span
                  aria-hidden="true"
                  className="h-[9px] w-[9px] shrink-0 rounded-full shadow-[0_0_3px_currentColor]"
                  style={{ backgroundColor: category?.color, color: category?.color }}
                />
                <span className="min-w-0 flex-1">
                  <strong className="block truncate text-[13px] font-semibold text-text-1">
                    {place.title}
                  </strong>
                  <span className="mt-0.5 block truncate text-[11px] text-text-3">
                    #{category?.label} · {MAP_ITEM_TYPE_LABEL[place.type]} · {place.address}
                  </span>
                </span>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
};

export default MapPlacePanel;
