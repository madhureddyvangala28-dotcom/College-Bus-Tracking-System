/* ==========================================
   GREETING
========================================== */

const greeting =
    document.getElementById("greeting");

if (greeting) {

    const hour =
        new Date().getHours();

    if (hour < 12) {

        greeting.innerHTML =
            "Good Morning 👋";

    }

    else if (hour < 17) {

        greeting.innerHTML =
            "Good Afternoon ☀️";

    }

    else {

        greeting.innerHTML =
            "Good Evening 🌙";

    }

}


/* ==========================================
   PROFILE MENU
========================================== */

const profileBtn =
    document.getElementById("profileBtn");

const profileMenu =
    document.getElementById("profileMenu");

if (profileBtn && profileMenu) {

    // --------------------------------------
    // Open / Close Profile Menu
    // --------------------------------------

    profileBtn.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

            profileMenu.classList.toggle(
                "active"
            );

        }
    );


    // --------------------------------------
    // Prevent closing inside menu
    // --------------------------------------

    profileMenu.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

        }
    );


    // --------------------------------------
    // Close outside
    // --------------------------------------

    document.addEventListener(
        "click",
        function () {

            profileMenu.classList.remove(
                "active"
            );

        }
    );


    // --------------------------------------
    // Close with Escape
    // --------------------------------------

    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Escape") {

                profileMenu.classList.remove(
                    "active"
                );

            }

        }
    );

}


/* ==========================================
   LIVE BUS STATUS
========================================== */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const liveData =
            document.getElementById(
                "dashboardLiveData"
            );

        const statusElement =
            document.getElementById(
                "dashboardStatus"
            );

        const statusDot =
            document.getElementById(
                "dashboardStatusDot"
            );


        // --------------------------------------
        // Check required elements
        // --------------------------------------

        if (
            !liveData ||
            !statusElement ||
            !statusDot
        ) {

            return;

        }


        // --------------------------------------
        // Get Bus ID
        // --------------------------------------

        const busId =
            liveData.dataset.busId;


        if (!busId) {

            return;

        }


        // ======================================
        // UPDATE STATUS
        // ======================================

        async function updateDashboardStatus() {

            try {

                const response =
                    await fetch(
                        `/student/live_location/${busId}`,
                        {
                            method: "GET",

                            cache: "no-store"
                        }
                    );


                if (!response.ok) {

                    throw new Error(
                        "Live location request failed."
                    );

                }


                const data =
                    await response.json();


                // ----------------------------------
                // No live data
                // ----------------------------------

                if (
                    !data ||
                    data.success === false
                ) {

                    setDashboardStatus(
                        "Offline"
                    );

                    return;

                }


                // ----------------------------------
                // Get real status
                // ----------------------------------

                let status =
                    data.trip_status;


                // ----------------------------------
                // Fallback if trip_status empty
                // ----------------------------------

                if (
                    !status ||
                    status.trim() === ""
                ) {

                    const speed =
                        parseFloat(
                            data.speed || 0
                        );


                    if (speed > 0) {

                        status =
                            "Moving";

                    }

                    else {

                        status =
                            "Stopped";

                    }

                }


                setDashboardStatus(
                    status
                );

            }

            catch (error) {

                console.error(
                    "Dashboard live status error:",
                    error
                );

            }

        }


        // ======================================
        // SET STATUS UI
        // ======================================

        function setDashboardStatus(
            status
        ) {

            status =
                String(status || "Offline")
                    .trim();


            statusElement.textContent =
                status;


            // Remove previous classes

            statusDot.className =
                "status-dot";


            // ----------------------------------
            // Online
            // ----------------------------------

            if (
                status.toLowerCase() ===
                "online"
            ) {

                statusDot.classList.add(
                    "online"
                );

            }


            // ----------------------------------
            // Moving
            // ----------------------------------

            else if (
                status.toLowerCase() ===
                "moving"
            ) {

                statusDot.classList.add(
                    "moving"
                );

            }


            // ----------------------------------
            // On Trip
            // ----------------------------------

            else if (
                status.toLowerCase() ===
                "on trip"
            ) {

                statusDot.classList.add(
                    "moving"
                );

            }


            // ----------------------------------
            // Stopped
            // ----------------------------------

            else if (
                status.toLowerCase() ===
                "stopped"
            ) {

                statusDot.classList.add(
                    "stopped"
                );

            }


            // ----------------------------------
            // Delayed
            // ----------------------------------

            else if (
                status.toLowerCase() ===
                "delayed"
            ) {

                statusDot.classList.add(
                    "delayed"
                );

            }


            // ----------------------------------
            // Offline
            // ----------------------------------

            else {

                statusDot.classList.add(
                    "offline"
                );

            }

        }


        // ======================================
        // FIRST UPDATE
        // ======================================

        updateDashboardStatus();


        // ======================================
        // AUTO UPDATE EVERY 10 SECONDS
        // ======================================

        setInterval(
            updateDashboardStatus,
            10000
        );

    }
);