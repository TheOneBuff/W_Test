import request from '@/utils/request'

export const dispatchTask = (caseId: number) => {
  return request({
    url: `/api/android/dispatch/${caseId}`,
    method: 'post'
  })
}

export const getReportStatus = (reportId: number) => {
    // 这里可以直接复用获取 report 详情的接口，假设后端有 /api/reports/{id}
    // 或者你需要去 backend/app/api/android.py 再加一个查询接口
    // 这里假设复用 ReportList.vue 里的逻辑
    return request({
        url: `/api/reports/${reportId}`,
        method: 'get'
    })
}