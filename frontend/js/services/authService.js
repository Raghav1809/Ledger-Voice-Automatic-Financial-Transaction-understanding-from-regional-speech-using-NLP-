app.factory('authService', ['apiService', '$rootScope', '$q', function (apiService, $rootScope, $q) {
  var currentUser = null;

  try {
    var stored = localStorage.getItem('user_info');
    if (stored) currentUser = JSON.parse(stored);
  } catch (e) {
    currentUser = null;
  }

  function setCurrentUser(user) {
    currentUser = user;
    if (user) {
      localStorage.setItem('user_info', JSON.stringify(user));
    } else {
      localStorage.removeItem('user_info');
    }
    $rootScope.$broadcast('auth:userChanged', currentUser);
  }

  return {
    login: function (credentials) {
      return apiService.post('/auth/login/', credentials).then(function (res) {
        localStorage.setItem('access_token', res.data.access);
        localStorage.setItem('refresh_token', res.data.refresh);

        return apiService.get('/auth/user/').then(function (userRes) {
          setCurrentUser(userRes.data);
          return currentUser;
        });
      });
    },

    register: function (userData) {
      return apiService.post('/auth/register/', userData).then(function (res) {
        localStorage.setItem('access_token', res.data.access);
        localStorage.setItem('refresh_token', res.data.refresh);
        setCurrentUser(res.data.user);
        return res.data;
      });
    },

    logout: function () {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setCurrentUser(null);
    },

    isAuthenticated: function () {
      return !!localStorage.getItem('access_token');
    },

    getUser: function () {
      return currentUser;
    },

    changePassword: function (passData) {
      return apiService.post('/auth/change-password/', passData);
    }
  };
}]);