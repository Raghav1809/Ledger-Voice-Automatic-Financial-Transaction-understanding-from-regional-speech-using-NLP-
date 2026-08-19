app.controller('InsightController', ['$scope', 'insightService', 'toastService', '$timeout', function($scope, insightService, toastService, $timeout) {
  $scope.isLoading = true;
  $scope.analytics = null;
  $scope.timeFilter = 'month';
  $scope.customStartDate = null;
  $scope.customEndDate = null;

  $scope.cleanPhone = function(phone) {
    if (!phone) return '';
    return phone.replace(/[^0-9]/g, '');
  };

  var chartInstances = {};

  $scope.setTimeFilter = function(filter) {
    $scope.timeFilter = filter;
    $scope.loadAnalytics();
  };

  $scope.applyCustomFilter = function() {
    if (!$scope.customStartDate || !$scope.customEndDate) {
      toastService.warning('Please select both Start Date and End Date for custom filter.');
      return;
    }
    $scope.timeFilter = 'custom';
    $scope.loadAnalytics();
  };

  $scope.loadAnalytics = function() {
    $scope.isLoading = true;
    var params = { time_filter: $scope.timeFilter };
    if ($scope.timeFilter === 'custom' && $scope.customStartDate && $scope.customEndDate) {
      var sDate = new Date($scope.customStartDate).toISOString().split('T')[0];
      var eDate = new Date($scope.customEndDate).toISOString().split('T')[0];
      params.start_date = sDate;
      params.end_date = eDate;
    }

    insightService.getAnalytics(params).then(function(res) {
      $scope.analytics = res.data;
      $timeout(function() {
        $scope.renderAllCharts(res.data);
      }, 100);
    }).catch(function() {
      toastService.danger('Failed to load analytics data.');
    }).finally(function() {
      $scope.isLoading = false;
    });
  };

  function createChart(canvasId, config) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    if (chartInstances[canvasId]) {
      chartInstances[canvasId].destroy();
      delete chartInstances[canvasId];
    }
    chartInstances[canvasId] = new Chart(canvas, config);
  }

  $scope.renderAllCharts = function(data) {
    if (!data) return;

    // 1. Sales Trend Line Chart
    createChart('salesTrendChart', {
      type: 'line',
      data: {
        labels: data.trends.labels,
        datasets: [{
          label: 'Sales Revenue (₹)',
          data: data.trends.sales,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });

    // 2. Sales vs Expenses Grouped Bar Chart
    createChart('salesVsExpenseChart', {
      type: 'bar',
      data: {
        labels: data.trends.labels,
        datasets: [
          {
            label: 'Sales (₹)',
            data: data.trends.sales,
            backgroundColor: '#0ea5e9',
            borderRadius: 5
          },
          {
            label: 'Expenses (₹)',
            data: data.trends.expenses,
            backgroundColor: '#f43f5e',
            borderRadius: 5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true } }
      }
    });

    // 3. Cash Flow Multi-Line Chart
    var netCashFlowSeries = data.trends.sales.map(function(s, idx) {
      var p = data.trends.payments[idx] || 0;
      var e = data.trends.expenses[idx] || 0;
      var c = data.trends.credits[idx] || 0;
      return (s + p) - (e + c);
    });

    createChart('cashFlowChart', {
      type: 'line',
      data: {
        labels: data.trends.labels,
        datasets: [
          {
            label: 'Money In (₹)',
            data: data.trends.sales.map(function(s, idx) { return s + (data.trends.payments[idx] || 0); }),
            borderColor: '#10b981',
            tension: 0.3,
            borderWidth: 2
          },
          {
            label: 'Money Out (₹)',
            data: data.trends.expenses.map(function(e, idx) { return e + (data.trends.credits[idx] || 0); }),
            borderColor: '#ef4444',
            tension: 0.3,
            borderWidth: 2
          },
          {
            label: 'Net Cash Flow (₹)',
            data: netCashFlowSeries,
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99, 102, 241, 0.08)',
            fill: true,
            tension: 0.3,
            borderWidth: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } }
      }
    });

    // 4. Credit Recovery Ring / Donut
    createChart('creditRecoveryChart', {
      type: 'doughnut',
      data: {
        labels: ['Recovered Payments (₹)', 'Outstanding Pending (₹)'],
        datasets: [{
          data: [data.summary.recovered_credit, data.summary.outstanding_credit],
          backgroundColor: ['#10b981', '#f59e0b'],
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' } },
        cutout: '70%'
      }
    });

    // 5. Weekly Activity Bar Chart
    createChart('weeklyActivityChart', {
      type: 'bar',
      data: {
        labels: data.weekly_activity.days,
        datasets: [
          {
            label: 'Sales Revenue (₹)',
            data: data.weekly_activity.sales,
            backgroundColor: '#10b981',
            borderRadius: 4
          },
          {
            label: 'Expenses (₹)',
            data: data.weekly_activity.expenses,
            backgroundColor: '#f43f5e',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } }
      }
    });

    // 6. Top Products Horizontal Bar Chart
    if (data.top_products_revenue && data.top_products_revenue.length > 0) {
      createChart('topProductsChart', {
        type: 'bar',
        data: {
          labels: data.top_products_revenue.map(function(p) { return p.name; }),
          datasets: [{
            label: 'Revenue (₹)',
            data: data.top_products_revenue.map(function(p) { return p.revenue; }),
            backgroundColor: '#8b5cf6',
            borderRadius: 4
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } }
        }
      });
    }

    // 7. Expense Categories Horizontal Bar Chart
    if (data.expense_categories && data.expense_categories.length > 0) {
      createChart('expenseCategoriesChart', {
        type: 'bar',
        data: {
          labels: data.expense_categories.map(function(c) { return c.category; }),
          datasets: [{
            label: 'Expense Amount (₹)',
            data: data.expense_categories.map(function(c) { return c.amount; }),
            backgroundColor: '#ec4899',
            borderRadius: 4
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } }
        }
      });
    }

    // 8. Transaction Mix Donut Chart
    if (data.transaction_mix && Object.keys(data.transaction_mix).length > 0) {
      var mixKeys = Object.keys(data.transaction_mix);
      var mixVals = mixKeys.map(function(k) { return data.transaction_mix[k]; });
      createChart('transactionMixChart', {
        type: 'doughnut',
        data: {
          labels: mixKeys,
          datasets: [{
            data: mixVals,
            backgroundColor: ['#0ea5e9', '#10b981', '#8b5cf6', '#f43f5e', '#f59e0b', '#64748b']
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'bottom' } }
        }
      });
    }
  };

  $scope.loadAnalytics();
}]);
