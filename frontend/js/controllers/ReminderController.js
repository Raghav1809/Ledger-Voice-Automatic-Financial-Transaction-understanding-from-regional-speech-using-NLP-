app.controller('ReminderController', ['$scope', 'reminderService', 'customerService', 'toastService', 'authService', 'settingsService', function($scope, reminderService, customerService, toastService, authService, settingsService) {
  $scope.userProfile = authService.getUser() || {};
  $scope.appSettings = {};
  settingsService.get().then(function(res) {
    $scope.appSettings = res.data;
  });
  $scope.reminders = [];
  $scope.customers = [];
  $scope.isLoading = false;
  $scope.currentCategory = 'today';
  $scope.newReminder = {};

  $scope.loadReminders = function(category) {
    $scope.currentCategory = category || $scope.currentCategory;
    $scope.isLoading = true;

    reminderService.getAll({ category: $scope.currentCategory }).then(function(res) {
      $scope.reminders = res.data.results || res.data;
    }).catch(function() {
      toastService.danger('Failed to load reminders.');
    }).finally(function() {
      $scope.isLoading = false;
    });
  };

  $scope.loadCustomers = function() {
    customerService.getAll().then(function(res) {
      $scope.customers = res.data.results || res.data;
    });
  };

  $scope.toggleStatus = function(reminder) {
    reminderService.toggleComplete(reminder.id).then(function(res) {
      reminder.status = res.data.status;
      reminder.computed_status = res.data.computed_status;
      toastService.success('Reminder status updated.');
      $scope.loadReminders();
    });
  };

  $scope.openAddModal = function() {
    $scope.newReminder = {
      due_date: new Date()
    };
    $scope.loadCustomers();
  };

  $scope.saveReminder = function() {
    if (!$scope.newReminder.customer || !$scope.newReminder.title || !$scope.newReminder.due_date) {
      toastService.warning('Customer, Title, and Due Date are required.');
      return;
    }

    var payload = angular.copy($scope.newReminder);
    if (payload.due_date instanceof Date) {
      payload.due_date = payload.due_date.toISOString().split('T')[0];
    }

    reminderService.create(payload).then(function() {
      toastService.success('Reminder added.');
      $scope.loadReminders();
    }).catch(function() {
      toastService.danger('Failed to create reminder.');
    });
  };

  $scope.deleteReminder = function(id) {
    if (confirm('Delete this reminder?')) {
      reminderService.delete(id).then(function() {
        toastService.success('Reminder removed.');
        $scope.loadReminders();
      });
    }
  };

  $scope.getDaysLeft = function(dueDateStr) {
    if (!dueDateStr) return '';
    var due = new Date(dueDateStr);
    var today = new Date();
    due.setHours(0,0,0,0);
    today.setHours(0,0,0,0);
    var diffTime = due - today;
    var diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Due today';
    if (diffDays > 0) return diffDays + ' day(s) left';
    return Math.abs(diffDays) + ' day(s) overdue';
  };

  $scope.sendWhatsApp = function(reminder) {
    var name = reminder.customer_detail ? reminder.customer_detail.name : 'Customer';
    var amount = reminder.amount || '0';
    var date = reminder.due_date || 'soon';
    var storeName = ($scope.userProfile.profile && $scope.userProfile.profile.business_name) ? $scope.userProfile.profile.business_name : 'VoiceKhata Store';
    
    var upiLink = $scope.appSettings.upi_link || '';
    if (!upiLink && $scope.appSettings.upi_id) {
        upiLink = "upi://pay?pa=" + $scope.appSettings.upi_id + "&pn=" + encodeURIComponent(storeName);
    }
    var paymentSection = upiLink ? ("Pay here: " + upiLink + "\n\n") : "";
    
    var text = "*Ledger Voice Reminder*\n\n" + 
               name + "! 🙏 Your pending credit of ₹" + amount + " has been successfully recorded.\n" +
               "Note: Udhaar entry\n" +
               "Due Date: " + date + "\n\n" +
               paymentSection +
               "*" + storeName + "*\n" +
               "Supported by Ledger Voice";
               
    var url = "https://wa.me/?text=" + encodeURIComponent(text);
    window.open(url, '_blank');
  };

  $scope.loadReminders('today');
}]);
