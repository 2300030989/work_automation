$(document).ready(function () {



    // Display Speak Message
    eel.expose(DisplayMessage)
    function DisplayMessage(message) {
        // Replace the hidden textillate <li>
        $(".siri-message .texts li").text(message);

        // Re-initialize textillate so it splits into chars again
        $('.siri-message').textillate('start');
        // Auto-return to the home hood after displaying long messages (e.g., translations)
        try {
            // clear any previous auto-hide timer
            if (window._autoShowHoodTimeout) {
                clearTimeout(window._autoShowHoodTimeout);
                window._autoShowHoodTimeout = null;
            }
            // Only auto-hide for longer messages to avoid interrupting short prompts
            var len = (message || '').toString().trim().length;
            if (len > 80) {
                // If the mic is active, don't auto-hide; check MicStatus visibility
                var micVisible = ($('#MicStatus').is(':visible'));
                if (!micVisible) {
                    // give the user a few seconds to read the message, then return
                    window._autoShowHoodTimeout = setTimeout(function () {
                        try { ShowHood(); } catch (e) { }
                    }, 6000);
                }
            }
        } catch (e) { }
    }

    // Display hood
    eel.expose(ShowHood)
    function ShowHood() {
        $("#Oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
    }

    // Allow Python to hide mic status if needed
    eel.expose(hideMicStatus)
    function hideMicStatus() {
        try{
            $("#MicBtn").removeClass('disabled');
            $("#MicStatus").attr('hidden', true);
        }catch(e){ }
    }

    eel.expose(senderText)
    function senderText(message) {
        var chatBox = document.getElementById("chat-canvas-body");
        if (message.trim() !== "") {
            chatBox.innerHTML += `<div class="row justify-content-end mb-4">
            <div class = "width-size">
            <div class="sender_message">${message}</div>
        </div>`; 
    
            // Scroll to the bottom of the chat box
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }

    eel.expose(receiverText)
    function receiverText(message) {

        var chatBox = document.getElementById("chat-canvas-body");
        if (message.trim() !== "") {
            chatBox.innerHTML += `<div class="row justify-content-start mb-4">
            <div class = "width-size">
            <div class="receiver_message">${message}</div>
            </div>
        </div>`; 
    
            // Scroll to the bottom of the chat box
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        
    }

    
    // Hide Loader and display Face Auth animation
    eel.expose(hideLoader)
    function hideLoader() {

        $("#Loader").attr("hidden", true);
        $("#FaceAuth").attr("hidden", false);

    }
    // Hide Face auth and display Face Auth success animation
    eel.expose(hideFaceAuth)
    function hideFaceAuth() {

        $("#FaceAuth").attr("hidden", true);
        $("#FaceAuthSuccess").attr("hidden", false);

    }
    // Hide success and display 
    eel.expose(hideFaceAuthSuccess)
    function hideFaceAuthSuccess() {

        $("#FaceAuthSuccess").attr("hidden", true);
        $("#HelloGreet").attr("hidden", false);

    }


    // Hide Start Page and display blob
    eel.expose(hideStart)
    function hideStart() {

        $("#Start").attr("hidden", true);

        setTimeout(function () {
            $("#Oval").addClass("animate__animated animate__zoomIn");

        }, 1000)
        setTimeout(function () {
            $("#Oval").attr("hidden", false);
        }, 1000)
    }


});