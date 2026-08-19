app.factory('customerService', ['apiService', function(apiService) {
  return {
    getAll: function(params) {
      return apiService.get('/customers/', params);
    },
    getById: function(id) {
      return apiService.get('/customers/' + id + '/');
    },
    getTransactions: function(id) {
      return apiService.get('/customers/' + id + '/transactions/');
    },
    create: function(customerData) {
      return apiService.post('/customers/', customerData);
    },
    update: function(id, customerData) {
      return apiService.put('/customers/' + id + '/', customerData);
    },
    delete: function(id) {
      return apiService.delete('/customers/' + id + '/');
    }
  };
}]);
