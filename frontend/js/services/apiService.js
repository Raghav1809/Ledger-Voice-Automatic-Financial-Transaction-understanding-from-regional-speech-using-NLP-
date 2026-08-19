app.factory('apiService', ['$http', 'API_BASE_URL', function($http, API_BASE_URL) {
  return {
    get: function(endpoint, params) {
      return $http.get(API_BASE_URL + endpoint, { params: params });
    },
    post: function(endpoint, data, config) {
      return $http.post(API_BASE_URL + endpoint, data, config);
    },
    put: function(endpoint, data, config) {
      return $http.put(API_BASE_URL + endpoint, data, config);
    },
    patch: function(endpoint, data, config) {
      return $http.patch(API_BASE_URL + endpoint, data, config);
    },
    delete: function(endpoint, config) {
      return $http.delete(API_BASE_URL + endpoint, config);
    }
  };
}]);
