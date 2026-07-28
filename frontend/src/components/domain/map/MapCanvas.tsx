import { useEffect, useMemo, useRef } from 'react';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { MapAdapter } from '@/components/domain/map/mapAdapter';
import { createOpenFreeMapAdapter } from '@/components/domain/map/openFreeMapAdapter';
import { MAP_CATEGORIES, MAP_ITEM_TYPE_LABEL } from '@/stores/mock/map';
import type { MapPlace } from '@/types/map';

interface MapCanvasProps {
  places: MapPlace[];
  selectedPlaceId: number | null;
  onSelectPlace: (placeId: number) => void;
}

const categoryById = new Map(MAP_CATEGORIES.map((category) => [category.id, category]));

const MapCanvas = ({ places, selectedPlaceId, onSelectPlace }: MapCanvasProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const adapterRef = useRef<MapAdapter | null>(null);
  const onSelectPlaceRef = useRef(onSelectPlace);
  onSelectPlaceRef.current = onSelectPlace;

  const points = useMemo(
    () =>
      places.map((place) => {
        const category = categoryById.get(place.categoryId);
        return {
          id: place.id,
          lat: place.lat,
          lng: place.lng,
          title: place.title,
          address: place.address,
          categoryLabel: category?.label ?? '미분류',
          typeLabel: MAP_ITEM_TYPE_LABEL[place.type],
          color: category?.color ?? 'var(--color-star-white)',
        };
      }),
    [places],
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const adapter = createOpenFreeMapAdapter({
      container,
      onSelectPoint: (pointId) => onSelectPlaceRef.current(pointId),
    });
    const resizeObserver = new ResizeObserver(() => adapter.resize());

    adapterRef.current = adapter;
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      adapter.destroy();
      adapterRef.current = null;
    };
  }, []);

  useEffect(() => {
    adapterRef.current?.setPoints(points);
  }, [points]);

  useEffect(() => {
    adapterRef.current?.selectPoint(selectedPlaceId);
  }, [selectedPlaceId]);

  return (
    <section
      aria-label="저장한 장소 지도"
      data-testid="map-canvas"
      className="absolute inset-0 overflow-hidden bg-space"
    >
      <div className="woojuin-open-free-map absolute inset-0">
        <div ref={containerRef} className="h-full w-full" />
      </div>
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(14,16,23,.14),transparent_38%,rgba(14,16,23,.08))]" />
      <div className="pointer-events-none absolute bottom-[calc(88px+env(safe-area-inset-bottom))] left-4 rounded-pill border border-border/70 bg-sidebar/65 px-3 py-1.5 text-[11px] font-semibold text-text-2 backdrop-blur-md desktop:bottom-5 desktop:left-5">
        OpenFreeMap · 장소 {places.length}곳
      </div>
    </section>
  );
};

export default MapCanvas;
