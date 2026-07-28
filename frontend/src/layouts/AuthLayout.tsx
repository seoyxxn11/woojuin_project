import { Outlet, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAtomValue } from 'jotai';
import { accessTokenAtom } from '@/stores/authAtoms';

const AuthLayout = () => {
  const accessToken = useAtomValue(accessTokenAtom);
  const navigate = useNavigate();

  useEffect(() => {
    if (!accessToken) {
      navigate('/', { replace: true });
    }
  }, [accessToken, navigate]);

  if (!accessToken) return null;

  return (
    <>
      <Outlet />
    </>
  );
};

export default AuthLayout;
