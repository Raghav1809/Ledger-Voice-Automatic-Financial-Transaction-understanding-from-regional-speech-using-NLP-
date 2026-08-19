app.factory('transactionService', ['apiService', function(apiService) {
  return {
    getAll: function(params) {
      return apiService.get('/transactions/', params);
    },
    getById: function(id) {
      return apiService.get('/transactions/' + id + '/');
    },
    create: function(txData) {
      return apiService.post('/transactions/', txData);
    },
    update: function(id, txData) {
      return apiService.put('/transactions/' + id + '/', txData);
    },
    delete: function(id) {
      return apiService.delete('/transactions/' + id + '/');
    }
  };
}]);
