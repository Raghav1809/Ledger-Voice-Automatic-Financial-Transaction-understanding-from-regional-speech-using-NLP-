app.factory('voiceService', ['apiService', '$rootScope', function(apiService, $rootScope) {
  var mediaRecorder = null;
  var audioChunks = [];
  var isRecording = false;
  var transcript = ''; // This will be set by the backend response
  var isSupported = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  var currentStream = null;

  var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recognition = null;

  return {
    isSupported: isSupported,
    startRecording: function() {
      if (!isSupported || isRecording) return;
      
      transcript = '';
      $rootScope.$broadcast('voice:transcriptUpdated', { transcript: '', interimTranscript: '' });
      
      // Instantiate fresh SpeechRecognition for this session only
      if (SpeechRecognition) {
        try {
          recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'en-US';

          recognition.onresult = function(event) {
            var interimTranscript = '';
            var finalTranscript = '';
            for (var i = event.resultIndex; i < event.results.length; ++i) {
              if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
              } else {
                interimTranscript += event.results[i][0].transcript;
              }
            }
            transcript += finalTranscript;
            $rootScope.$apply(function() {
              $rootScope.$broadcast('voice:transcriptUpdated', { 
                transcript: transcript, 
                interimTranscript: interimTranscript 
              });
            });
          };

          recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
          };
        } catch (e) {
          console.error('Failed to create SpeechRecognition:', e);
        }
      }

      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(function(stream) {
          currentStream = stream;
          mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
          audioChunks = [];
          
          mediaRecorder.ondataavailable = function(event) {
            if (event.data.size > 0) {
              audioChunks.push(event.data);
            }
          };
          
          mediaRecorder.onstop = function() {
            var audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            // Cleanup stream tracks
            if (currentStream) {
              currentStream.getTracks().forEach(track => track.stop());
              currentStream = null;
            }
            // Clean up recognition session
            if (recognition) {
              try {
                recognition.onresult = null;
                recognition.onerror = null;
                recognition.onend = null;
                recognition.stop();
              } catch(e) {}
              recognition = null;
            }
            $rootScope.$apply(function() {
              $rootScope.$broadcast('voice:audioReady', { audioBlob: audioBlob });
            });
          };

          mediaRecorder.start();
          if (recognition) {
              try { recognition.start(); } catch(e) {}
          }
          isRecording = true;
          $rootScope.$apply(function() {
            $rootScope.$broadcast('voice:statusChanged', { isRecording: true });
          });
        })
        .catch(function(err) {
          console.error('Error accessing microphone:', err);
          if (recognition) {
            try {
              recognition.onresult = null;
              recognition.onerror = null;
              recognition.stop();
            } catch(e) {}
            recognition = null;
          }
          $rootScope.$apply(function() {
            $rootScope.$broadcast('voice:statusChanged', { isRecording: false, error: err.message });
          });
        });
    },

    stopRecording: function() {
      if (!isSupported || !isRecording || !mediaRecorder) return;
      isRecording = false;
      // Triggers mediaRecorder.onstop which releases recognition and mic tracks
      try {
        mediaRecorder.stop();
      } catch (e) {
        console.error('Failed to stop mediaRecorder:', e);
      }
      $rootScope.$broadcast('voice:statusChanged', { isRecording: false });
    },

    clearTranscript: function() {
      transcript = '';
      $rootScope.$broadcast('voice:transcriptUpdated', { transcript: '', interimTranscript: '' });
    },

    getTranscript: function() {
      return transcript;
    },

    setTranscript: function(text) {
      transcript = text;
      $rootScope.$broadcast('voice:transcriptUpdated', { transcript: transcript, interimTranscript: '' });
    },

    parseAudio: function(audioBlob) {
      var formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      return apiService.post('/voice/parse/', formData, {
        headers: { 'Content-Type': undefined } // Let browser set multipart/form-data boundary
      });
    },

    parseTranscript: function(textToParse) {
      var text = textToParse || transcript;
      return apiService.post('/voice/parse/', { transcript: text });
    }
  };
}]);
