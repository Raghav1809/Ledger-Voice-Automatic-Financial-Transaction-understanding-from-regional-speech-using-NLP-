app.controller('CustomerController', ['$scope', 'customerService', 'toastService', function($scope, customerService, toastService) {
  $scope.customers = [];
  $scope.isLoading = false;
  $scope.searchQuery = '';
  $scope.selectedCustomer = null;
  $scope.customerTransactions = [];
  $scope.newCustomer = {};
  $scope.editMode = false;

  $scope.loadCustomers = function() {
    $scope.isLoading = true;
    var params = {};
    if ($scope.searchQuery) params.search = $scope.searchQuery;

    customerService.getAll(params).then(function(res) {
      $scope.customers = res.data.results || res.data;
    }).catch(function(err) {
      toastService.danger('Failed to load customers list.');
    }).finally(function() {
      $scope.isLoading = false;
    });
  };

  $scope.openCustomerDetails = function(customer) {
    $scope.selectedCustomer = customer;
    customerService.getTransactions(customer.id).then(function(res) {
      $scope.customerTransactions = res.data.transactions;
    });
  };

  $scope.openAddModal = function() {
    $scope.newCustomer = {};
    $scope.editMode = false;
  };

  $scope.openEditModal = function(customer) {
    $scope.newCustomer = angular.copy(customer);
    $scope.editMode = true;
  };

  $scope.saveCustomer = function() {
    if (!$scope.newCustomer.name) {
      toastService.warning('Customer name is required.');
      return;
    }

    if ($scope.editMode) {
      customerService.update($scope.newCustomer.id, $scope.newCustomer).then(function() {
        toastService.success('Customer updated successfully.');
        $scope.loadCustomers();
      }).catch(function(err) {
        toastService.danger('Failed to update customer.');
      });
    } else {
      customerService.create($scope.newCustomer).then(function() {
        toastService.success('Customer created successfully.');
        $scope.loadCustomers();
      }).catch(function(err) {
        toastService.danger('Failed to create customer.');
      });
    }
  };

  $scope.deleteCustomer = function(customer) {
    if (confirm('Are you sure you want to delete ' + customer.name + '?')) {
      customerService.delete(customer.id).then(function() {
        toastService.success('Customer deleted.');
        $scope.loadCustomers();
      });
    }
  };

  $scope.loadCustomers();
}]);
