app.factory('insightService', ['apiService', function(apiService) {
  return {
    getSummary: function() {
      return apiService.get('/insights/summary/');
    },
    getAnalytics: function(params) {
      return apiService.get('/insights/analytics/', params);
    }
  };
}]);
