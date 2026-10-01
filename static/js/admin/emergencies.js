// ==========================================================
// ADMIN EMERGENCY RESPONSE
// ==========================================================

async function sendEmergencyResponse() {

    // -----------------------------------------
    // GET SELECTED EMERGENCY ID
    // -----------------------------------------

    const emergencyId =
        window.currentEmergencyId;


    // -----------------------------------------
    // GET RESPONSE TEXT
    // -----------------------------------------

    const responseTextarea =
        document.getElementById(
            "responseMessage"
        );


    if (!responseTextarea) {

        console.error(
            "Response textarea not found."
        );

        return;
    }


    const responseMessage =
        responseTextarea.value.trim();


    // -----------------------------------------
    // VALIDATION
    // -----------------------------------------

    if (!emergencyId) {

        alert(
            "Emergency ID not found."
        );

        return;
    }


    if (!responseMessage) {

        alert(
            "Please enter a response message."
        );

        responseTextarea.focus();

        return;
    }


    // -----------------------------------------
    // SEND RESPONSE TO FLASK
    // -----------------------------------------

    try {

        const response =
            await fetch(
                `/admin/emergencies/${emergencyId}/respond`,
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            response:
                                responseMessage

                        })

                }
            );


        const result =
            await response.json();


        console.log(
            "Emergency response result:",
            result
        );


        // -----------------------------------------
        // SUCCESS
        // -----------------------------------------

        if (result.success) {

            alert(
                "Emergency response sent successfully."
            );


            // Close modal

            closeEmergencyResponseModal();


            // Reload emergency list

            window.location.reload();

        }


        // -----------------------------------------
        // ERROR
        // -----------------------------------------

        else {

            alert(
                result.message ||
                "Unable to send emergency response."
            );

        }

    }

    catch (error) {

        console.error(
            "Emergency response error:",
            error
        );


        alert(
            "Unable to connect to the server."
        );

    }

}