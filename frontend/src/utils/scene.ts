import * as THREE from 'three';
import {
  MOCK_UNIVERSE,
  STAR_RADIUS,
  UNCLASSIFIED_COLOR,
  type Star,
  type UniverseResponse,
} from '@/stores/mock/universe';
import { buildHubLinks, deriveHubs, type Hub } from './deriveHubs';

/**
 * 성좌 3D 씬 — v3.5/my-universe.html 의 three.js 로직 기반.
 *
 * 데이터 구조:
 *   - 아이템(별)은 서버가 준 좌표에 그대로 찍는다
 *   - 카테고리(별자리)는 소속 아이템의 중심을 계산해서 찍는다
 *   - 선은 별자리↔별자리(MST), 아이템→자기 별자리. 미분류는 선이 없다
 *
 * React 밖에 두는 이유: 매 프레임 도는 렌더 루프를 React 상태로 올리면
 * 초당 60번 리렌더가 발생한다. 씬은 자기 루프를 돌고,
 * 바깥에는 "호버/선택/라벨 위치"만 콜백으로 알린다.
 */

/** 화면에 떠 있는 별 하나 */
export interface StarNode {
  /** 별자리 중심이면 Hub, 저장물이면 Star */
  hub?: Hub;
  star?: Star;
  isHub: boolean;
  /** 소속 별자리 이름 — 미분류면 null */
  categoryName: string | null;
  /** 툴팁 점 색 */
  cssColor: string;
}

export interface ScreenPosition {
  x: number;
  y: number;
  /** 카메라 뒤로 넘어가면 false */
  visible: boolean;
}

export interface LabelPosition extends ScreenPosition {
  categoryId: number;
  name: string;
}

export interface SceneCallbacks {
  onLabels: (labels: LabelPosition[]) => void;
  onHover: (node: StarNode | null, pos: ScreenPosition | null) => void;
  onSelect: (node: StarNode) => void;
}

export interface UniverseScene {
  focusOn: (categoryId: number) => void;
  setPointerOverTooltip: (over: boolean) => void;
  dispose: () => void;
}

/* ── 내부 유틸 ─────────────────────────────────────────── */

