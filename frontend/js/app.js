var app = angular.module('voiceKhataApp', ['ngRoute']);

app.constant('API_BASE_URL', '/api');

app.config(['$routeProvider', '$httpProvider', function ($routeProvider, $httpProvider) {
  $httpProvider.interceptors.push('jwtInterceptor');

  $routeProvider
    .when('/', { templateUrl: 'views/landing.html', controller: 'LandingController' })
    .when('/login', { templateUrl: 'views/login.html', controller: 'AuthController' })
    .when('/register', { templateUrl: 'views/register.html', controller: 'AuthController' })
    .when('/dashboard', { templateUrl: 'views/dashboard.html', controller: 'DashboardController', requiresAuth: true })
    .when('/voice', { templateUrl: 'views/voice.html', controller: 'VoiceInputController', requiresAuth: true })
    .when('/customers', { templateUrl: 'views/customers.html', controller: 'CustomerController', requiresAuth: true })
    .when('/transactions', { templateUrl: 'views/transactions.html', controller: 'TransactionController', requiresAuth: true })
    .when('/insights', { 
      templateUrl: function() { return 'views/insights.html?v=' + Date.now(); }, 
      controller: 'InsightController', 
      requiresAuth: true 
    })
    .when('/reminders', { templateUrl: 'views/reminders.html', controller: 'ReminderController', requiresAuth: true })
    .when('/inventory', { 
      templateUrl: function() { return 'views/inventory.html?v=' + Date.now(); }, 
      controller: 'InventoryController', 
      requiresAuth: true 
    })
    .when('/settings', { templateUrl: 'views/settings.html', controller: 'SettingsController', requiresAuth: true })
    .otherwise({ redirectTo: '/' });
}]);

app.factory('jwtInterceptor', ['$q', '$location', function ($q, $location) {
  return {
    request: function (config) {
      var token = localStorage.getItem('access_token');
      if (token && (config.url.indexOf('/api/') !== -1 || config.url.indexOf('/api') !== -1)) {
        config.headers.Authorization = 'Bearer ' + token;
      }
      return config;
    },
    responseError: function (rejection) {
      if (rejection.status === 401) {
        if ($location.path() !== '/login' && $location.path() !== '/register') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user_info');
          $location.path('/login');
        }
      }
      return $q.reject(rejection);
    }
  };
}]);

app.controller('MainController', ['$scope', '$rootScope', '$location', 'authService', 'toastService', function ($scope, $rootScope, $location, authService, toastService) {
  $scope.currentUser = authService.getUser();
  $scope.toasts = toastService.toasts;

  $scope.isAuthenticated = function () { return authService.isAuthenticated(); };
  $scope.isActive = function (viewLocation) { return viewLocation === $location.path(); };

  $scope.logout = function () {
    authService.logout();
    toastService.info('You have logged out.');
    $location.path('/login');
  };

  $scope.removeToast = function (index) { toastService.remove(index); };

  $rootScope.$on('auth:userChanged', function (evt, user) {
    $scope.currentUser = user;
  });

  $rootScope.$on('$routeChangeStart', function (event, next, current) {
    $scope.currentUser = authService.getUser();
    if (next && next.requiresAuth && !authService.isAuthenticated()) {
      event.preventDefault();
      toastService.warning('Please login to access VoiceKhata.');
      $location.path('/login');
    }
  });
}]);