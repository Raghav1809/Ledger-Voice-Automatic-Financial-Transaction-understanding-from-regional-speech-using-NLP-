app.factory('reminderService', ['apiService', function(apiService) {
  return {
    getAll: function(params) {
      return apiService.get('/reminders/', params);
    },
    create: function(reminderData) {
      return apiService.post('/reminders/', reminderData);
    },
    toggleComplete: function(id) {
      return apiService.post('/reminders/' + id + '/toggle_complete/');
    },
    delete: function(id) {
      return apiService.delete('/reminders/' + id + '/');
    }
  };
}]);
