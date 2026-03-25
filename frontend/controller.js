
$(document).ready(function () {
  
  function DisplayMessage(message) {
    $('.siri-message').text(message || "");
    if ($('.siri-message').data('textillate')) {
      $('.siri-message').textillate('start');
    }
  }
  eel.expose(DisplayMessage);

  function ShowHood() {
    $("#Oval").attr("hidden", false);
    $("#SiriWave").attr("hidden", true);
    $("#MicBtn").prop("disabled", false).removeClass("disabled");
  }
  eel.expose(ShowHood);
});