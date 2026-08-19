app.factory('inventoryService', ['apiService', function(apiService) {
  return {
    getAll: function(params) {
      return apiService.get('/inventory/', params);
    },
    getById: function(id) {
      return apiService.get('/inventory/' + id + '/');
    },
    create: function(data) {
      return apiService.post('/inventory/', data);
    },
    update: function(id, data) {
      return apiService.put('/inventory/' + id + '/', data);
    },
    delete: function(id) {
      return apiService.delete('/inventory/' + id + '/');
    },
    lookup: function(productName) {
      return apiService.get('/inventory/lookup/', { product: productName });
    }
  };
}]);
