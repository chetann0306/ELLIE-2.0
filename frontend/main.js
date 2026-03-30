$(document).ready(function () {
  // ================== TEXT ANIMATION ==================
  if ($.fn.textillate) {
    $('.text').textillate({
      loop: true,
      speed: 1500,
      sync: true,
      in: { effect: "bounceIn" },
      out: { effect: "bounceOut" }
    });

    $('.siri-message').textillate({
      loop: false,
      minDisplayTime: 1200,
      in: { effect: "fadeInUp", sync: true },
      out: { effect: "fadeOutUp", sync: true }
    });
  }

  // ================== HUD STATE MACHINE ==================
  function setSiriMessage(text) {
    $('.siri-message').stop(true, true).text(text);
    if ($('.siri-message').data('textillate')) {
      $('.siri-message').textillate('start');
    }
  }

  function setIdleState() {
    $("#StateListening").hide();
    $("#StateThinking").hide();
    $("#voiceIndicator").removeClass("active-speaking");
    $("#MicBtn, #ChatBtn").prop("disabled", false).removeClass("disabled");
    setSiriMessage("System Online. Ready.");
  }

  function setListeningState() {
    $("#StateThinking").hide();
    $("#voiceIndicator").removeClass("active-speaking");
    $("#MicBtn, #ChatBtn").prop("disabled", true).addClass("disabled");
    $("#StateListening").fadeIn(200);
    setSiriMessage("Listening...");
  }

  function setThinkingState() {
    $("#StateListening").hide();
    $("#voiceIndicator").removeClass("active-speaking");
    $("#StateThinking").fadeIn(200);
    setSiriMessage("Processing...");
  }

  function setSpeakingState() {
    $("#StateListening").hide();
    $("#StateThinking").hide();
    $("#voiceIndicator").addClass("active-speaking");
    setSiriMessage("Speaking...");
  }

  // ================== STRICT FEMALE VOICE CONTROLLER ==================
  // This ensures the browser never defaults to a male voice like "David"
  function speakTextWithFemaleVoice(text, onEndCallback) {
      if (!('speechSynthesis' in window)) {
          if (onEndCallback) setTimeout(onEndCallback, 1500);
          return;
      }
      
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1;
      
      // Load available voices
      const voices = window.speechSynthesis.getVoices();
      
      // Strict list of common female voice engines
      const femaleNames = ['zira', 'samantha', 'victoria', 'karen', 'hazel', 'tessa', 'melina', 'female', 'woman'];
      let chosenVoice = null;
      
      for (let name of femaleNames) {
          chosenVoice = voices.find(v => v.name.toLowerCase().includes(name));
          if (chosenVoice) break;
      }
      
      // Fallback: If no name matched, index 1 is almost always female on Windows
      if (!chosenVoice && voices.length > 1) {
          chosenVoice = voices[1];
      }
      
      if (chosenVoice) {
          u.voice = chosenVoice;
      }

      if (onEndCallback) {
          u.onend = onEndCallback;
          u.onerror = onEndCallback;
      }
      
      window.speechSynthesis.speak(u);
  }

  // Trigger voice loading immediately so it's ready
  if ('speechSynthesis' in window) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = function() {
          window.speechSynthesis.getVoices();
      };
  }

  if (typeof eel === "undefined") {
    console.warn("eel is not defined. Serve via Eel (eel.js).");
  }

  // ================== STARTUP MESSAGE ==================
  function startupGreeting() {
    const welcomeText = "Welcome boss, I am ELLIE. How can I help you?";
    setSiriMessage("System Online. Ready.");

    if (typeof eel !== "undefined" && eel.play_assistant_sound) {
      try { eel.play_assistant_sound()(); } catch (e) { console.warn("play_assistant_sound failed:", e); }
    }

    // Use our new strict female voice function
    speakTextWithFemaleVoice(welcomeText, function() {
        setSiriMessage("Tap the mic to speak");
    });
  }

  // ================== MIC BUTTON HANDLER ==================
  $("#MicBtn").on("click", function () {
    const $btn = $(this);
    if ($btn.prop("disabled")) return;

    setListeningState();

    if (typeof eel !== "undefined" && eel.play_assistant_sound) {
     try { eel.play_assistant_sound()(); } catch (e) { console.warn(e); }
    }

    if (typeof eel !== "undefined" && eel.takeAllCommands) {
      try {
        eel.takeAllCommands()(function (res) {
          if (!res) {
            setSiriMessage("System Error: No Response");
            setTimeout(function () { setIdleState(); }, 1400);
            return;
          }

          if (res.success) {
            const recognized = res.text || "";
            $("#chatbox").val(recognized);

            if (res.action === "opened") {
              setSpeakingState();
              speakTextWithFemaleVoice(`Opened ${res.target}`, function() {
                  setIdleState();
              });
              
            } else if (res.action === "failed") {
              setSpeakingState();
              const msg = res.reply || `Could not open ${res.target}`;
              speakTextWithFemaleVoice(msg, function() {
                  setIdleState();
              });
              
            } else {
              setSpeakingState();
              const reply = res.reply || recognized;
              speakTextWithFemaleVoice(reply, function() {
                  setIdleState();
              });
              
              // Fallback clear just in case TTS hangs
              const fallbackMs = Math.max(3000, reply.length * 70) + 1000;
              setTimeout(function () { setIdleState(); }, fallbackMs);
            }
          } else {
            setSiriMessage("I didn't catch that.");
            setTimeout(function () { setIdleState(); }, 1400);
          }
        });
      } catch (err) {
        console.error("Error invoking eel.takeAllCommands:", err);
        setSiriMessage("Voice error. Try again.");
        setTimeout(function () { setIdleState(); }, 1400);
      }
    } else {
      setSiriMessage("Voice backend offline");
      setTimeout(function () { setIdleState(); }, 1400);
    }
  });

  // ================== CHAT BUTTON & TEXT INPUT HANDLER ==================
  function handleTextMessage() {
    const txt = $("#chatbox").val().trim();
    if (txt.length > 0) {
      $("#chatbox").val("");
      
      setThinkingState();

      if (typeof eel !== "undefined" && eel.process_recognized_command) {
        eel.process_recognized_command(txt)(function (res) {
          
          if (res && res.success) {
            setSpeakingState();
            
            const replyText = res.reply || "";
            const fallbackMs = Math.max(3000, replyText.length * 70) + 1000;
            setTimeout(function () { setIdleState(); }, fallbackMs);

          } else {
            setSiriMessage("Connection Failed.");
            setTimeout(function () { setIdleState(); }, 2000);
          }
        });
      } else {
        setSiriMessage("Backend offline.");
        setTimeout(function () { setIdleState(); }, 2000);
      }
    }
  }

  $("#ChatBtn").on("click", handleTextMessage);
  $("#chatbox").on("keypress", function (e) {
    if (e.which === 13) handleTextMessage();
  });

  eel.expose(ShowSiriWave);
  function ShowSiriWave() {
    setListeningState();
  }

  // ================== AUTHENTICATION & STARTUP ==================
  function unlockAssistant() {
    $("#LoginScreen").fadeOut(300, function() {
        $("#MainApp").fadeIn(500);
        startupGreeting();
        
        if (typeof eel !== "undefined" && eel.wake_listener) {
            try { 
                eel.wake_listener(); 
            } catch (e) { console.warn("Failed to start wake listener:", e); }
        }
    });
  }

  function handleLogin() {
    const pwd = $("#passwordInput").val().trim();
    if (typeof eel !== "undefined" && eel.verify_password) {
        eel.verify_password(pwd)(function(isValid) {
            if (isValid) {
                $("#loginError").hide();
                unlockAssistant();
            } else {
                $("#loginError").fadeIn();
                $("#passwordInput").val("").focus();
                if (typeof $(".login-box").effect === "function") {
                    $(".login-box").effect("shake", { distance: 5, times: 3 }, 300); 
                }
            }
        });
    } else {
        alert("Backend not connected.");
    }
  }

  $("#loginBtn").on("click", handleLogin);
  $("#passwordInput").on("keypress", function(e) { if (e.which === 13) handleLogin(); });

  $("#faceUnlockBtn").on("click", function(e) {
      e.preventDefault();
      $("#LoginScreen").fadeOut(300, function() {
          $("#Start").fadeIn(300);
          $("#Loader").prop("hidden", false);
          $("#FaceAuth").prop("hidden", true);
          $("#FaceAuthSuccess").prop("hidden", true);
          $("#HelloGreet").prop("hidden", true);
          $("#WishMessage").text("Initializing Camera...");
          
          setTimeout(function() {
              $("#Loader").prop("hidden", true);
              $("#FaceAuth").prop("hidden", false);
              $("#WishMessage").text("Scanning Face... Look at the lens!");
              
              if (typeof eel !== "undefined" && eel.verify_face) {
                  eel.verify_face()(function(isValid) {
                      if (isValid === true) {
                          $("#FaceAuth").prop("hidden", true);
                          $("#FaceAuthSuccess").prop("hidden", false);
                          $("#WishMessage").text("Identity Verified.");
                          
                          setTimeout(function() {
                              $("#FaceAuthSuccess").prop("hidden", true);
                              $("#HelloGreet").prop("hidden", false);
                              $("#WishMessage").text("Welcome back, Boss.");
                              
                              setTimeout(function() {
                                  $("#Start").fadeOut(500, function() { unlockAssistant(); });
                              }, 2500);
                          }, 2000);
                      } else {
                          $("#Start").fadeOut(300, function() {
                              $("#LoginScreen").fadeIn(300);
                              $("#loginError").text("Face not recognized.").css("color", "#ff4444").fadeIn();
                              if (typeof $(".login-box").effect === "function") {
                                  $(".login-box").effect("shake", { distance: 5, times: 3 }, 300);
                              }
                          });
                      }
                  });
              } else {
                  console.error("⚠️ CRITICAL ERROR: eel.verify_face is missing!");
                  $("#Start").hide();
                  $("#LoginScreen").show();
                  $("#loginError").text("Camera module not connected.").css("color", "#ff4444").fadeIn();
              }
          }, 1500);
      });
  });
});