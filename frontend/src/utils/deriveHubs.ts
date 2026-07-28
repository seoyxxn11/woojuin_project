import { type Constellation, type Vec3 } from '@/stores/mock/universe';

/**
 * 카테고리(별자리)의 위치·크기는 서버가 주지 않는다.
 * **소속 아이템들의 중심**을 카테고리 위치로 삼는다.
 * 아이템이 추가·삭제되면 별자리가 자연스럽게 그쪽으로 움직인다.
 */
export interface Hub {
  categoryId: number;
  name: string;
  color: number;
  /** 소속 아이템 좌표의 평균 */
  position: Vec3;
  /** 아이템 수에 비례 — 큰 별자리가 크게 보인다 */
  radius: number;
  itemCount: number;
}

/** 허브 크기 범위 (v3.5 목업의 1.5~2.7 을 따른다) */
const MIN_RADIUS = 1.5;
const MAX_RADIUS = 2.7;
/** 이 개수 이상이면 최대 크기 */
const RADIUS_SATURATION = 12;

function hubRadius(itemCount: number): number {
  const t = Math.min(itemCount, RADIUS_SATURATION) / RADIUS_SATURATION;
  return MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * t;
}

/** 아이템이 하나도 없는 별자리는 위치를 정할 수 없으므로 건너뛴다 */
export function deriveHubs(constellations: Constellation[]): Hub[] {
  return constellations
    .filter((c) => c.items.length > 0)
    .map((c) => {
      const sum = c.items.reduce<Vec3>(
        (acc, item) => [
          acc[0] + item.position[0],
          acc[1] + item.position[1],
          acc[2] + item.position[2],
        ],
        [0, 0, 0],
      );
      const n = c.items.length;
      return {
        categoryId: c.categoryId,
        name: c.categoryName,
        color: c.color,
        position: [sum[0] / n, sum[1] / n, sum[2] / n] as Vec3,
        radius: hubRadius(n),
        itemCount: n,
      };
    });
}

function distance(a: Hub, b: Hub): number {
  return Math.hypot(
    a.position[0] - b.position[0],
    a.position[1] - b.position[1],
    a.position[2] - b.position[2],
  );
}

/**
 * 별자리끼리 잇는 선 — **최소 신장 트리(MST)**.
 *
 * 모든 쌍을 이으면 N(N-1)/2 개(10개 → 45개)라 화면이 거미줄이 된다.
 * MST 는 정확히 N-1 개 선으로 **모든 별자리를 하나로 연결**하면서,
 * 가까운 것끼리 잇기 때문에 별자리다운 모양이 나온다.
 *
 * Prim 알고리즘 — 별자리 수가 수십 개 수준이라 O(N²) 로 충분하다.
 */
export function buildHubLinks(hubs: Hub[]): [number, number][] {
  if (hubs.length < 2) return [];

  const connected = new Set<number>([0]);
  const links: [number, number][] = [];

  // 연결된 무리에서 가장 가까운 바깥 별자리를 하나씩 끌어들인다
  while (connected.size < hubs.length) {
    let from = -1;
    let to = -1;
    let min = Infinity;

    for (const i of connected) {
      for (let j = 0; j < hubs.length; j++) {
        if (connected.has(j)) continue;
        const d = distance(hubs[i], hubs[j]);
        if (d < min) {
          min = d;
          from = i;
          to = j;
        }
      }
    }

    links.push([hubs[from].categoryId, hubs[to].categoryId]);
    connected.add(to);
  }

  return links;
}
