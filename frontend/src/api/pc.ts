import request from '@/utils/request'

export const getExecutorList = (params?: { status?: string; search?: string; skip?: number; limit?: number }) => {
  return request({
    url: '/pc/executors/',
    method: 'get',
    params
  })
}

export const getExecutor = (id: number) => {
  return request({
    url: `/pc/executors/${id}`,
    method: 'get'
  })
}

export const updateExecutor = (id: number, data: { name?: string; is_active?: boolean }) => {
  return request({
    url: `/pc/executors/${id}`,
    method: 'patch',
    data
  })
}

export const deleteExecutor = (id: number) => {
  return request({
    url: `/pc/executors/${id}`,
    method: 'delete'
  })
}

export const wakeExecutor = (id: number) => {
  return request({
    url: `/pc/executors/${id}/wake`,
    method: 'post'
  })
}

export const dispatchTask = (caseId: number, executorId: number) => {
  return request({
    url: '/pc/tasks/dispatch',
    method: 'post',
    data: {
      case_id: caseId,
      executor_id: executorId
    }
  })
}

export const getTaskStatus = (taskId: number) => {
  return request({
    url: `/pc/tasks/${taskId}/status`,
    method: 'get'
  })
}