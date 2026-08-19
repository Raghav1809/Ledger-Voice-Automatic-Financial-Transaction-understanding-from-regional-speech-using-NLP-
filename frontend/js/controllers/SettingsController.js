app.controller('SettingsController', ['$scope', 'settingsService', 'authService', 'toastService', function($scope, settingsService, authService, toastService) {
  $scope.userProfile = authService.getUser() || {};
  $scope.appSettings = {};
  $scope.passwordData = {};
  $scope.isLoading = false;
  $scope.activeTab = 'profile';

  $scope.loadSettings = function() {
    $scope.isLoading = true;
    settingsService.get().then(function(res) {
      $scope.appSettings = res.data;
    }).catch(function() {
      toastService.danger('Failed to load settings.');
    }).finally(function() {
      $scope.isLoading = false;
    });
  };

  $scope.saveSettings = function() {
    settingsService.update($scope.appSettings).then(function() {
      toastService.success('Preferences saved successfully.');
    }).catch(function() {
      toastService.danger('Failed to save settings.');
    });
  };

  $scope.updatePassword = function() {
    if (!$scope.passwordData.old_password || !$scope.passwordData.new_password) {
      toastService.warning('Please enter current and new password.');
      return;
    }
    if ($scope.passwordData.new_password !== $scope.passwordData.confirm_password) {
      toastService.warning('New passwords do not match.');
      return;
    }

    authService.changePassword($scope.passwordData).then(function() {
      toastService.success('Password changed successfully.');
      $scope.passwordData = {};
    }).catch(function(err) {
      var msg = err.data && err.data.old_password ? err.data.old_password[0] : 'Failed to change password.';
      toastService.danger(msg);
    });
  };

  $scope.loadSettings();
}]);
