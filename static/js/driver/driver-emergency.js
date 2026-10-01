// ==========================================================
// DRIVER EMERGENCY SYSTEM
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {

    // ======================================================
    // GET ALL EMERGENCY BUTTONS
    // ======================================================

    const emergencyButtons =
        document.querySelectorAll(".emergency-type-card");


    if (emergencyButtons.length === 0) {

        console.warn(
            "No emergency buttons found on driver dashboard."
        );

        return;
    }


    console.log(
        "Driver Emergency System Loaded:",
        emergencyButtons.length,
        "buttons found"
    );


    // ======================================================
    // CONNECT EACH EMERGENCY BUTTON
    // ======================================================

    emergencyButtons.forEach((button) => {

        button.addEventListener("click", async () => {

            const emergencyType =
                button.dataset.emergencyType;


            // ==================================================
            // VALIDATE EMERGENCY TYPE
            // ==================================================

            if (!emergencyType) {

                console.error(
                    "Emergency type missing from button."
                );

                alert(
                    "Unable to identify the emergency type."
                );

                return;
            }


            console.log(
                "Emergency selected:",
                emergencyType
            );


            // ==================================================
            // CONFIRM BEFORE SENDING
            // ==================================================

            const confirmed = confirm(
                `Send "${emergencyType}" emergency alert now?`
            );


            if (!confirmed) {

                return;
            }


            // ==================================================
            // PREVENT MULTIPLE CLICKS
            // ==================================================

            if (button.dataset.sending === "true") {

                return;
            }


            button.dataset.sending = "true";

            button.disabled = true;


            try {

                // ==================================================
                // GET DRIVER GPS LOCATION
                // ==================================================

                const location =
                    await getDriverLocation();


                console.log(
                    "Driver GPS Location:",
                    location
                );


                // ==================================================
                // CREATE DEFAULT EMERGENCY MESSAGE
                // ==================================================

                const emergencyMessage =
                    getEmergencyMessage(
                        emergencyType
                    );


                // ==================================================
                // SEND EMERGENCY TO FLASK
                // ==================================================

                const response =
                    await fetch(
                        "/driver/emergency",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({

                                emergency_type:
                                    emergencyType,

                                latitude:
                                    location.latitude,

                                longitude:
                                    location.longitude,

                                message:
                                    emergencyMessage

                            })

                        }
                    );


                // ==================================================
                // READ SERVER RESPONSE
                // ==================================================

                let result;


                try {

                    result =
                        await response.json();

                }

                catch (jsonError) {

                    throw new Error(
                        "Invalid response received from server."
                    );

                }


                console.log(
                    "Emergency Server Response:",
                    result
                );


                // ==================================================
                // CHECK RESPONSE
                // ==================================================

                if (
                    !response.ok ||
                    !result.success
                ) {

                    throw new Error(
                        result.message ||
                        "Unable to send emergency alert."
                    );

                }


                // ==================================================
                // SUCCESS
                // ==================================================

                console.log(
                    "Emergency alert created successfully."
                );


                alert(
                    `${emergencyType} alert sent successfully.\n\nYour emergency has been reported to the system.`
                );


            }

            catch (error) {

                console.error(
                    "Driver Emergency Error:",
                    error
                );


                alert(
                    error.message ||
                    "Unable to send emergency alert. Please try again."
                );

            }

            finally {

                // ==================================================
                // ENABLE BUTTON AGAIN
                // ==================================================

                button.disabled = false;

                button.dataset.sending = "false";

            }

        });

    });

});


// ==========================================================
// GET DRIVER CURRENT GPS LOCATION
// ==========================================================

function getDriverLocation() {

    return new Promise(
        (resolve, reject) => {


            // ======================================================
            // CHECK GEOLOCATION SUPPORT
            // ======================================================

            if (!navigator.geolocation) {

                reject(
                    new Error(
                        "GPS location is not supported on this device."
                    )
                );

                return;
            }


            console.log(
                "Requesting driver GPS location..."
            );


            // ======================================================
            // GET CURRENT LOCATION
            // ======================================================

            navigator.geolocation.getCurrentPosition(

                // ==================================================
                // LOCATION SUCCESS
                // ==================================================

                (position) => {

                    const latitude =
                        position.coords.latitude;

                    const longitude =
                        position.coords.longitude;


                    console.log(
                        "Latitude:",
                        latitude
                    );


                    console.log(
                        "Longitude:",
                        longitude
                    );


                    resolve({

                        latitude:
                            latitude,

                        longitude:
                            longitude

                    });

                },


                // ==================================================
                // LOCATION ERROR
                // ==================================================

                (error) => {

                    console.error(
                        "GPS Error:",
                        error
                    );


                    let errorMessage;


                    switch (error.code) {

                        case error.PERMISSION_DENIED:

                            errorMessage =
                                "Location permission was denied. Please allow location access and try again.";

                            break;


                        case error.POSITION_UNAVAILABLE:

                            errorMessage =
                                "Your current location is unavailable.";

                            break;


                        case error.TIMEOUT:

                            errorMessage =
                                "Location request timed out. Please try again.";

                            break;


                        default:

                            errorMessage =
                                "Unable to get your current location.";

                    }


                    reject(
                        new Error(
                            errorMessage
                        )
                    );

                },


                // ==================================================
                // GPS OPTIONS
                // ==================================================

                {

                    enableHighAccuracy: true,

                    timeout: 15000,

                    maximumAge: 0

                }

            );

        }
    );

}


// ==========================================================
// CREATE EMERGENCY MESSAGE
// ==========================================================

function getEmergencyMessage(
    emergencyType
) {

    switch (emergencyType) {


        // ==================================================
        // ACCIDENT
        // ==================================================

        case "Accident":

            return (
                "The driver has reported a bus accident. " +
                "Immediate attention is required."
            );


        // ==================================================
        // MEDICAL EMERGENCY
        // ==================================================

        case "Medical Emergency":

            return (
                "The driver has reported a medical emergency. " +
                "Immediate medical assistance may be required."
            );


        // ==================================================
        // BUS BREAKDOWN
        // ==================================================

        case "Bus Breakdown":

            return (
                "The driver has reported a bus breakdown or technical issue."
            );


        // ==================================================
        // SOS / OTHER
        // ==================================================

        case "SOS / Other Emergency":

            return (
                "The driver has sent an urgent SOS / emergency alert."
            );


        // ==================================================
        // DEFAULT
        // ==================================================

        default:

            return (
                "The driver has reported an emergency."
            );

    }

}