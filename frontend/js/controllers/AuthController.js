app.controller('AuthController', ['$scope', '$location', 'authService', 'toastService', function ($scope, $location, authService, toastService) {
  $scope.loginData = {};
  $scope.registerData = {};
  $scope.isLoading = false;
  $scope.errorMessage = '';

  $scope.doLogin = function () {
    if (!$scope.loginData.username || !$scope.loginData.password) {
      toastService.warning('Please fill in all fields.');
      return;
    }
    $scope.isLoading = true;
    $scope.errorMessage = '';

    authService.login($scope.loginData).then(function (user) {
      toastService.success('Welcome back, ' + (user.username || '') + '!');
      $location.path('/dashboard');
    }).catch(function (err) {
      if (err.data && err.data.detail) {
        $scope.errorMessage = err.data.detail;
      } else {
        $scope.errorMessage = 'Invalid username or password.';
      }
      toastService.danger($scope.errorMessage);
    }).finally(function () {
      $scope.isLoading = false;
    });
  };

  $scope.doRegister = function () {
    if (!$scope.registerData.username || !$scope.registerData.password) {
      toastService.warning('Please enter a username and password.');
      return;
    }
    if ($scope.registerData.password !== $scope.registerData.confirm_password) {
      toastService.warning('Passwords do not match.');
      return;
    }
    $scope.isLoading = true;
    $scope.errorMessage = '';

    authService.register($scope.registerData).then(function (res) {
      toastService.success('Account created successfully!');
      $location.path('/dashboard');
    }).catch(function (err) {
      if (err.data) {
        if (typeof err.data === 'string') {
          $scope.errorMessage = err.data;
        } else if (err.data.username) {
          $scope.errorMessage = 'Username error: ' + (Array.isArray(err.data.username) ? err.data.username[0] : err.data.username);
        } else if (err.data.email) {
          $scope.errorMessage = 'Email error: ' + (Array.isArray(err.data.email) ? err.data.email[0] : err.data.email);
        } else if (err.data.password) {
          $scope.errorMessage = 'Password error: ' + (Array.isArray(err.data.password) ? err.data.password[0] : err.data.password);
        } else if (err.data.non_field_errors) {
          $scope.errorMessage = Array.isArray(err.data.non_field_errors) ? err.data.non_field_errors[0] : err.data.non_field_errors;
        } else if (err.data.detail) {
          $scope.errorMessage = err.data.detail;
        } else {
          var firstKey = Object.keys(err.data)[0];
          if (firstKey) {
            var val = err.data[firstKey];
            $scope.errorMessage = firstKey + ': ' + (Array.isArray(val) ? val[0] : val);
          } else {
            $scope.errorMessage = 'Registration failed. Please check your details.';
          }
        }
      } else {
        $scope.errorMessage = 'Registration failed. Network/Server error.';
      }
      toastService.danger($scope.errorMessage);
    }).finally(function () {
      $scope.isLoading = false;
    });
  };
}]);