function makeGlowTexture(): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.2, 'rgba(255,255,255,.85)');
  grad.addColorStop(0.45, 'rgba(255,255,255,.28)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

interface StarObject extends StarNode {
  glow: THREE.Sprite;
  core: THREE.Sprite;
  hit: THREE.Mesh;
  position: THREE.Vector3;
  baseRadius: number;
}

/* ── 씬 생성 ──────────────────────────────────────────── */

export function createUniverseScene(
  canvas: HTMLCanvasElement,
  callbacks: SceneCallbacks,
  data: UniverseResponse = MOCK_UNIVERSE,
): UniverseScene {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 600);
  /** 카메라 거리 범위 — 휠·핀치 줌이 공유한다 */
  const CAM_MIN = 30;
  const CAM_MAX = 120;
  let camZ = 62;
  camera.position.set(0, 0, camZ);

  const universe = new THREE.Group();
  scene.add(universe);

  const glowTex = makeGlowTexture();
  const disposables: { dispose: () => void }[] = [glowTex, renderer];

  /* 배경 별먼지 — 성좌를 가리지 않도록 반경 135~210 바깥쪽에만 */
  function addStarShell(count: number, radius: number, size: number, opacity: number) {
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = 6.283 * u;
      const phi = Math.acos(2 * v - 1);
      const r = radius * (0.92 + Math.random() * 0.16);
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({
      color: 0xffffff,
      size,
      map: glowTex,
      alphaTest: 0.01,
      transparent: true,
      opacity,
      depthWrite: false,
    });
    disposables.push(geo, mat);
    universe.add(new THREE.Points(geo, mat));
  }
  addStarShell(1400, 210, 0.55, 0.35);
  addStarShell(900, 170, 0.9, 0.5);
  addStarShell(400, 135, 1.5, 0.6);

  /* ── 카테고리 위치 계산 ──────────────────────────── */
  const hubs = deriveHubs(data.constellations);
  const hubById = new Map<number, StarObject>();

  /* 성좌 전체를 원점에 맞춘다 (별자리 중심들의 평균) */
  const center = new THREE.Vector3();
  hubs.forEach((h) => center.add(new THREE.Vector3(...h.position)));
  if (hubs.length > 0) center.multiplyScalar(1 / hubs.length);

  const nodes: StarObject[] = [];

  function addStar(
    worldPosition: [number, number, number],
    radius: number,
    colorHex: number,
    node: Omit<StarNode, 'cssColor'>,
  ): StarObject {
    const color = new THREE.Color(colorHex);
    const pos = new THREE.Vector3(...worldPosition).sub(center);

    const glowMat = new THREE.SpriteMaterial({
      map: glowTex,
      color,
      blending: THREE.AdditiveBlending,
      transparent: true,
      depthWrite: false,
      opacity: 0.65,
    });
    const glow = new THREE.Sprite(glowMat);
    const gs = radius * 2.3;
    glow.scale.set(gs, gs, 1);
    glow.position.copy(pos);
    universe.add(glow);

    /* 중심은 흰색 — 검은 배경에서 가장 밝은 점이 된다 */
    const coreMat = new THREE.SpriteMaterial({
      map: glowTex,
      color: 0xffffff,
      blending: THREE.AdditiveBlending,
      transparent: true,
      depthWrite: false,
    });
    const core = new THREE.Sprite(coreMat);
    const cs = radius * 1.4;
    core.scale.set(cs, cs, 1);
    core.position.copy(pos);
    universe.add(core);

    /* 클릭·호버 판정용 (보이지 않는 구) */
    const hitGeo = new THREE.SphereGeometry(Math.max(radius, 1.5), 8, 8);
    const hitMat = new THREE.MeshBasicMaterial({ visible: false });
    const hit = new THREE.Mesh(hitGeo, hitMat);
    hit.position.copy(pos);
    universe.add(hit);

    disposables.push(glowMat, coreMat, hitGeo, hitMat);

    const starObject: StarObject = {
      ...node,
      cssColor: `#${color.getHexString()}`,
      glow,
      core,
      hit,
      position: pos,
      baseRadius: radius,
    };
    hit.userData.node = starObject;
    nodes.push(starObject);
    return starObject;
  }

  /* 별자리 중심 */
  hubs.forEach((hub) => {
    hubById.set(
      hub.categoryId,
      addStar(hub.position, hub.radius, hub.color, {
        hub,
        isHub: true,
        categoryName: hub.name,
      }),
    );
  });

  /* 저장물 — 서버가 준 좌표 그대로 */
  data.constellations.forEach((constellation) => {
    const colorHex = constellation.color;
    constellation.items.forEach((star) => {
      const node = addStar(star.position, STAR_RADIUS, colorHex, {
        star,
        isHub: false,
        categoryName: constellation.categoryName,
      });
      /* 아이템 → 자기 별자리 연결선 */
      const hub = hubById.get(constellation.categoryId);
      if (hub) {
        const geo = new THREE.BufferGeometry().setFromPoints([hub.position, node.position]);
        const mat = new THREE.LineBasicMaterial({
          color: colorHex,
          transparent: true,
          opacity: 0.13,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        });
        disposables.push(geo, mat);
        universe.add(new THREE.Line(geo, mat));
      }
    });
  });

  /* 미분류 — 흰 별, 연결선 없음 */
  data.unclassified.forEach((star) => {
    addStar(star.position, STAR_RADIUS, UNCLASSIFIED_COLOR, {
      star,
      isHub: false,
      categoryName: null,
    });
  });

  /* 별자리끼리 (MST) — 그라디언트로 양쪽 색을 잇는다 */
  buildHubLinks(hubs).forEach(([a, b]) => {
    const from = hubById.get(a);
    const to = hubById.get(b);
    if (!from || !to) return;
    const ca = new THREE.Color(from.hub!.color);
    const cb = new THREE.Color(to.hub!.color);
    const geo = new THREE.BufferGeometry().setFromPoints([from.position, to.position]);
    geo.setAttribute(
      'color',
      new THREE.BufferAttribute(new Float32Array([ca.r, ca.g, ca.b, cb.r, cb.g, cb.b]), 3),
    );
    const mat = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.26,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    disposables.push(geo, mat);
    universe.add(new THREE.Line(geo, mat));
  });

  /* ── 상호작용 ────────────────────────────────────── */
  const rot = { x: -0.15, y: 0.2 };
  const targetRot = { x: -0.15, y: 0.2 };
  let dragging = false;
  let moved = false;
  let last = { x: 0, y: 0 };
  let hovered: StarObject | null = null;
  let overTooltip = false;
  let focused: StarObject | null = null;

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function project(p: THREE.Vector3): ScreenPosition {
    const r = canvas.getBoundingClientRect();
    const v = p.clone().applyMatrix4(universe.matrixWorld).project(camera);
    return {
      x: (v.x * 0.5 + 0.5) * r.width,
      y: (-v.y * 0.5 + 0.5) * r.height,
      visible: v.z < 1,
    };
  }

  /** 화면 좌표에서 별을 찾는다 */
  function pickAt(clientX: number, clientY: number): StarObject | null {
    const r = canvas.getBoundingClientRect();
    pointer.x = ((clientX - r.left) / r.width) * 2 - 1;
    pointer.y = -((clientY - r.top) / r.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(nodes.map((n) => n.hit));
    return hits.length ? (hits[0].object.userData.node as StarObject) : null;
  }

  const onPointerDown = (e: PointerEvent) => {
    // 두 손가락은 핀치 줌이므로 회전 시작으로 치지 않는다
    if (e.pointerType === 'touch' && activeTouches >= 2) return;
    dragging = true;
    focused = null;
    moved = false;
    last = { x: e.clientX, y: e.clientY };
    canvas.style.cursor = 'grabbing';
  };

  const onPointerUp = () => {
    dragging = false;
    canvas.style.cursor = 'grab';
  };

  const onPointerMove = (e: PointerEvent) => {
    if (dragging) {
      const dx = e.clientX - last.x;
      const dy = e.clientY - last.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
      targetRot.y += dx * 0.005;
      targetRot.x += dy * 0.005;
      targetRot.x = Math.max(-1.1, Math.min(1.1, targetRot.x));
      last = { x: e.clientX, y: e.clientY };
      if (hovered) {
        hovered = null;
        callbacks.onHover(null, null);
      }
      return;
    }

    // 호버 툴팁은 마우스 전용. 터치는 탭하면 바로 열리므로 툴팁 단계가 없다
    if (e.pointerType === 'touch') return;

    const node = pickAt(e.clientX, e.clientY);
    if (node) {
      canvas.style.cursor = 'pointer';
      if (node !== hovered) {
        hovered = node;
        callbacks.onHover(node, project(node.position));
      }
    } else if (!overTooltip) {
      hovered = null;
      canvas.style.cursor = 'grab';
      callbacks.onHover(null, null);
    }
  };

  /**
   * 드래그로 회전한 경우는 클릭으로 치지 않는다.
   * 좌표로 직접 찾기 때문에 호버 상태가 없는 터치에서도 동작한다.
   */
  const onClick = (e: MouseEvent) => {
    if (moved) return;
    const node = hovered ?? pickAt(e.clientX, e.clientY);
    if (node) callbacks.onSelect(node);
  };

  const onWheel = (e: WheelEvent) => {
    e.preventDefault();
    camZ = Math.max(CAM_MIN, Math.min(CAM_MAX, camZ + e.deltaY * 0.04));
  };

  /* ── 핀치 줌 ─────────────────────────────────────── */
  let activeTouches = 0;
  let pinchDistance = 0;

  const touchDistance = (t: TouchList) =>
    Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);

  const onTouchStart = (e: TouchEvent) => {
    activeTouches = e.touches.length;
    if (activeTouches >= 2) {
      dragging = false; // 두 손가락이면 회전을 멈춘다
      pinchDistance = touchDistance(e.touches);
    }
  };

  const onTouchMove = (e: TouchEvent) => {
    if (e.touches.length < 2) return;
    e.preventDefault();
    const d = touchDistance(e.touches);
    if (pinchDistance) {
      camZ = Math.max(CAM_MIN, Math.min(CAM_MAX, camZ * (pinchDistance / d)));
    }
    pinchDistance = d;
    moved = true; // 핀치 후 손을 떼도 클릭으로 오인하지 않게
  };

  const onTouchEnd = (e: TouchEvent) => {
    activeTouches = e.touches.length;
    if (activeTouches < 2) pinchDistance = 0;
  };

  canvas.addEventListener('pointerdown', onPointerDown);
  window.addEventListener('pointerup', onPointerUp);
  canvas.addEventListener('pointermove', onPointerMove);
  canvas.addEventListener('click', onClick);
  canvas.addEventListener('wheel', onWheel, { passive: false });
  canvas.addEventListener('touchstart', onTouchStart, { passive: true });
  canvas.addEventListener('touchmove', onTouchMove, { passive: false });
  canvas.addEventListener('touchend', onTouchEnd, { passive: true });
  canvas.addEventListener('touchcancel', onTouchEnd, { passive: true });

  canvas.style.cursor = 'grab';
  // 브라우저 기본 제스처(페이지 스크롤·더블탭 확대)를 막아야 회전·핀치가 먹는다
  canvas.style.touchAction = 'none';

  /* ── 리사이즈 ────────────────────────────────────── */
  function resize() {
    const parent = canvas.parentElement;
    if (!parent) return;
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    if (w === 0 || h === 0) return;
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  const resizeObserver = new ResizeObserver(resize);
  if (canvas.parentElement) resizeObserver.observe(canvas.parentElement);
  resize();

  /* ── 렌더 루프 ───────────────────────────────────── */
  let raf = 0;
  let prev = performance.now();

  function animate(now: number) {
    const dt = (now - prev) / 1000;
    prev = now;

    // 아무것도 안 건드리면 천천히 자전한다
    if (!dragging && !hovered && !focused) targetRot.y += 0.02 * dt;
    rot.x += (targetRot.x - rot.x) * 0.08;
    rot.y += (targetRot.y - rot.y) * 0.08;
    universe.rotation.x = rot.x;
    universe.rotation.y = rot.y;
    camera.position.z += (camZ - camera.position.z) * 0.1;

    // 별 맥동 — 포커스된 별은 1.5배
    const t = now / 1000;
    nodes.forEach((n, i) => {
      const focusScale = n === focused ? 1.5 : 1;
      const pulse = (1 + 0.13 * Math.sin(t * 1.8 + i * 0.7)) * focusScale;
      const cs = n.baseRadius * 1.4 * pulse;
      n.core.scale.set(cs, cs, 1);
      n.glow.material.opacity =
        (n === hovered || n === focused ? 0.95 : 0.6) + 0.05 * Math.sin(t * 2 + i);
    });

    renderer.render(scene, camera);

    // 오버레이(라벨·툴팁) 위치를 바깥에 알린다
    callbacks.onLabels(
      hubs.map((h) => {
        const star = hubById.get(h.categoryId)!;
        const p = project(star.position);
        return {
          categoryId: h.categoryId,
          name: h.name,
          x: p.x + star.baseRadius * 4,
          y: p.y,
          visible: p.visible,
        };
      }),
    );
    if (hovered) callbacks.onHover(hovered, project(hovered.position));

    raf = requestAnimationFrame(animate);
  }
  raf = requestAnimationFrame(animate);

  /* ── 외부 API ────────────────────────────────────── */
  return {
    focusOn(categoryId) {
      const star = hubById.get(categoryId);
      if (!star) return;
      focused = star;
      const p = star.position;
      targetRot.y = Math.atan2(-p.x, p.z);
      const horizon = Math.hypot(p.x, p.z);
      targetRot.x = Math.max(-1.1, Math.min(1.1, Math.atan2(p.y, horizon)));
      camZ = 40;
    },
    setPointerOverTooltip(over) {
      overTooltip = over;
    },
    dispose() {
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      canvas.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointerup', onPointerUp);
      canvas.removeEventListener('pointermove', onPointerMove);
      canvas.removeEventListener('click', onClick);
      canvas.removeEventListener('wheel', onWheel);
      canvas.removeEventListener('touchstart', onTouchStart);
      canvas.removeEventListener('touchmove', onTouchMove);
      canvas.removeEventListener('touchend', onTouchEnd);
      canvas.removeEventListener('touchcancel', onTouchEnd);
      disposables.forEach((d) => d.dispose());
    },
  };
}
