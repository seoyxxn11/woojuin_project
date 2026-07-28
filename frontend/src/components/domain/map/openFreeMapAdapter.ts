import {
  LngLatBounds,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  Popup,
  setWorkerUrl,
} from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import type { MapAdapter, MapAdapterOptions, MapPoint } from '@/components/domain/map/mapAdapter';

const OPEN_FREE_MAP_STYLE = 'https://tiles.openfreemap.org/styles/fiord';
const DEFAULT_CENTER: [number, number] = [127.7669, 35.9078];

setWorkerUrl(maplibreWorkerUrl);

const createPopupContent = (point: MapPoint) => {
  const content = document.createElement('article');
  content.className = 'woojuin-map-popup-content';

  const meta = document.createElement('div');
  meta.className = 'woojuin-map-popup-meta';

  const dot = document.createElement('span');
  dot.className = 'woojuin-map-popup-dot';
  dot.style.backgroundColor = point.color;

  const category = document.createElement('span');
  category.textContent = `#${point.categoryLabel} · ${point.typeLabel}`;

  const title = document.createElement('strong');
  title.textContent = point.title;

  const address = document.createElement('span');
  address.className = 'woojuin-map-popup-address';
  address.textContent = point.address;

  meta.append(dot, category);
  content.append(meta, title, address);
  return content;
};

export const createOpenFreeMapAdapter = ({
  container,
  onSelectPoint,
}: MapAdapterOptions): MapAdapter => {
  const map = new MapLibreMap({
    container,
    style: OPEN_FREE_MAP_STYLE,
    center: DEFAULT_CENTER,
    zoom: 6.2,
    attributionControl: { compact: true },
  });

  map.addControl(
    new NavigationControl({
      showCompass: false,
      showZoom: true,
    }),
    'bottom-right',
  );

  let points: MapPoint[] = [];
  let markers = new Map<number, { marker: Marker; element: HTMLButtonElement }>();
  let popup: Popup | null = null;
  let selectedPointId: number | null = null;

  const removePopup = () => {
    popup?.remove();
    popup = null;
  };

  const updateSelection = () => {
    markers.forEach(({ element }, id) => {
      const selected = id === selectedPointId;
      element.classList.toggle('is-selected', selected);
      element.setAttribute('aria-pressed', String(selected));
    });

    removePopup();
    if (selectedPointId === null) return;

    const point = points.find(({ id }) => id === selectedPointId);
    if (!point) return;

    popup = new Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 18,
      className: 'woojuin-map-popup',
    })
      .setLngLat([point.lng, point.lat])
      .setDOMContent(createPopupContent(point))
      .addTo(map);

    map.easeTo({
      center: [point.lng, point.lat],
      duration: 450,
    });
  };

  const fitPoints = () => {
    if (points.length === 0) return;

    const width = container.clientWidth;
    const height = container.clientHeight;
    if (width < 2 || height < 2) return;

    if (points.length === 1) {
      map.easeTo({ center: [points[0].lng, points[0].lat], zoom: 13, duration: 500 });
      return;
    }

    const isDesktop = width >= 640;
    const requestedPadding = isDesktop
      ? { top: 96, right: 390, bottom: 96, left: 72 }
      : { top: 72, right: 24, bottom: Math.round(height * 0.5), left: 24 };
    const horizontalBudget = width - 1;
    const verticalBudget = height - 1;
    const left = Math.min(requestedPadding.left, Math.floor(horizontalBudget / 2));
    const top = Math.min(requestedPadding.top, Math.floor(verticalBudget / 2));
    const padding = {
      top,
      right: Math.min(requestedPadding.right, horizontalBudget - left),
      bottom: Math.min(requestedPadding.bottom, verticalBudget - top),
      left,
    };

    const bounds = new LngLatBounds();
    points.forEach((point) => bounds.extend([point.lng, point.lat]));
    map.fitBounds(bounds, {
      padding,
      maxZoom: 14,
      duration: 650,
    });
  };

  return {
    setPoints(nextPoints) {
      markers.forEach(({ marker }) => marker.remove());
      markers = new Map();
      points = nextPoints;

      points.forEach((point) => {
        const markerAnchor = document.createElement('div');
        markerAnchor.className = 'woojuin-map-marker-anchor';

        const element = document.createElement('button');
        element.type = 'button';
        element.className = 'woojuin-map-marker';
        element.style.setProperty('--marker-color', point.color);
        element.setAttribute('aria-label', `${point.title} 지도 위치`);
        element.addEventListener('click', () => onSelectPoint(point.id));
        markerAnchor.append(element);

        const marker = new Marker({ element: markerAnchor, anchor: 'center' })
          .setLngLat([point.lng, point.lat])
          .addTo(map);

        markers.set(point.id, { marker, element });
      });

      updateSelection();
      fitPoints();
    },
    selectPoint(pointId) {
      selectedPointId = pointId;
      updateSelection();
    },
    resize() {
      map.resize();
    },
    destroy() {
      removePopup();
      markers.forEach(({ marker }) => marker.remove());
      markers.clear();
      map.remove();
    },
  };
};
