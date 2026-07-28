export interface MapPoint {
  id: number;
  lat: number;
  lng: number;
  title: string;
  address: string;
  categoryLabel: string;
  typeLabel: string;
  color: string;
}

export interface MapAdapter {
  setPoints: (points: MapPoint[]) => void;
  selectPoint: (pointId: number | null) => void;
  resize: () => void;
  destroy: () => void;
}

export interface MapAdapterOptions {
  container: HTMLElement;
  onSelectPoint: (pointId: number) => void;
}
