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

  // ================== HUD STATUS LOGIC ==================
  function setSiriMessage(text) {
    $('.siri-message').stop(true, true).text(text);
    if ($('.siri-message').data('textillate')) {
      $('.siri-message').textillate('start');
    }
  }

  function showSiriView($btn) {
    // Show the neon equalizer
    $("#AudioVisualizer").fadeIn(300);
    if ($btn) { $btn.prop("disabled", true).addClass("disabled"); }
    setSiriMessage("Listening...");
  }

  function restoreMainView($btn) {
    // Hide the neon equalizer completely
    $("#AudioVisualizer").fadeOut(300);
    if ($btn) { $btn.prop("disabled", false).removeClass("disabled"); }
    setSiriMessage("Tap the mic to speak again");
  }

  if (typeof eel === "undefined") {
    console.warn("eel is not defined. Serve via Eel (eel.js).");
  }

  // ================== STARTUP MESSAGE ==================
  function startupGreeting() {
    const welcomeText = "Welcome boss, I am ELLIE. How can I help you?";
    
    // HUD shows clean status instead of the paragraph
    setSiriMessage("System Online. Ready.");

    if (typeof eel !== "undefined" && eel.play_assistant_sound) {
      try { eel.play_assistant_sound()(); } catch (e) { console.warn("play_assistant_sound failed:", e); }
    }

    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(welcomeText);
        u.rate = 1;
        u.onend = function () { setSiriMessage("Tap the mic to speak"); };
        u.onerror = function () { setSiriMessage("Tap the mic to speak"); };
        window.speechSynthesis.getVoices();
        window.speechSynthesis.speak(u);
      } catch (err) {
        console.warn("Startup TTS failed:", err);
        setSiriMessage("Tap the mic to speak");
      }
    } else {
      setTimeout(() => setSiriMessage("Tap the mic to speak"), 1200);
    }
  }

  // ================== MIC BUTTON HANDLER ==================
  $("#MicBtn").on("click", function () {
    const $btn = $(this);
    if ($btn.prop("disabled")) return;

    showSiriView($btn);

    if (typeof eel !== "undefined" && eel.play_assistant_sound) {
     try { eel.play_assistant_sound()(); } catch (e) { console.warn(e); }
    }

    if (typeof eel !== "undefined" && eel.takeAllCommands) {
      try {
        eel.takeAllCommands()(function (res) {
          if (!res) {
            setSiriMessage("System Error: No Response");
            setTimeout(function () { restoreMainView($btn); }, 1400);
            return;
          }

          if (res.success) {
            const recognized = res.text || "";
            $("#chatbox").val(recognized);

            if (res.action === "opened") {
              setSiriMessage("Executing command...");
              if ('speechSynthesis' in window) {
                try {
                  const u = new SpeechSynthesisUtterance(`Opened ${res.target}`);
                  u.rate = 1;
                  window.speechSynthesis.cancel();
                  window.speechSynthesis.speak(u);
                } catch (ttsErr) { console.warn("TTS error:", ttsErr); }
              }
              setTimeout(function () { restoreMainView($btn); }, 1500);
              
            } else if (res.action === "failed") {
              setSiriMessage("Action failed.");
              if ('speechSynthesis' in window) {
                try {
                  const msg = res.reply || `Could not open ${res.target}`;
                  const u = new SpeechSynthesisUtterance(msg);
                  u.rate = 1;
                  window.speechSynthesis.cancel();
                  window.speechSynthesis.speak(u);
                } catch (ttsErr) { console.warn("TTS error:", ttsErr); }
              }
              setTimeout(function () { restoreMainView($btn); }, 2000);
              
            } else {
              // The AI is speaking its response. Keep HUD clean!
              setSiriMessage("Speaking...");
              const reply = res.reply || recognized;
              
              if ('speechSynthesis' in window) {
                try {
                  window.speechSynthesis.cancel();
                  const u = new SpeechSynthesisUtterance(reply);
                  u.rate = 1;
                  u.onend = function () { restoreMainView($btn); };
                  u.onerror = function () { restoreMainView($btn); };
                  window.speechSynthesis.speak(u);
                  
                  // Fades out the wave automatically based on how long the text takes to speak
                  const fallbackMs = Math.max(2000, reply.length * 70) + 2000;
                  setTimeout(function () { if ($btn.prop("disabled")) restoreMainView($btn); }, fallbackMs);
                } catch (ttsErr) {
                  console.warn("TTS error:", ttsErr);
                  restoreMainView($btn);
                }
              } else {
                setTimeout(function () { restoreMainView($btn); }, 2000);
              }
            }
          } else {
            setSiriMessage("I didn't catch that.");
            setTimeout(function () { restoreMainView($btn); }, 1400);
          }
        });
      } catch (err) {
        console.error("Error invoking eel.takeAllCommands:", err);
        setSiriMessage("Voice error. Try again.");
        setTimeout(function () { restoreMainView($btn); }, 1400);
      }
    } else {
      console.warn("eel.takeAllCommands is not available.");
      setSiriMessage("Voice backend offline");
      setTimeout(function () { restoreMainView($btn); }, 1400);
    }
  });

  // ================== CHAT BUTTON & TEXT INPUT HANDLER ==================
  function handleTextMessage() {
    const txt = $("#chatbox").val().trim();
    if (txt.length > 0) {
      $("#chatbox").val("");
      
      // Show wave and status
      showSiriView($("#ChatBtn")); 
      setSiriMessage("Processing...");

      if (typeof eel !== "undefined" && eel.process_recognized_command) {
        eel.process_recognized_command(txt)(function (res) {
          
          if (res && res.success) {
            setSiriMessage("Speaking...");
            
            // Fades out the wave automatically after the AI finishes speaking
            const replyText = res.reply || "";
            const fallbackMs = Math.max(3000, replyText.length * 70) + 1000;
            
            setTimeout(function () { 
              restoreMainView($("#ChatBtn")); 
            }, fallbackMs);

          } else {
            setSiriMessage("Connection Failed.");
            setTimeout(function () { 
              restoreMainView($("#ChatBtn")); 
            }, 2000);
          }
        });
      } else {
        setSiriMessage("Backend offline.");
        setTimeout(function () { restoreMainView($("#ChatBtn")); }, 2000);
      }
    }
  }

  $("#ChatBtn").on("click", handleTextMessage);
  $("#chatbox").on("keypress", function (e) {
    if (e.which === 13) handleTextMessage();
  });

  // ================== WAKE WORD EXPOSED FUNCTION ==================
  // Called by Python backend when wake word is detected
  eel.expose(ShowSiriWave);
  function ShowSiriWave() {
    $("#AudioVisualizer").fadeIn(300);
    setSiriMessage("Listening...");
  }

  // ================== AUTHENTICATION & STARTUP ==================
  function unlockAssistant() {
    $("#LoginScreen").fadeOut(300, function() {
        $("#MainApp").fadeIn(500);
        startupGreeting();
        
        if (typeof eel !== "undefined" && eel.wake_listener) {
            try { 
                eel.wake_listener(); 
                console.log("Wake listener started successfully."); 
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

  // ================== FACE UNLOCK HANDLER ==================
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