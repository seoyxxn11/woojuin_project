import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import Modal from '@/components/ui/Modal';
import SubmitButton from '@/components/ui/SubmitButton';
import TextInput from '@/components/ui/TextInput';
import { createWorkspace } from '@/services/workspaces';

interface CreateWorkspaceModalProps {
  open: boolean;
  onClose: () => void;
}

/** 사이드바 "New workspace" 클릭 시 뜨는 생성 폼 */
const CreateWorkspaceModal = ({ open, onClose }: CreateWorkspaceModalProps) => {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');

  const createMutation = useMutation({
    mutationFn: createWorkspace,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      setName('');
      onClose();
    },
  });

  const errorMessage = axios.isAxiosError(createMutation.error)
    ? (createMutation.error.response?.data?.message ?? '워크스페이스 생성에 실패했습니다')
    : null;

  return (
    <Modal open={open} onClose={onClose} title="새 워크스페이스">
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          createMutation.mutate({ name, type: 'TEAM' });
        }}
      >
        <TextInput
          type="text"
          placeholder="워크스페이스 이름"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
          required
        />
        {errorMessage && <p className="text-sm text-red-500">{errorMessage}</p>}
        <SubmitButton pending={createMutation.isPending} pendingLabel="생성 중...">
          만들기
        </SubmitButton>
      </form>
    </Modal>
  );
};

export default CreateWorkspaceModal;
