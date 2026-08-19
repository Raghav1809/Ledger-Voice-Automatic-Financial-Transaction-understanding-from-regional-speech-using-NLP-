app.controller('LandingController', ['$scope', 'authService', function($scope, authService) {
  $scope.isAuthenticated = authService.isAuthenticated();

  $scope.samplePhrases = [
    { text: "John borrowed 500 rupees.", type: "Credit", amount: "₹500", name: "John" },
    { text: "David paid me 300.", type: "Payment", amount: "₹300", name: "David" },
    { text: "Alex borrowed 2500 and will return after 5 days.", type: "Credit + Due Date", amount: "₹2,500", name: "Alex" },
    { text: "Sold goods worth 1200 to Sarah.", type: "Sales", amount: "₹1,200", name: "Sarah" }
  ];
}]);
