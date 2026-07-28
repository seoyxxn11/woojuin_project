import { createBrowserRouter, Navigate } from 'react-router-dom';
import AuthLayout from '@/layouts/AuthLayout';
import Layout from '@/layouts/Layout';
import StageLayout from '@/layouts/StageLayout';
import DesktopOnly from '@/layouts/DesktopOnly';
import PersonalSpacePage from '@/pages/PersonalSpacePage';
import WorkspacePage from '@/pages/WorkspacePage';
import ShareTargetPage from '@/pages/ShareTargetPage';
import LandingPage from '@/pages/LandingPage';
import UniversePage from '@/pages/UniversePage';
import LibraryPage from '@/pages/LibraryPage';
import MyPage from '@/pages/MyPage';
import TrashPage from '@/pages/TrashPage';
import MapPage from '@/pages/MapPage';
import CanvasPage from '@/pages/CanvasPage';
import LoginPage from '@/pages/LoginPage';
import SignupPage from '@/pages/SignupPage';
import OAuthCallbackPage from '@/pages/OAuthCallbackPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <LandingPage />,
  },
  { path: '/login', element: <LoginPage /> },
  { path: '/signup', element: <SignupPage /> },
  // 구글 OAuth 콜백 (백엔드 woojuin.oauth.redirect-base-url과 경로 일치 필요)
  { path: '/oauth/callback', element: <OAuthCallbackPage /> },
  // 로그인해야 들어갈 수 있는 앱 화면들 (사이드바 포함)
  {
    element: <AuthLayout />,
    children: [
      {
        element: <Layout />,
        children: [
          // 로그인 직후 도착지 — 개인 워크스페이스 성좌로 넘긴다
          { path: '/home', element: <PersonalSpacePage /> },
          // 워크스페이스에 속하지 않는 화면들 (모바일 탭바에서 진입)
          { path: '/my', element: <MyPage /> },
          { path: '/trash', element: <TrashPage /> },
          {
            path: '/workspace/:workspaceId',
            children: [
              // 뷰 없이 들어오면 성좌가 기본
              { index: true, element: <Navigate to="universe" replace /> },
              // 같은 워크스페이스를 다르게 보는 네 화면 — 상단 헤더(제목·뷰바)를 공유한다
              {
                element: <StageLayout />,
                children: [
                  { path: 'universe', element: <UniversePage /> },
                  { path: 'library', element: <LibraryPage /> },
                  { path: 'map', element: <MapPage /> },
                  // 한눈에 보기는 넓은 화면이 전제라 모바일에서는 성좌로 돌려보낸다
                  {
                    element: <DesktopOnly />,
                    children: [{ path: 'canvas', element: <CanvasPage /> }],
                  },
                ],
              },
              // 저장 API 확인용 임시 화면 — CommandBar 가 생기면 이 줄만 지운다
              { path: 'items', element: <WorkspacePage /> },
            ],
          },
        ],
      },
    ],
  },
  // Web Share Target 진입점 (manifest.share_target.action)
  // OS 공유 시트에서 바로 진입하는 화면이라 사이드바 없이 단독 렌더
  { path: '/share-target', element: <ShareTargetPage /> },
]);
