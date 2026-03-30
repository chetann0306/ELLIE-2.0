$(document).ready(function () {
  
  function DisplayMessage(message) {
    // OVERRIDE: We intentionally leave this blank!
    // This blocks the Python backend from printing long paragraphs on the screen.
    // main.js will handle the "Listening..." and "Speaking..." states natively.
  }
  eel.expose(DisplayMessage);

  function ShowHood() {
    $("#Oval").attr("hidden", false);
  }
  eel.expose(ShowHood);
  
});