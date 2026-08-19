app.controller('TransactionController', ['$scope', 'transactionService', 'customerService', 'toastService', 'authService', 'settingsService', function($scope, transactionService, customerService, toastService, authService, settingsService) {
  $scope.userProfile = authService.getUser() || {};
  $scope.appSettings = {};
  settingsService.get().then(function(res) {
    $scope.appSettings = res.data;
  });
  $scope.transactions = [];
  $scope.customers = [];
  $scope.isLoading = false;
  $scope.filterType = '';
  $scope.searchQuery = '';
  $scope.currentTx = {};
  $scope.editMode = false;

  $scope.loadTransactions = function() {
    $scope.isLoading = true;
    var params = {};
    if ($scope.filterType) params.type = $scope.filterType;
    if ($scope.searchQuery) params.search = $scope.searchQuery;

    transactionService.getAll(params).then(function(res) {
      $scope.transactions = res.data.results || res.data;
    }).catch(function() {
      toastService.danger('Failed to load transactions.');
    }).finally(function() {
      $scope.isLoading = false;
    });
  };

  $scope.loadCustomers = function() {
    customerService.getAll().then(function(res) {
      $scope.customers = res.data.results || res.data;
    });
  };

  $scope.openAddModal = function() {
    $scope.currentTx = {
      transaction_type: 'credit',
      date: new Date(),
      amount: null,
      status: 'completed'
    };
    $scope.editMode = false;
    $scope.loadCustomers();
  };

  $scope.openEditModal = function(tx) {
    $scope.currentTx = angular.copy(tx);
    if ($scope.currentTx.date) $scope.currentTx.date = new Date($scope.currentTx.date);
    if ($scope.currentTx.due_date) $scope.currentTx.due_date = new Date($scope.currentTx.due_date);
    $scope.editMode = true;
    $scope.loadCustomers();
  };

  $scope.saveTransaction = function() {
    if (!$scope.currentTx.amount || $scope.currentTx.amount <= 0) {
      toastService.warning('Valid amount is required.');
      return;
    }

    var payload = angular.copy($scope.currentTx);
    if (payload.date instanceof Date) payload.date = payload.date.toISOString().split('T')[0];
    if (payload.due_date instanceof Date) payload.due_date = payload.due_date.toISOString().split('T')[0];

    if ($scope.editMode) {
      transactionService.update(payload.id, payload).then(function() {
        toastService.success('Transaction updated.');
        $scope.loadTransactions();
      }).catch(function() {
        toastService.danger('Failed to update transaction.');
      });
    } else {
      transactionService.create(payload).then(function() {
        toastService.success('Transaction added.');
        $scope.loadTransactions();
      }).catch(function() {
        toastService.danger('Failed to add transaction.');
      });
    }
  };

  $scope.deleteTransaction = function(tx) {
    if (confirm('Delete this transaction?')) {
      transactionService.delete(tx.id).then(function() {
        toastService.success('Transaction deleted.');
        $scope.loadTransactions();
      });
    }
  };

  $scope.sendWhatsApp = function(tx) {
    var name = tx.customer_detail ? tx.customer_detail.name : (tx.customer_name_raw || 'Customer');
    var amount = tx.amount || '0';
    var text = "";
    
    var date = tx.due_date || 'N/A';
    var storeName = ($scope.userProfile.profile && $scope.userProfile.profile.business_name) ? $scope.userProfile.profile.business_name : 'VoiceKhata Store';
    
    var upiLink = $scope.appSettings.upi_link || '';
    if (!upiLink && $scope.appSettings.upi_id) {
        upiLink = "upi://pay?pa=" + $scope.appSettings.upi_id + "&pn=" + encodeURIComponent(storeName);
    }
    var paymentSection = upiLink ? ("Pay here: " + upiLink + "\n\n") : "";

    if (tx.transaction_type === 'credit') {
        text = "*Ledger Voice Reminder*\n\n" + 
               name + "! 🙏 Your pending credit of ₹" + amount + " has been successfully recorded.\n" +
               "Note: Udhaar entry\n" +
               "Due Date: " + date + "\n\n" +
               paymentSection +
               "*" + storeName + "*\n" +
               "Supported by Ledger Voice";
    } else if (tx.transaction_type === 'payment') {
        text = "*Ledger Voice Receipt*\n\n" + 
               name + "! 🙏 Your payment of ₹" + amount + " has been successfully received.\n" +
               "Note: Payment entry\n\n" +
               "*" + storeName + "*\n" +
               "Supported by Ledger Voice";
    } else if (tx.transaction_type === 'sales') {
        text = "*Ledger Voice Invoice*\n\n" + 
               name + "! 🙏 Your purchase of ₹" + amount + " has been successfully recorded.\n" +
               "Note: Sales entry\n\n" +
               paymentSection +
               "*" + storeName + "*\n" +
               "Supported by Ledger Voice";
    } else {
        return; // No message for expense
    }
    
    var url = "https://wa.me/?text=" + encodeURIComponent(text);
    window.open(url, '_blank');
  };

  $scope.loadTransactions();
}]);
