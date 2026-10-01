/*==========================================================
                DRIVER DASHBOARD
==========================================================*/

document.addEventListener("DOMContentLoaded", function () {

    /*======================================================
                    GREETING
    ======================================================*/

    const greeting = document.getElementById("greeting");

    if (greeting) {

        const hour = new Date().getHours();

        if (hour < 12) {

            greeting.innerHTML = "Good Morning 👋";

        }

        else if (hour < 17) {

            greeting.innerHTML = "Good Afternoon ☀️";

        }

        else {

            greeting.innerHTML = "Good Evening 🌙";

        }

    }

    /*======================================================
                    PROFILE MENU
    ======================================================*/

    const profileBtn = document.getElementById("profileBtn");

    const profileMenu = document.getElementById("profileMenu");

    if (profileBtn && profileMenu) {

        profileBtn.addEventListener("click", function (e) {

            e.stopPropagation();

            profileMenu.classList.toggle("active");

        });

        profileMenu.addEventListener("click", function (e) {

            e.stopPropagation();

        });

        document.addEventListener("click", function () {

            profileMenu.classList.remove("active");

        });

        document.addEventListener("keydown", function (e) {

            if (e.key === "Escape") {

                profileMenu.classList.remove("active");

            }

        });

    }

        /*======================================================
                    NOTIFICATION BUTTON
    ======================================================*/

    const notificationBtn = document.querySelector(".notification-btn");

    if (notificationBtn) {

        notificationBtn.addEventListener("click", function () {

            window.location.href = "/driver/notifications";

        });

    }

    /*======================================================
                    START TRIP
    ======================================================*/

    const startTripBtn = document.getElementById("startTripBtn");

    if (startTripBtn) {

        startTripBtn.addEventListener("click", async function () {

            startTripBtn.disabled = true;

            startTripBtn.innerHTML = `
                <i class="fa-solid fa-spinner fa-spin"></i>
                <span>Starting...</span>
            `;

            try {

                const response = await fetch("/driver/start_trip", {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    }

                });

                const result = await response.json();

                if (result.success) {

                    alert(result.message);

                    location.reload();

                }

                else {

                    alert(result.message);

                    startTripBtn.disabled = false;

                    startTripBtn.innerHTML = `
                        <i class="fa-solid fa-play"></i>
                        <span>Start Trip</span>
                    `;

                }

            }

            catch (error) {

                console.error(error);

                alert("Server Error");

                startTripBtn.disabled = false;

                startTripBtn.innerHTML = `
                    <i class="fa-solid fa-play"></i>
                    <span>Start Trip</span>
                `;

            }

        });

    }

        /*======================================================
                    END TRIP
    ======================================================*/

    const endTripBtn = document.getElementById("endTripBtn");

    if (endTripBtn) {

        endTripBtn.addEventListener("click", async function () {

            const confirmEnd = confirm(
                "Are you sure you want to end today's trip?"
            );

            if (!confirmEnd) {

                return;

            }

            endTripBtn.disabled = true;

            endTripBtn.innerHTML = `
                <i class="fa-solid fa-spinner fa-spin"></i>
                <span>Ending...</span>
            `;

            try {

                const response = await fetch("/driver/end_trip", {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    }

                });

                const result = await response.json();

                if (result.success) {

                    alert(result.message);

                    location.reload();

                }

                else {

                    alert(result.message);

                    endTripBtn.disabled = false;

                    endTripBtn.innerHTML = `
                        <i class="fa-solid fa-stop"></i>
                        <span>End Trip</span>
                    `;

                }

            }

            catch (error) {

                console.error(error);

                alert("Server Error");

                endTripBtn.disabled = false;

                endTripBtn.innerHTML = `
                    <i class="fa-solid fa-stop"></i>
                    <span>End Trip</span>
                `;

            }

        });

    }

    /*======================================================
                    EMERGENCY
    ======================================================*/

    const emergencyBtn = document.getElementById("emergencyBtn");

    if (emergencyBtn) {

        emergencyBtn.addEventListener("click", function () {

            const confirmEmergency = confirm(
                "Send Emergency Alert?"
            );

            if (!confirmEmergency) {

                return;

            }

            alert("Emergency Alert Sent Successfully.");

            // We'll connect this to the Flask backend later.

        });

    }

        /*======================================================
                LIVE GPS TRACKING
    ======================================================*/

    function updateDriverLocation(position) {

        const latitude = position.coords.latitude;

        const longitude = position.coords.longitude;

        fetch("/driver/update_location", {

            method: "POST",

            headers: {

                "Content-Type": "application/json"

            },

            body: JSON.stringify({

                latitude: latitude,

                longitude: longitude

            })

        })

        .then(response => response.json())

        .then(data => {

            if (data.success) {

                console.log("Driver Location Updated");

            }

            else {

                console.log("Location Update Failed");

            }

        })

        .catch(error => {

            console.error("Location Error :", error);

        });

    }

    /*======================================================
                LOCATION ERROR
    ======================================================*/

    function locationError(error) {

        switch(error.code){

            case error.PERMISSION_DENIED:

                console.log("Location Permission Denied");

                break;

            case error.POSITION_UNAVAILABLE:

                console.log("Location Unavailable");

                break;

            case error.TIMEOUT:

                console.log("Location Request Timed Out");

                break;

            default:

                console.log("Unknown Location Error");

        }

    }

    /*======================================================
                START GPS TRACKING
    ======================================================*/

    if ("geolocation" in navigator) {

        navigator.geolocation.watchPosition(

            updateDriverLocation,

            locationError,

            {

                enableHighAccuracy: true,

                timeout: 10000,

                maximumAge: 0

            }

        );

    }

    else {

        console.log("Geolocation Not Supported");

    }

        /*======================================================
                    MOBILE SIDEBAR
    ======================================================*/

    const menuBtn = document.getElementById("menuBtn");

    const mobileSidebar = document.getElementById("mobileSidebar");

    if (menuBtn && mobileSidebar) {

        /*----------------------------------
                OPEN / CLOSE
        ----------------------------------*/

        menuBtn.addEventListener("click", function (e) {

            e.stopPropagation();

            mobileSidebar.classList.toggle("show");

        });

        /*----------------------------------
                PREVENT CLOSE
        ----------------------------------*/

        mobileSidebar.addEventListener("click", function (e) {

            e.stopPropagation();

        });

        /*----------------------------------
                CLICK OUTSIDE
        ----------------------------------*/

        document.addEventListener("click", function () {

            mobileSidebar.classList.remove("show");

        });

        /*----------------------------------
                ESC KEY
        ----------------------------------*/

        document.addEventListener("keydown", function (e) {

            if (e.key === "Escape") {

                mobileSidebar.classList.remove("show");

            }

        });

    }

    /*======================================================
                    PAGE LOADED
    ======================================================*/

    console.log("Driver Dashboard Loaded Successfully");

});