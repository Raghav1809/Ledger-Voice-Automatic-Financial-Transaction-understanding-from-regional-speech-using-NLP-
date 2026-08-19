app.factory('toastService', ['$timeout', function($timeout) {
  var toasts = [];

  function add(message, type, duration) {
    type = type || 'info';
    duration = duration || 4000;
    var toast = { message: message, type: type };
    toasts.push(toast);
    $timeout(function() {
      var idx = toasts.indexOf(toast);
      if (idx !== -1) {
        toasts.splice(idx, 1);
      }
    }, duration);
  }

  return {
    toasts: toasts,
    success: function(msg) { add(msg, 'success'); },
    danger: function(msg) { add(msg, 'danger'); },
    warning: function(msg) { add(msg, 'warning'); },
    info: function(msg) { add(msg, 'info'); },
    remove: function(index) {
      toasts.splice(index, 1);
    }
  };
}]);
