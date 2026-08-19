app.controller('VoiceInputController', ['$scope', 'voiceService', 'transactionService', 'toastService', '$location', '$window', function ($scope, voiceService, transactionService, toastService, $location, $window) {
  $scope.isSupported = voiceService.isSupported;
  $scope.isRecording = false;
  $scope.transcript = voiceService.getTranscript();
  $scope.interimTranscript = '';
  $scope.isParsing = false;
  $scope.isSaving = false;
  $scope.showConfirmation = false;

  // ── Sales mode state ──────────────────────────────────────────────
  $scope.isSalesMode = false;
  $scope.salesItems = [];   // [{name, qty, unit, price, total}]

  $scope.parsedData = {
    customer_name: '',
    customer_phone: '',
    amount: 0,
    transaction_type: 'credit',
    due_date: '',
    description: '',
    date: new Date(),
    status: 'pending'
  };

  // ── Voice event listeners ─────────────────────────────────────────
  $scope.$on('voice:statusChanged', function (evt, args) {
    $scope.isRecording = args.isRecording;
    if (args.error) toastService.danger('Voice recognition error: ' + args.error);
  });

  $scope.$on('voice:transcriptUpdated', function (evt, args) {
    $scope.transcript = args.transcript;
    $scope.interimTranscript = args.interimTranscript;
  });

  $scope.$on('voice:audioReady', function(evt, args) {
    if ($scope.transcript && $scope.transcript.trim()) {
      toastService.info('Extracting details using spaCy NLP...');
      $scope.processSpeech();
    } else {
      toastService.warning('No speech transcript captured. Please try speaking again or type manually.');
      $scope.isParsing = false;
    }
  });

  // ── Recording controls ────────────────────────────────────────────
  $scope.toggleRecording = function () {
    if (!$scope.isSupported) {
      toastService.warning('Browser microphone is not supported. Please use Chrome, Edge, or Safari.');
      return;
    }
    if ($scope.isRecording) {
      voiceService.stopRecording();
    } else {
      voiceService.startRecording();
      toastService.info('Listening... Speak in English. Click stop when finished.');
    }
  };

  $scope.clearText = function () {
    voiceService.clearTranscript();
    $scope.transcript = '';
    $scope.showConfirmation = false;
    $scope.isSalesMode = false;
    $scope.salesItems = [];
  };

  function handleParseResponse(res) {
    var data = res.data;
    
    // Update transcript from backend if provided (Gemini Audio parsing populates notes with transcript)
    if (data.notes && data.parser_used === 'gemini-audio') {
        $scope.transcript = data.notes;
    }

    // ── SALES MODE: items array present ──
    // ── SALES MODE: items array present ──
      if (data.is_sales && data.items && data.items.length > 0) {
        $scope.isSalesMode = true;
        // Ensure each item has a computed total
        $scope.salesItems = data.items.map(function (item) {
          var priceVal = parseFloat(item.price);
          var hasPrice = !isNaN(priceVal) && priceVal > 0;
          return {
            name:  item.name  || '',
            qty:   parseFloat(item.qty)   || 1,
            unit:  item.unit  || 'pcs',
            price: hasPrice ? priceVal : 0,
            total: hasPrice ? (parseFloat(item.total) || (parseFloat(item.qty || 1) * priceVal)) : 0,
            price_source: item.price_source || (hasPrice ? 'voice' : 'missing'),
            unit_mismatch: item.unit_mismatch || false,
            inventory_unit: item.inventory_unit || null,
            inventory_price: item.inventory_price || null
          };
        });
        $scope.parsedData = {
          customer_name: data.customer_name || '',
          customer_phone: data.customer_phone || '',
          amount: $scope.calculateSalesTotal(),
          transaction_type: 'sales',
          due_date: data.due_date ? new Date(data.due_date) : null,
          description: data.notes || '',
          date: data.date ? new Date(data.date) : new Date(),
          status: 'completed'
        };
        toastService.success('Sales items extracted via ' + (data.parser_used || 'AI') + '!');

      // ── STANDARD MODE ──
      } else {
        $scope.isSalesMode = false;
        $scope.salesItems = [];
        $scope.parsedData = {
          customer_name: data.customer_name || 'General',
          customer_phone: data.customer_phone || '',
          amount: data.amount || 0,
          transaction_type: data.transaction_type || 'credit',
          due_date: data.due_date ? new Date(data.due_date) : null,
          description: data.notes || '',
          date: data.date ? new Date(data.date) : new Date(),
          status: data.status || 'pending'
        };
        toastService.success('Voice extracted via ' + (data.parser_used || 'AI') + ' successfully!');
      }

      $scope.showConfirmation = true;
      $scope.isParsing = false;
    }

  $scope.processSpeech = function () {
    if (!$scope.transcript) {
      toastService.warning('Please type a speech transcript first.');
      return;
    }
    if ($scope.isRecording) voiceService.stopRecording();

    $scope.isParsing = true;
    voiceService.parseTranscript($scope.transcript).then(handleParseResponse).catch(function () {
      toastService.danger('Failed to parse speech transcript.');
      $scope.isParsing = false;
    });
  };

  // ── Sales Item Helpers ────────────────────────────────────────────
  $scope.calculateSalesTotal = function () {
    var total = 0;
    ($scope.salesItems || []).forEach(function (item) {
      total += (parseFloat(item.qty) || 0) * (parseFloat(item.price) || 0);
    });
    return Math.round(total * 100) / 100;
  };

  $scope.updateItemTotal = function (item) {
    var priceVal = parseFloat(item.price);
    if (!isNaN(priceVal) && priceVal > 0) {
      if (item.price_source === 'missing') {
        item.price_source = 'manual';
      }
    } else {
      item.price_source = 'missing';
    }
    item.total = Math.round((parseFloat(item.qty) || 0) * (priceVal || 0) * 100) / 100;
    $scope.parsedData.amount = $scope.calculateSalesTotal();
  };

  $scope.addSalesItem = function () {
    $scope.salesItems.push({ name: '', qty: 1, unit: 'kg', price: 0, total: 0, price_source: 'missing' });
  };

  $scope.removeSalesItem = function (index) {
    $scope.salesItems.splice(index, 1);
    $scope.parsedData.amount = $scope.calculateSalesTotal();
  };

  $scope.hasMissingPrices = function () {
    return ($scope.salesItems || []).some(function (item) {
      return !item.price || parseFloat(item.price) <= 0;
    });
  };

  // ── Save Transaction ──────────────────────────────────────────────
  function sendWhatsAppMessage(payload) {
    if (!payload.customer_phone) return;

    var cleanPhone = payload.customer_phone.replace(/[^0-9]/g, '');
    if (!cleanPhone) return;

    // Default to prefixing '91' for India if number is 10 digits
    if (cleanPhone.length === 10) {
      cleanPhone = '91' + cleanPhone;
    }

    var message = '';
    var dateStr = payload.date || new Date().toISOString().split('T')[0];
    var amount = payload.amount;
    var customerName = payload.customer_name || 'Customer';

    if (payload.transaction_type === 'credit') {
      message = 'Dear ' + customerName + ', your credit transaction of ₹' + amount + ' has been recorded on ' + dateStr + '.';
      if (payload.due_date) {
        message += ' Due date: ' + payload.due_date + '.';
      }
      message += ' Please clear it soon. Thank you!';
    } else if (payload.transaction_type === 'payment') {
      message = 'Dear ' + customerName + ', we have received your payment of ₹' + amount + ' on ' + dateStr + '. Thank you!';
    } else if (payload.transaction_type === 'sales') {
      message = 'Dear ' + customerName + ', thank you for your purchase! Total Bill Amount: ₹' + amount + ' on ' + dateStr + '.';
      if (payload.items_data && payload.items_data.length > 0) {
        var itemsList = payload.items_data.map(function(item) {
          return item.name + ' (' + item.qty + ' ' + item.unit + ' @ ₹' + item.price + ')';
        }).join(', ');
        message += ' Items: ' + itemsList;
      }
      message += ' Thank you for shopping with us!';
    } else {
      message = 'Dear ' + customerName + ', a transaction of ₹' + amount + ' (' + payload.transaction_type + ') has been recorded on ' + dateStr + '.';
    }

    var whatsappUrl = 'https://api.whatsapp.com/send?phone=' + cleanPhone + '&text=' + encodeURIComponent(message);
    $window.open(whatsappUrl, '_blank');
  }

  $scope.saveTransaction = function () {
    if ($scope.isSalesMode) {
      // Validate sales items
      if (!$scope.salesItems || $scope.salesItems.length === 0) {
        toastService.warning('Please add at least one item.');
        return;
      }
      var invalidItem = $scope.salesItems.some(function (item) {
        return !item.name || !item.name.trim() || parseFloat(item.price) <= 0;
      });
      if (invalidItem) {
        toastService.warning('Each item must have a name and a price greater than 0.');
        return;
      }

      var total = $scope.calculateSalesTotal();
      if (total <= 0) {
        toastService.warning('Total sales amount must be greater than 0.');
        return;
      }

      // Build items_data with correct totals
      var itemsData = $scope.salesItems.map(function (item) {
        var qty = parseFloat(item.qty) || 1;
        var price = parseFloat(item.price) || 0;
        return {
          name:  item.name.trim(),
          qty:   qty,
          unit:  item.unit || 'pcs',
          price: price,
          total: Math.round(qty * price * 100) / 100
        };
      });

      var payload = {
        customer_name: $scope.parsedData.customer_name || '',
        customer_phone: $scope.parsedData.customer_phone || '',
        amount: total,
        transaction_type: 'sales',
        due_date: $scope.parsedData.due_date ? $scope.parsedData.due_date.toISOString().split('T')[0] : null,
        description: $scope.parsedData.description,
        date: $scope.parsedData.date ? $scope.parsedData.date.toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
        status: 'completed',
        items_data: itemsData
      };

      $scope.isSaving = true;
      transactionService.create(payload).then(function () {
        toastService.success('Sales transaction saved! ' + itemsData.length + ' item(s), Total ₹' + total);
        sendWhatsAppMessage(payload);
        voiceService.clearTranscript();
        $scope.showConfirmation = false;
        $scope.isSalesMode = false;
        $scope.salesItems = [];
        $location.path('/transactions');
      }).catch(function (err) {
        var errMsg = 'Failed to save sales transaction.';
        if (err.data) {
          var firstKey = Object.keys(err.data)[0];
          if (firstKey) errMsg = firstKey + ': ' + (err.data[firstKey][0] || err.data[firstKey]);
        }
        toastService.danger(errMsg);
      }).finally(function () {
        $scope.isSaving = false;
      });

    } else {
      // ── Standard (credit/payment) save ──
      if (!$scope.parsedData.customer_name) {
        toastService.warning('Customer name is required.');
        return;
      }
      if (!$scope.parsedData.amount || $scope.parsedData.amount <= 0) {
        toastService.warning('Please enter a valid amount.');
        return;
      }

      $scope.isSaving = true;
      var payload = {
        customer_name: $scope.parsedData.customer_name,
        customer_phone: $scope.parsedData.customer_phone || '',
        amount: $scope.parsedData.amount,
        transaction_type: $scope.parsedData.transaction_type,
        due_date: $scope.parsedData.due_date ? $scope.parsedData.due_date.toISOString().split('T')[0] : null,
        description: $scope.parsedData.description,
        date: $scope.parsedData.date ? $scope.parsedData.date.toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
        status: $scope.parsedData.status || 'completed'
      };

      transactionService.create(payload).then(function () {
        toastService.success('Transaction saved for ' + $scope.parsedData.customer_name + '!');
        sendWhatsAppMessage(payload);
        voiceService.clearTranscript();
        $scope.showConfirmation = false;
        $location.path('/dashboard');
      }).catch(function (err) {
        var errMsg = 'Failed to save transaction.';
        if (err.data) {
          if (err.data.amount) errMsg = 'Amount error: ' + err.data.amount[0];
          else if (err.data.customer_name) errMsg = 'Customer error: ' + err.data.customer_name[0];
          else if (err.data.due_date) errMsg = 'Due date error: ' + err.data.due_date[0];
        }
        toastService.danger(errMsg);
      }).finally(function () {
        $scope.isSaving = false;
      });
    }
  };

  // Stop recording when leaving the page / unmounting
  $scope.$on('$destroy', function () {
    if ($scope.isRecording) {
      voiceService.stopRecording();
    }
  });
}]);