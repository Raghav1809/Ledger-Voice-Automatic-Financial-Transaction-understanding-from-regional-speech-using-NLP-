app.factory('settingsService', ['apiService', function(apiService) {
  return {
    get: function() {
      return apiService.get('/settings/');
    },
    update: function(settingsData) {
      return apiService.put('/settings/', settingsData);
    }
  };
}]);
