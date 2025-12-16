// Site Management APIs - UPDATED with Controller support

export const siteAPI = {
  // Controller Management
  getControllers: (activeOnly = false) => 
    api.get('/controllers', { params: { active_only: activeOnly } }),
  getController: (id) => 
    api.get(`/controllers/${id}`),
  createController: (data) => 
    api.post('/controllers', data),
  updateController: (id, data) => 
    api.put(`/controllers/${id}`, data),
  deleteController: (id) => 
    api.delete(`/controllers/${id}`),
  
  // Site Management
  getSites: (activeOnly = false, controllerId = null) => 
    api.get('/sites', { params: { active_only: activeOnly, controller_id: controllerId } }),
  getSite: (id) => 
    api.get(`/sites/${id}`),
  createSite: (data) => 
    api.post('/sites', data),
  updateSite: (id, data) => 
    api.put(`/sites/${id}`, data),
  deleteSite: (id) => 
    api.delete(`/sites/${id}`),
  getSiteStats: (id) => 
    api.get(`/sites/${id}/stats`),
  getSiteActiveSessions: (id) => 
    api.get(`/sites/${id}/sessions/active`),
  disconnectUser: (id, data) => 
    api.post(`/sites/${id}/disconnect`, data),
};
