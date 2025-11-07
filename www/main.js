$(document).ready(function () {

    eel.init()()

    $('.text').textillate({
        loop: true,
        sync: true,
        in: {
            effect: "bounceIn",
        },
        out: {
            effect: "bounceOut",
        },

    });

    // Siri configuration
    var siriWave = new SiriWave({
        container: document.getElementById("siri-container"),
        width: 800,
        height: 200,
        style: "ios9",
        amplitude: "1",
        speed: "0.30",
        autostart: true
    });

    // Siri message animation
    $('.siri-message').textillate({
        loop: true,
        sync: true,
        in: {
            effect: "fadeInUp",
            sync: true,
        },
        out: {
            effect: "fadeOutUp",
            sync: true,
        },

    });

    // mic button click event
    $("#MicBtn").click(function () {
        // show listening UI and disable button to prevent double clicks
    $("#MicBtn").addClass('disabled');
    $("#MicStatus").removeAttr('hidden');
    $("#CancelMicBtn").removeAttr('hidden');
        eel.playAssistantSound()
        $("#Oval").attr("hidden", true);
        $("#SiriWave").attr("hidden", false);
        // call python; when it returns, it will call eel.ShowHood() which hides the wave
        // but also expose hideMicStatus for cases where multiple background threads run
        eel.allCommands()().then(() => {
            // re-enable mic button and hide status when returned
            $("#MicBtn").removeClass('disabled');
            $("#MicStatus").attr('hidden', true);
        }).catch(()=>{
            $("#MicBtn").removeClass('disabled');
            $("#MicStatus").attr('hidden', true);
            $("#CancelMicBtn").attr('hidden', true);
        });
    });

    // Cancel button handler
    $("#CancelMicBtn").click(function(){
        try{
            eel.cancel_listen()();
        }catch(e){ }
        $("#CancelMicBtn").attr('hidden', true);
        $("#MicBtn").removeClass('disabled');
        $("#MicStatus").attr('hidden', true);
    });

    // Send button click event for typing commands
    $("#SendBtn").click(function () {
        var message = $("#chatbox").val().trim();
        if (message !== "") {
            $("#Oval").attr("hidden", true);
            $("#SiriWave").attr("hidden", false);
            eel.allCommands(message)()
            $("#chatbox").val(""); // Clear input field
        }
    });

    // Enter key press in input field
    $("#chatbox").keypress(function (e) {
        if (e.which === 13) { // Enter key
            var message = $("#chatbox").val().trim();
            if (message !== "") {
                $("#Oval").attr("hidden", true);
                $("#SiriWave").attr("hidden", false);
                eel.allCommands(message)()
                $("#chatbox").val(""); // Clear input field
            }
        }
    });


    function doc_keyUp(e) {
        // this would test for whichever key is 40 (down arrow) and the ctrl key at the same time

        if (e.key === 'j' && e.metaKey) {
            eel.playAssistantSound()
            $("#Oval").attr("hidden", true);
            $("#SiriWave").attr("hidden", false);
            eel.allCommands()()
        }
    }
    document.addEventListener('keyup', doc_keyUp, false);

    // to play assisatnt 
    function PlayAssistant(message) {

        if (message != "") {

            $("#Oval").attr("hidden", true);
            $("#SiriWave").attr("hidden", false);
            eel.allCommands(message);
            $("#chatbox").val("")
            $("#MicBtn").attr('hidden', false);
            $("#SendBtn").attr('hidden', true);

        }

    }

    // Skip prompt button removed — skip option disabled

    // Speech language selector
    function initSpeechLang() {
        try{
            let stored = localStorage.getItem('speech_lang');
            if(stored){
                $('#SpeechLangSelect').val(stored);
                eel.set_speech_language(stored)();
            } else {
                // keep default selected and save
                let v = $('#SpeechLangSelect').val();
                localStorage.setItem('speech_lang', v);
                eel.set_speech_language(v)();
            }

            $('#SpeechLangSelect').change(function(){
                let v = $(this).val();
                localStorage.setItem('speech_lang', v);
                try{ eel.set_speech_language(v)(); }catch(e){}
            });
        }catch(e){ }
    }

    initSpeechLang();

    // Show YouTube confirmation modal and return user's choice to Python via Eel
    window.showYouTubeConfirm = function(term) {
        return new Promise((resolve) => {
            try{
                $('#youtubeConfirmTerm').text(term || '');
                const modalEl = document.getElementById('youtubeConfirmModal');
                const modal = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });
                modalEl.addEventListener('hidden.bs.modal', function cb() {
                    // default: cancel
                    modalEl.removeEventListener('hidden.bs.modal', cb);
                    resolve(false);
                });

                $('#YouTubePlayBtn').off('click.youtubeConfirm').on('click.youtubeConfirm', function(){
                    modal.hide();
                    resolve(true);
                });

                $('#YouTubeCancelBtn').off('click.youtubeConfirm').on('click.youtubeConfirm', function(){
                    modal.hide();
                    resolve(false);
                });

                modal.show();
            }catch(e){
                resolve(true);
            }
        });
    }

    // Display the YouTube result found by Python and allow user to open it
    window.displayYouTubeResult = function(title, url) {
        try{
            $('#youtubeResultTitle').text(title || url || 'YouTube video');
            $('#youtubeResultLink').attr('href', url || '#').text(url || 'Open video');
            const modalEl = document.getElementById('youtubeResultModal');
            const modal = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: true });

            $('#YouTubeOpenBtn').off('click.youtubeResult').on('click.youtubeResult', function(){
                window.open(url, '_blank');
                modal.hide();
            });

            modal.show();
        }catch(e){
            console.log('displayYouTubeResult error', e);
        }
    }

    // toogle fucntion to hide and display mic and send button 
    function ShowHideButton(message) {
        if (message.length == 0) {
            $("#MicBtn").attr('hidden', false);
            $("#SendBtn").attr('hidden', true);
        }
        else {
            $("#MicBtn").attr('hidden', true);
            $("#SendBtn").attr('hidden', false);
        }
    }

    // key up event handler on text box
    $("#chatbox").keyup(function () {

        let message = $("#chatbox").val();
        ShowHideButton(message)

    });

    // send button event handler
    $("#SendBtn").click(function () {

        let message = $("#chatbox").val()
        PlayAssistant(message)

    });


    // enter press event handler on chat box
    $("#chatbox").keypress(function (e) {
        key = e.which;
        if (key == 13) {
            let message = $("#chatbox").val()
            PlayAssistant(message)
        }
    });


    // Settings Code

    eel.personalInfo()();
    eel.displaySysCommand()();
    eel.displayWebCommand()();
    eel.displayPhoneBookCommand()();



    // Execute: python side :
    eel.expose(getData)
    function getData(user_info) {
        let data = JSON.parse(user_info);
        let idsPersonalInfo = ['OwnerName', 'Designation', 'MobileNo', 'Email', 'City']
        let idsInputInfo = ['InputOwnerName', 'InputDesignation', 'InputMobileNo', 'InputEmail', 'InputCity']

        for (let i = 0; i < data.length; i++) {
            hashid = "#" + idsPersonalInfo[i]
            $(hashid).text(data[i]);
            $("#" + idsInputInfo[i]).val(data[i]);
        }

    }

    // Personal Data Update Button:

    $("#UpdateBtn").click(function () {

        let OwnerName = $("#InputOwnerName").val();
        let Designation = $("#InputDesignation").val();
        let MobileNo = $("#InputMobileNo").val();
        let Email = $("#InputEmail").val();
        let City = $("#InputCity").val();

        if (OwnerName.length > 0 && Designation.length > 0 && MobileNo.length > 0 && Email.length > 0 && City.length > 0) {
            eel.updatePersonalInfo(OwnerName, Designation, MobileNo, Email, City)

            swal({
                title: "Updated Successfully",
                icon: "success",
            });


        }
        else {
            const toastLiveExample = document.getElementById('liveToast')
            const toast = new bootstrap.Toast(toastLiveExample)

            $("#ToastMessage").text("All Fields Medatory");

            toast.show()
        }

    });


    // Display System Command Method
    eel.expose(displaySysCommand)
    function displaySysCommand(array) {

        let data = JSON.parse(array);
        console.log(data)

        let placeholder = document.querySelector("#TableData");
        let out = "";
        let index = 0
        for (let i = 0; i < data.length; i++) {
            index++
            out += `
                    <tr>
                        <td class="text-light"> ${index} </td>
                        <td class="text-light"> ${data[i][1]} </td>
                        <td class="text-light"> ${data[i][2]} </td>
                        <td class="text-light"> <button id="${data[i][0]}" onClick="SysDeleteID(this.id)" class="btn btn-sm btn-glow-red">Delete</button></td>
                        
                    </tr>
            `;

            // console.log(data[i][0])
            // console.log(data[i][1])


        }

        placeholder.innerHTML = out;

    }

    // Add System Command Button
    $("#SysCommandAddBtn").click(function () {

        let key = $("#SysCommandKey").val();
        let value = $("#SysCommandValue").val();

        if (key.length > 0 && value.length) {
            eel.addSysCommand(key, value)

            swal({
                title: "Updated Successfully",
                icon: "success",
            });
            eel.displaySysCommand()();
            $("#SysCommandKey").val("");
            $("#SysCommandValue").val("");


        }
        else {
            const toastLiveExample = document.getElementById('liveToast')
            const toast = new bootstrap.Toast(toastLiveExample)

            $("#ToastMessage").text("All Fields Medatory");

            toast.show()
        }

    });


    // Display Web Commands Table
    eel.expose(displayWebCommand)
    function displayWebCommand(array) {

        let data = JSON.parse(array);
        console.log(data)

        let placeholder = document.querySelector("#WebTableData");
        let out = "";
        let index = 0
        for (let i = 0; i < data.length; i++) {
            index++
            out += `
                    <tr>
                        <td class="text-light"> ${index} </td>
                        <td class="text-light"> ${data[i][1]} </td>
                        <td class="text-light"> ${data[i][2]} </td>
                        <td class="text-light"> <button id="${data[i][0]}" onClick="WebDeleteID(this.id)" class="btn btn-sm btn-glow-red">Delete</button></td>
                        
                    </tr>
            `;

            // console.log(data[i][0])
            // console.log(data[i][1])


        }

        placeholder.innerHTML = out;

    }


    // Add Web Commands

    $("#WebCommandAddBtn").click(function () {

        let key = $("#WebCommandKey").val();
        let value = $("#WebCommandValue").val();

        if (key.length > 0 && value.length) {
            eel.addWebCommand(key, value)

            swal({
                title: "Updated Successfully",
                icon: "success",
            });
            eel.displayWebCommand()();
            $("#WebCommandKey").val("");
            $("#WebCommandValue").val("");


        }
        else {
            const toastLiveExample = document.getElementById('liveToast')
            const toast = new bootstrap.Toast(toastLiveExample)

            $("#ToastMessage").text("All Fields Medatory");

            toast.show()
        }

    });


    // Display Phone Book

    eel.expose(displayPhoneBookCommand)
    function displayPhoneBookCommand(array) {

        let data = JSON.parse(array);
        console.log(data)

        let placeholder = document.querySelector("#ContactTableData");
        let out = "";
        let index = 0
        for (let i = 0; i < data.length; i++) {
            index++
            out += `
                    <tr>
                        <td class="text-light"> ${index} </td>
                        <td class="text-light"> ${data[i][1]} </td>
                        <td class="text-light"> ${data[i][2]} </td>
                        <td class="text-light"> ${data[i][3]} </td>
                        <td class="text-light"> ${data[i][4]} </td>
                        <td class="text-light"> <button id="${data[i][0]}" onClick="ContactDeleteID(this.id)" class="btn btn-sm btn-glow-red">Delete</button></td>
                        
                    </tr>
            `;


        }

        placeholder.innerHTML = out;

    }

    // Add Contacts to database

    $("#AddContactBtn").click(function () {

        let Name = $("#InputContactName").val();
        let MobileNo = $("#InputContactMobileNo").val();
        let Email = $("#InputContactEmail").val();
        let City = $("#InputContactCity").val();

        if (Name.length > 0 && MobileNo.length > 0) {

            if (Email.length < 0) {
                Email = "";
            }
            else if (City < 0) {
                City = "";
            }

            eel.InsertContacts(Name, MobileNo, Email, City)

            swal({
                title: "Updated Successfully",
                icon: "success",
            });

            $("#InputContactName").val("");
            $("#InputContactMobileNo").val("");
            $("#InputContactEmail").val("");
            $("#InputContactCity").val("");
            eel.displayPhoneBookCommand()()

        }
        else {
            const toastLiveExample = document.getElementById('liveToast')
            const toast = new bootstrap.Toast(toastLiveExample)

            $("#ToastMessage").text("Name and Mobile number Madatory");

            toast.show()
        }

    });




});

function SysDeleteID(clicked_id) {


    // console.log(clicked_id);
    eel.deleteSysCommand(clicked_id)
    eel.displaySysCommand()();

}

function WebDeleteID(clicked_id) {


    // console.log(clicked_id);
    eel.deleteWebCommand(clicked_id)
    eel.displayWebCommand()();


}
function ContactDeleteID(clicked_id) {

    // console.log(clicked_id);
    eel.deletePhoneBookCommand(clicked_id)
    eel.displayPhoneBookCommand()();

}