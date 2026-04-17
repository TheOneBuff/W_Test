import request from '../utils/request'

export interface Skill {
  id: number
  name: string
  description?: string
  prompt_content: string
  skill_type: string
  is_active: boolean
  created_by?: number
  create_time: string
  update_time: string
}

export interface SkillCreate {
  name: string
  description?: string
  prompt_content: string
  skill_type: string
  is_active?: boolean
}

export interface SkillUpdate {
  name?: string
  description?: string
  prompt_content?: string
  skill_type?: string
  is_active?: boolean
}

export const getSkills = (params?: {
  skill_type?: string
  is_active?: boolean
  skip?: number
  limit?: number
}) => {
  return request.get<Skill[]>('/skills/', { params })
}

export const getAvailableSkills = (has_image?: boolean) => {
  return request.get('/skills/available', {
    params: { has_image }
  })
}

export const getSkill = (id: number) => {
  return request.get<Skill>(`/skills/${id}`)
}

export const createSkill = (data: SkillCreate) => {
  return request.post<Skill>('/skills/', data)
}

export const updateSkill = (id: number, data: SkillUpdate) => {
  return request.put<Skill>(`/skills/${id}`, data)
}

export const deleteSkill = (id: number) => {
  return request.delete(`/skills/${id}`)
}

export const toggleSkill = (id: number) => {
  return request.post(`/skills/${id}/toggle`)
}

export const seedDefaultSkills = () => {
  return request.post('/skills/seed-defaults')
}
