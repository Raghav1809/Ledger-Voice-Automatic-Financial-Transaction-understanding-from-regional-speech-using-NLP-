app.controller('InventoryController', ['$scope', 'inventoryService', 'toastService', function ($scope, inventoryService, toastService) {

  // ── State ─────────────────────────────────────────────────────────
  $scope.inventoryItems = [];
  $scope.isLoading = true;
  $scope.searchQuery = '';
  $scope.editMode = false;
  $scope.isSaving = false;

  // Form model for Add / Edit modal
  $scope.formItem = {
    product_name: '',
    unit: 'kg',
    quantity: 1.0,
    price: null
  };
  $scope.editingId = null;

  // Voice add state  ── all private to InventoryController ──────────
  $scope.isVoiceMode = false;
  $scope.isRecording = false;
  $scope.voiceTranscript = '';
  $scope.voiceInterim = '';
  $scope.voiceParsed = null;
  $scope.showVoiceConfirm = false;

  // Valid units for display
  $scope.unitOptions = [
    { value: 'kg', label: 'kg' },
    { value: 'g', label: 'g' },
    { value: 'litre', label: 'litre' },
    { value: 'ml', label: 'ml' },
    { value: 'piece', label: 'piece' },
    { value: 'pcs', label: 'pcs' },
    { value: 'bottle', label: 'bottle' },
    { value: 'dozen', label: 'dozen' },
    { value: 'packet', label: 'packet' },
    { value: 'box', label: 'box' },
    { value: 'bag', label: 'bag' },
    { value: 'bundle', label: 'bundle' },
    { value: 'mtr', label: 'mtr' },
    { value: 'ft', label: 'ft' }
  ];


  // ── Load Inventory ────────────────────────────────────────────────
  $scope.loadInventory = function () {
    $scope.isLoading = true;
    var params = {};
    if ($scope.searchQuery && $scope.searchQuery.trim()) {
      params.search = $scope.searchQuery.trim();
    }
    inventoryService.getAll(params).then(function (res) {
      $scope.inventoryItems = res.data.results || res.data;
    }).catch(function () {
      toastService.danger('Failed to load inventory items.');
    }).finally(function () {
      $scope.isLoading = false;
    });
  };

  $scope.loadInventory();

  // ── Search with debounce ──────────────────────────────────────────
  var searchTimer = null;
  $scope.onSearchChange = function () {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      $scope.$apply(function () {
        $scope.loadInventory();
      });
    }, 300);
  };

  // ── Add / Edit Modal ──────────────────────────────────────────────
  $scope.openAddModal = function () {
    $scope.editMode = false;
    $scope.editingId = null;
    $scope.formItem = { product_name: '', unit: 'kg', quantity: 1.0, price: null };
  };

  $scope.openEditModal = function (item) {
    $scope.editMode = true;
    $scope.editingId = item.id;
    $scope.formItem = {
      product_name: item.product_name,
      unit: item.unit,
      quantity: parseFloat(item.quantity) || 1.0,
      price: parseFloat(item.price)
    };
  };

  $scope.saveItem = function () {
    // Validation
    if (!$scope.formItem.product_name || !$scope.formItem.product_name.trim()) {
      toastService.warning('Product name cannot be empty.');
      return;
    }
    if ($scope.formItem.quantity === null || $scope.formItem.quantity === undefined || $scope.formItem.quantity <= 0) {
      toastService.warning('Quantity must be greater than zero.');
      return;
    }
    if ($scope.formItem.price === null || $scope.formItem.price === undefined || $scope.formItem.price < 0) {
      toastService.warning('Price cannot be negative or empty.');
      return;
    }

    $scope.isSaving = true;
    var data = {
      product_name: $scope.formItem.product_name.trim(),
      unit: $scope.formItem.unit,
      quantity: $scope.formItem.quantity,
      price: $scope.formItem.price
    };

    var promise;
    if ($scope.editMode && $scope.editingId) {
      promise = inventoryService.update($scope.editingId, data);
    } else {
      promise = inventoryService.create(data);
    }

    promise.then(function () {
      toastService.success($scope.editMode ? 'Inventory item updated!' : 'Inventory item added!');
      // Close modal
      var modal = bootstrap.Modal.getInstance(document.getElementById('inventoryFormModal'));
      if (modal) modal.hide();
      $scope.loadInventory();
    }).catch(function (err) {
      var errMsg = 'Failed to save inventory item.';
      if (err.data) {
        if (err.data.product_name) {
          errMsg = Array.isArray(err.data.product_name) ? err.data.product_name[0] : err.data.product_name;
        } else if (err.data.quantity) {
          errMsg = Array.isArray(err.data.quantity) ? err.data.quantity[0] : err.data.quantity;
        } else if (err.data.price) {
          errMsg = Array.isArray(err.data.price) ? err.data.price[0] : err.data.price;
        } else if (err.data.non_field_errors) {
          errMsg = err.data.non_field_errors[0];
        }
      }
      toastService.danger(errMsg);
    }).finally(function () {
      $scope.isSaving = false;
    });
  };

  // ── Delete ────────────────────────────────────────────────────────
  $scope.deleteItem = function (item) {
    if (!confirm('Delete "' + item.product_name + '" from inventory?')) return;
    inventoryService.delete(item.id).then(function () {
      toastService.success('"' + item.product_name + '" deleted from inventory.');
      $scope.loadInventory();
    }).catch(function () {
      toastService.danger('Failed to delete inventory item.');
    });
  };


  // ════════════════════════════════════════════════════════════════════
  // INVENTORY-PRIVATE VOICE ADD
  // Uses its own SpeechRecognition instance – completely independent
  // from voiceService and VoiceInputController. No $rootScope events.
  // ════════════════════════════════════════════════════════════════════

  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  var inventoryRecognition = null;

  // Safe $apply — avoids "$apply already in progress" error when called
  // from SpeechRecognition callbacks which can fire inside or outside a digest.
  function _safeApply(fn) {
    if ($scope.$$phase || $scope.$root.$$phase) {
      fn();
    } else {
      $scope.$apply(fn);
    }
  }

  // ── Private helpers for speech recognition lifecycle ──────────────
  function _startInventoryRecognition() {
    if (!SpeechRecognition) {
      toastService.warning('Speech recognition is not supported in this browser. Use Chrome or Edge.');
      return;
    }
    if (inventoryRecognition) {
      _stopInventoryRecognition();
    }

    $scope.voiceTranscript = '';
    $scope.voiceInterim = '';
    $scope.isRecording = true;
    console.log('[Inventory Voice] Creating and starting fresh recognition session...');

    try {
      inventoryRecognition = new SpeechRecognition();
      inventoryRecognition.continuous = true;
      inventoryRecognition.interimResults = true;
      inventoryRecognition.lang = 'en-US';

      inventoryRecognition.onresult = function (event) {
        console.log('[Inventory Voice] recognition.onresult fired');
        var interimText = '';
        var finalText = '';

        for (var i = event.resultIndex; i < event.results.length; i++) {
          var result = event.results[i];
          console.log('[Inventory Voice] result[' + i + '] isFinal=' + result.isFinal +
            ' text="' + result[0].transcript + '"');
          if (result.isFinal) {
            finalText += result[0].transcript;
          } else {
            interimText += result[0].transcript;
          }
        }

        _safeApply(function () {
          if (finalText) {
            $scope.voiceTranscript += finalText;
          }
          $scope.voiceInterim = interimText;
          console.log('[Inventory Voice] $scope.voiceTranscript =', $scope.voiceTranscript);
          console.log('[Inventory Voice] $scope.voiceInterim    =', $scope.voiceInterim);
        });
      };

      inventoryRecognition.onerror = function (event) {
        console.error('[Inventory Voice] recognition.onerror:', event.error);
        // Bug fix: do NOT wrap _stopInventoryRecognition in $apply — it calls .stop()
        // which fires onend which calls $apply again → "$apply already in progress" crash.
        var errCode = event.error;
        _safeApply(function () {
          $scope.isRecording = false;
        });
        // Null out listeners and release instance without triggering onend restart
        if (inventoryRecognition) {
          inventoryRecognition.onresult = null;
          inventoryRecognition.onerror = null;
          inventoryRecognition.onend = null;
          try { inventoryRecognition.abort(); } catch (e) { }
          inventoryRecognition = null;
        }
        if (errCode !== 'no-speech') {
          toastService.danger('Microphone error: ' + errCode);
        }
      };

      inventoryRecognition.onend = function () {
        console.log('[Inventory Voice] recognition.onend fired, isRecording=', $scope.isRecording);
        // Bug fix: do NOT call .start() on the same ended instance — Chrome throws
        // InvalidStateError. Instead, create a brand new instance for the restart.
        if ($scope.isRecording) {
          console.log('[Inventory Voice] auto-restarting with a fresh recognition instance...');
          // Detach old dead instance first
          var dead = inventoryRecognition;
          if (dead) {
            dead.onresult = null;
            dead.onerror = null;
            dead.onend = null;
          }
          inventoryRecognition = null;
          // Small timeout lets Chrome release the mic before re-acquiring
          setTimeout(function () {
            if ($scope.isRecording) {
              _startInventoryRecognition();
            }
          }, 150);
        }
      };

      inventoryRecognition.start();
    } catch (e) {
      console.error('[Inventory Voice] start error:', e);
      toastService.danger('Failed to start microphone.');
      $scope.isRecording = false;
      inventoryRecognition = null;
    }
  }

  function _stopInventoryRecognition() {
    console.log('[Inventory Voice] Stopping and releasing recognition session...');
    $scope.isRecording = false;
    if (inventoryRecognition) {
      try {
        inventoryRecognition.onresult = null;
        inventoryRecognition.onerror = null;
        inventoryRecognition.onend = null;
        inventoryRecognition.stop();
      } catch (e) {
        console.error('[Inventory Voice] stop error:', e);
      }
      inventoryRecognition = null;
    }
  }

  // ── Open / Close Voice Add panel ─────────────────────────────────
  $scope.openVoiceAdd = function () {
    $scope.isVoiceMode = true;
    $scope.voiceTranscript = '';
    $scope.voiceInterim = '';
    $scope.voiceParsed = null;
    $scope.showVoiceConfirm = false;
    $scope.isRecording = false;
    console.log('[Inventory Voice] openVoiceAdd → isVoiceMode = true');
  };

  $scope.closeVoiceAdd = function () {
    _stopInventoryRecognition();
    $scope.isVoiceMode = false;
    $scope.voiceTranscript = '';
    $scope.voiceInterim = '';
    $scope.voiceParsed = null;
    $scope.showVoiceConfirm = false;
    console.log('[Inventory Voice] closeVoiceAdd → isVoiceMode = false');
  };

  // ── Toggle mic (called from HTML button) ─────────────────────────
  $scope.toggleVoiceRecording = function () {
    console.log('[Inventory Voice] toggleVoiceRecording — isRecording=', $scope.isRecording);
    if ($scope.isRecording) {
      _stopInventoryRecognition();
    } else {
      _startInventoryRecognition();
      toastService.info('Listening... Say something like "Add 20 kg sugar for 1000 rupees"');
    }
  };

  // ── Stop recognition when controller scope is destroyed ──────────
  $scope.$on('$destroy', function () {
    _stopInventoryRecognition();
  });

  // ── Parse transcript → voiceParsed ───────────────────────────────
  $scope.parseVoiceInventory = function () {
    var text = ($scope.voiceTranscript || '').trim();

    console.log('=== [Inventory Voice] parseVoiceInventory called ===');
    console.log('[Inventory Voice] voiceTranscript value:', text);

    if (!text) {
      toastService.warning('No speech captured. Please record again.');
      return;
    }

    var parsed = parseInventoryVoice(text);
    console.log('[Inventory Voice] parseInventoryVoice result:', parsed);

    if (parsed) {
      $scope.voiceParsed = parsed;
      $scope.showVoiceConfirm = true;
      console.log('[Inventory Voice] Parsed OK → showing confirm panel');
    } else {
      toastService.warning('Could not extract product details. Try: "Sugar 45 rupees per kg" or "Add 20 kg sugar for 1000 rupees"');
    }
  };

  // ── Confirm & save ────────────────────────────────────────────────
  $scope.confirmVoiceAdd = function () {
    if (!$scope.voiceParsed) return;

    var data = {
      product_name: $scope.voiceParsed.product_name,
      unit: $scope.voiceParsed.unit,
      quantity: $scope.voiceParsed.quantity,
      price: $scope.voiceParsed.price
    };

    console.log('[Inventory Voice] confirmVoiceAdd → sending to API:', data);

    $scope.isSaving = true;
    inventoryService.create(data).then(function () {
      console.log('[Inventory Voice] API save SUCCESS for product:', data.product_name);
      toastService.success('Added "' + data.product_name + '" to inventory via voice!');
      $scope.closeVoiceAdd();
      $scope.loadInventory();
    }).catch(function (err) {
      var errMsg = 'Failed to add inventory item.';
      if (err.data) {
        if (err.data.product_name) {
          errMsg = Array.isArray(err.data.product_name) ? err.data.product_name[0] : err.data.product_name;
        } else if (err.data.quantity) {
          errMsg = Array.isArray(err.data.quantity) ? err.data.quantity[0] : err.data.quantity;
        }
      }
      console.error('[Inventory Voice] API save FAILED:', err);
      toastService.danger(errMsg);
    }).finally(function () {
      $scope.isSaving = false;
    });
  };


  // ════════════════════════════════════════════════════════════════════
  // INVENTORY VOICE PARSER
  // Extracts product_name, unit, quantity, price from natural speech.
  //
  // Supported patterns (after stripping leading "add"/"inventory"/"i have"):
  //
  //   1) QTY  UNIT  [of]  PRODUCT  [CONN]  PRICE  → "Add 5 kg rice for ₹250"
  //   2) PRODUCT  QTY  UNIT  [CONN]  PRICE        → "Add wheat 2 kg for ₹100"
  //   3) PRODUCT  [CONN]  PRICE  [per]  UNIT      → "Add wheat for ₹100 per kg"
  //   4) PRICE  [per]  UNIT  PRODUCT              → "₹45 per kg sugar"
  //   5) PRODUCT  [CONN]  PRICE                   → "sugar at 45 rupees" (no unit)
  //   6) PRICE  PRODUCT                           → "₹45 sugar" (price-first, no unit)
  // ════════════════════════════════════════════════════════════════════

  var UNIT_MAP = {
    // weight
    'kg': 'kg', 'kgs': 'kg', 'kilo': 'kg', 'kilos': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
    'g': 'g', 'gm': 'g', 'gms': 'g', 'gram': 'g', 'grams': 'g',
    // volume
    'l': 'litre', 'ltr': 'litre', 'liter': 'litre', 'liters': 'litre',
    'litre': 'litre', 'litres': 'litre',
    'ml': 'ml', 'milliliter': 'ml', 'millilitre': 'ml',
    'milliliters': 'ml', 'millilitres': 'ml',
    // count
    'piece': 'piece', 'pieces': 'piece', 'pcs': 'piece', 'pc': 'piece',
    'unit': 'piece', 'units': 'piece',
    'dozen': 'dozen', 'dozens': 'dozen', 'doz': 'dozen',
    // packaging
    'packet': 'packet', 'packets': 'packet', 'pack': 'packet', 'packs': 'packet',
    'box': 'box', 'boxes': 'box',
    'bottle': 'bottle', 'bottles': 'bottle',
    'bag': 'bag', 'bags': 'bag',
    'bundle': 'bundle', 'bundles': 'bundle',
    // length
    'meter': 'mtr', 'meters': 'mtr', 'mtr': 'mtr',
    'ft': 'ft', 'feet': 'ft', 'foot': 'ft',
    // weight (tons)
    'ton': 'kg', 'tons': 'kg'
  };

  var unitKeys = Object.keys(UNIT_MAP).sort(function (a, b) { return b.length - a.length; });
  var unitPattern = unitKeys.join('|');

  // Regex fragments
  var CUR_RE = '(?:rs\\.?|rupees?|rupee|inr|₹|\\$)';
  var PRICE_RE = CUR_RE + '?\\s*(\\d+(?:\\.\\d{1,2})?)\\s*' + CUR_RE + '?';
  var CONN_RE = '(?:at|is|for|of|price|costs?|costing|rate(?:\\s+of)?|to|@)?';

  function parseInventoryVoice(text) {
    if (!text) return null;

    var rawTranscript = text;

    // ── Normalize ───────────────────────────────────────────────────
    var norm = text.trim()
      .replace(/[,;:!]/g, ' ')
      // strip leading trigger words: "add inventory", "add", "inventory", "i have"
      .replace(/^(?:(?:add\s+)?inventory\s+|add\s+|i\s+have\s+)/i, '')
      .replace(/\s+/g, ' ')
      .trim()
      .replace(/[.,!?;:]+$/, '')
      .trim();

    console.log('[Inventory Voice Parser] raw     :', rawTranscript);
    console.log('[Inventory Voice Parser] norm    :', norm);

    var result = null;
    var m;

    // ── Pattern 1: QTY  UNIT  [of]  PRODUCT  [CONN]  PRICE ─────────
    // "Add 5 kg rice for ₹250", "Add 10 packets biscuits for ₹200",
    var pQtyUnitProductPrice = new RegExp(
      '^(\\d+(?:\\.\\d+)?)\\s*\\b(' + unitPattern + ')\\b\\s+(?:of\\s+)?([a-zA-Z][a-zA-Z\\s]{0,29}?)\\s+' + CONN_RE + '\\s*' + PRICE_RE + '$',
      'i'
    );
    m = pQtyUnitProductPrice.exec(norm);
    if (m) {
      result = { product_name: m[3], quantity: m[1], unit: m[2], price: m[4] };
      console.log('[Inventory Voice Parser] Pattern 1 matched:', result);
    }

    // ── Pattern 2: PRODUCT  QTY  UNIT  [CONN]  PRICE ───────────────
    // "Add wheat 2 kg for ₹100", "Add oil 2 litres for ₹300"
    if (!result) {
      var pProductQtyUnitPrice = new RegExp(
        '^([a-zA-Z][a-zA-Z\\s]{0,29}?)\\s+(\\d+(?:\\.\\d+)?)\\s*\\b(' + unitPattern + ')\\b\\s+' + CONN_RE + '\\s*' + PRICE_RE + '$',
        'i'
      );
      m = pProductQtyUnitPrice.exec(norm);
      if (m) {
        result = { product_name: m[1], quantity: m[2], unit: m[3], price: m[4] };
        console.log('[Inventory Voice Parser] Pattern 2 matched:', result);
      }
    }

    // ── Pattern 3: PRODUCT  [CONN]  PRICE  [per]  UNIT ─────────────
    // "Add wheat for ₹100 per kg", "Add rice price 60 rupees per kg"
    if (!result) {
      var pProductPricePerUnit = new RegExp(
        '^([a-zA-Z0-9][a-zA-Z0-9\\s]{0,30}?)\\s+' + CONN_RE + '\\s*' + PRICE_RE + '\\s+(?:per|a|an|each|\\/)?\\s*\\b(' + unitPattern + ')\\b$',
        'i'
      );
      m = pProductPricePerUnit.exec(norm);
      if (m) {
        result = { product_name: m[1], quantity: 1.0, unit: m[3], price: m[2] };
        console.log('[Inventory Voice Parser] Pattern 3 matched:', result);
      }
    }

    // ── Pattern 4: PRICE  [per]  UNIT  PRODUCT ─────────────────────
    // "₹45 per kg sugar", "40 rupees per litre milk"
    if (!result) {
      var pPricePerUnitProduct = new RegExp(
        '^' + PRICE_RE + '\\s+(?:per|a|an|each|\\/)?\\s*\\b(' + unitPattern + ')\\b\\s+(?:of\\s+)?([a-zA-Z0-9][a-zA-Z0-9\\s]{0,30}?)$',
        'i'
      );
      m = pPricePerUnitProduct.exec(norm);
      if (m) {
        result = { product_name: m[3], quantity: 1.0, unit: m[2], price: m[1] };
        console.log('[Inventory Voice Parser] Pattern 4 matched:', result);
      }
    }

    // ── Pattern 5: PRODUCT  [CONN]  PRICE  (no unit) ───────────────
    // "sugar at 45 rupees", "sugar 45 rs"
    if (!result) {
      var pD = new RegExp(
        '^([a-zA-Z0-9][a-zA-Z0-9\\s]{0,30}?)\\s+' + CONN_RE + '\\s*' + PRICE_RE + '$',
        'i'
      );
      m = pD.exec(norm);
      if (m) {
        result = { product_name: m[1], quantity: 1.0, unit: '', price: m[2] };
        console.log('[Inventory Voice Parser] Pattern 5 matched:', result);
      }
    }

    // ── Pattern 6: PRICE  PRODUCT  (price-first, no unit) ──────────
    if (!result) {
      var pE = new RegExp(
        '^' + PRICE_RE + '\\s+(?:of\\s+)?([a-zA-Z0-9][a-zA-Z0-9\\s]{0,30}?)$',
        'i'
      );
      m = pE.exec(norm);
      if (m) {
        result = { product_name: m[2], quantity: 1.0, unit: '', price: m[1] };
        console.log('[Inventory Voice Parser] Pattern 6 matched:', result);
      }
    }

    // ── Finalize ────────────────────────────────────────────────────
    if (result) {
      result.product_name = result.product_name.trim()
        .split(/\s+/)
        .map(function (w) { return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase(); })
        .join(' ');

      var rawUnit = (result.unit || '').toLowerCase().trim();
      result.unit = UNIT_MAP[rawUnit] || rawUnit;
      result.quantity = parseFloat(result.quantity || 1.0);
      result.price = parseFloat(result.price);
    }

    console.log('[Inventory Voice Parser] Final result:', result);
    return result;
  }

}]);
