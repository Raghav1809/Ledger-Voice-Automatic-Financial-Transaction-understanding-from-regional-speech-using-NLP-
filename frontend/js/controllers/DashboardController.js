app.controller('DashboardController', ['$scope', 'insightService', 'reminderService', 'toastService', function($scope, insightService, reminderService, toastService) {
  $scope.isLoading = true;
  $scope.summary = {};
  $scope.recentReminders = [];

  $scope.loadDashboardData = function() {
    $scope.isLoading = true;
    insightService.getSummary().then(function(res) {
      $scope.summary = res.data;
    }).catch(function(err) {
      toastService.danger('Failed to load dashboard metrics.');
    }).finally(function() {
      $scope.isLoading = false;
    });

    reminderService.getAll({ category: 'today' }).then(function(res) {
      $scope.recentReminders = res.data.results || res.data;
    });
  };

  $scope.loadDashboardData();
}]);
