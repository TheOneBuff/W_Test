import request from '@/utils/request'

export const dispatchTask = (caseId: number) => {
  return request({
    url: `/api/android/dispatch/${caseId}`,
    method: 'post'
  })
}

export const getReportStatus = (reportId: number) => {
    // 这里可以直接复用获取 report 详情的接口
    // 复用 ReportList.vue 里的逻辑
    return request({
        url: `/testcases/reports/${reportId}`,
        method: 'get'
    })
}