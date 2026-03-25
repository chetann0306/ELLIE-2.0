

$(document).ready(function () {
  // TEXT ANIMATION 
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

  //  SIRI WAVE 
  var siriWave;
  var siriRunning = false;
  if (typeof SiriWave !== "undefined") {
    siriWave = new SiriWave({
      container: document.getElementById("siri-container"),
      width: 940,
      style: "ios9",
      amplitude: 1,
      speed: 0.30,
      height: 120,
      autostart: false,
      waveColor: "#1e90ff",
      waveOffset: 0,
      rippleEffect: true,
      rippleColor: "#ffffff",
    });
  }

  function startSiriWave() {
    if (siriWave && !siriRunning) {
      siriWave.start();
      siriRunning = true;
    }
  }

  function stopSiriWave() {
    if (siriWave && siriRunning) {
      siriWave.stop();
      siriRunning = false;
    }
  }

  function setSiriMessage(text) {
    $('.siri-message').stop(true, true).text(text);
    if ($('.siri-message').data('textillate')) {
      $('.siri-message').textillate('start');
    }
  }

  function showSiriView($btn) {
    $("#Oval").attr("hidden", true);
    $("#SiriWave").attr("hidden", false);
    if ($btn) { $btn.prop("disabled", true).addClass("disabled"); }
    setSiriMessage("Listening...");
    startSiriWave();
  }

  function restoreMainView($btn) {
    $("#Oval").attr("hidden", false);
    $("#SiriWave").attr("hidden", true);
    if ($btn) { $btn.prop("disabled", false).removeClass("disabled"); }
    setSiriMessage("Tap the mic to speak again");
    stopSiriWave();
  }

  if (typeof eel === "undefined") {
    console.warn("eel is not defined. Serve via Eel (eel.js).");
  }

  //  STARTUP MESSAGE 
  function startupGreeting() {
    const welcomeText = "Welcome boss, I am ELLIE. How can I help you?";
    setSiriMessage(welcomeText);

    if (typeof eel !== "undefined" && eel.play_assistant_sound) {
      try { eel.play_assistant_sound()(); } catch (e) { console.warn("play_assistant_sound failed:", e); }
    }

    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(welcomeText);
        u.rate = 1;
        u.onend = function () {
          setSiriMessage("Tap the mic to speak");
        };
        u.onerror = function () {
          setSiriMessage("Tap the mic to speak");
        };
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
  startupGreeting();

  //  MIC BUTTON HANDLER 
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
            setSiriMessage("No response from voice backend");
            setTimeout(function () { restoreMainView($btn); }, 1400);
            return;
          }

          if (res.success) {
            const recognized = res.text || "";
            $("#chatbox").val(recognized);

            if (res.action === "opened") {
              setSiriMessage(`Opened ${res.target}`);
              if ('speechSynthesis' in window) {
                try {
                  const u = new SpeechSynthesisUtterance(`Opened ${res.target}`);
                  u.rate = 1;
                  window.speechSynthesis.cancel();
                  window.speechSynthesis.speak(u);
                } catch (ttsErr) { console.warn("TTS error:", ttsErr); }
              }
              setTimeout(function () { restoreMainView($btn); }, 700);

            } else if (res.action === "failed") {
              const msg = res.reply || `Could not open ${res.target}`;
              setSiriMessage(msg);
              if ('speechSynthesis' in window) {
                try {
                  const u = new SpeechSynthesisUtterance(msg);
                  u.rate = 1;
                  window.speechSynthesis.cancel();
                  window.speechSynthesis.speak(u);
                } catch (ttsErr) { console.warn("TTS error:", ttsErr); }
              }
              setTimeout(function () { restoreMainView($btn); }, 1400);

            } else {
              const reply = res.reply || recognized;
              setSiriMessage(reply);
              if ('speechSynthesis' in window) {
                try {
                  window.speechSynthesis.cancel();
                  const u = new SpeechSynthesisUtterance(reply);
                  u.rate = 1;
                  u.onend = function () { restoreMainView($btn); };
                  u.onerror = function () { restoreMainView($btn); };
                  window.speechSynthesis.speak(u);
                  const fallbackMs = Math.max(2000, reply.length * 70) + 2000;
                  setTimeout(function () { if ($btn.prop("disabled")) restoreMainView($btn); }, fallbackMs);
                } catch (ttsErr) {
                  console.warn("TTS error:", ttsErr);
                  restoreMainView($btn);
                }
              } else {
                setTimeout(function () { restoreMainView($btn); }, 1400);
              }
            }
          } else {
            const errMsg = res.error || "I didn't catch that.";
            setSiriMessage(errMsg);
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
      setSiriMessage("Voice backend not available");
      setTimeout(function () { restoreMainView($btn); }, 1400);
    }
  });

  //  CHAT BUTTON HANDLER 
  $("#ChatBtn").on("click", function () {
    const txt = $("#chatbox").val().trim();
    if (txt.length) setSiriMessage(txt);
  });

  //  MICROPHONE DEBUG 
  if (typeof eel !== "undefined" && eel.list_microphones) {
    try {
      eel.list_microphones()(function (names) {
        console.log("Available microphones:", names);
      });
    } catch (e) {
      console.warn("Failed to request microphone list:", e);
    }
  }

  // ================== NEW: WAKE WORD LISTENER ==================
  if (typeof eel !== "undefined" && eel.wake_listener) {
    try {
      eel.wake_listener(); // starts Python background listener
      console.log("Wake listener started successfully.");
    } catch (e) {
      console.warn("Failed to start wake listener:", e);
    }
  }

  // Called by backend when wake word is detected
  eel.expose(ShowSiriWave);
  function ShowSiriWave() {
    $("#Oval").attr("hidden", true);
    $("#SiriWave").attr("hidden", false);
    $(".siri-message").text("Listening...");
    startSiriWave();
  }
});
