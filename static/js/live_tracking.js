// =====================================================
// STUDENT LIVE TRACKING
// =====================================================


// =====================================================
// STICKY HEADER
// =====================================================

document.addEventListener("DOMContentLoaded", function () {

    const stickyHeader =
        document.querySelector(".sticky-header");


    if (stickyHeader) {

        window.addEventListener("scroll", function () {

            if (window.scrollY > 120) {

                stickyHeader.classList.add("show");

            } else {

                stickyHeader.classList.remove("show");

            }

        });

    }


    // =================================================
    // LIVE MAP ELEMENT
    // =================================================

    const liveMap =
        document.getElementById("liveMap");


    if (!liveMap) {

        return;

    }


    // =================================================
    // BUS ID
    // =================================================

    const busId =
        liveMap.dataset.busid;


    if (!busId) {

        console.error(
            "Live tracking: Bus ID not found."
        );

        return;

    }


    // =================================================
    // UPDATE LIVE INFORMATION
    // =================================================

    async function updateLiveInformation() {

        try {

            const response =
                await fetch(
                    `/student/live_route/${busId}`,
                    {
                        method: "GET",
                        cache: "no-cache"
                    }
                );


            if (!response.ok) {

                throw new Error(
                    "Unable to fetch live route data."
                );

            }


            const data =
                await response.json();


            if (!data.success) {

                console.warn(
                    data.message ||
                    "Live route data unavailable."
                );

                return;

            }


            // =============================================
            // CURRENT STOP
            // =============================================

            const currentStop =
                document.getElementById(
                    "currentStop"
                );


            if (currentStop) {

                currentStop.textContent =
                    data.current_stop ||
                    "On Route";

            }


            // =============================================
            // NEXT STOP
            // =============================================

            const nextStop =
                document.getElementById(
                    "nextStop"
                );


            if (nextStop) {

                nextStop.textContent =
                    data.next_stop ||
                    "Route Completed";

            }


            // =============================================
            // DISTANCE TO NEXT STOP
            // =============================================

            const distanceToNext =
                document.getElementById(
                    "distanceToNext"
                );


            if (distanceToNext) {

                if (
                    data.distance_to_next !== null &&
                    data.distance_to_next !== undefined
                ) {

                    distanceToNext.textContent =
                        `${Number(
                            data.distance_to_next
                        ).toFixed(2)} km`;

                } else {

                    distanceToNext.textContent =
                        "--";

                }

            }


            // =============================================
            // DISTANCE REMAINING
            // =============================================

            const distanceRemaining =
                document.getElementById(
                    "distanceRemaining"
                );


            if (distanceRemaining) {

                if (
                    data.distance_remaining !== null &&
                    data.distance_remaining !== undefined
                ) {

                    distanceRemaining.textContent =
                        `${Number(
                            data.distance_remaining
                        ).toFixed(2)} km`;

                } else {

                    distanceRemaining.textContent =
                        "--";

                }

            }


            // =============================================
            // STOPS REMAINING
            // =============================================

            const stopsRemaining =
                document.getElementById(
                    "stopsRemaining"
                );


            if (stopsRemaining) {

                if (
                    data.stops_remaining !== null &&
                    data.stops_remaining !== undefined
                ) {

                    stopsRemaining.textContent =
                        data.stops_remaining;

                } else {

                    stopsRemaining.textContent =
                        "--";

                }

            }


            // =============================================
            // ETA
            // =============================================

            const busEta =
                document.getElementById(
                    "busEta"
                );


            if (busEta) {

                busEta.textContent =
                    data.eta ||
                    "--";

            }


            // =============================================
            // SPEED
            // =============================================

            const busSpeed =
                document.getElementById(
                    "busSpeed"
                );


            if (busSpeed) {

                const speed =
                    Number(data.speed || 0);


                busSpeed.textContent =
                    `${speed.toFixed(1)} km/h`;

            }


            // =============================================
            // DRIVER STATUS
            // =============================================

            const busStatus =
                document.getElementById(
                    "busStatus"
                );


            if (busStatus) {

                if (
                    data.trip_status === "Online" ||
                    data.trip_status === "On Trip"
                ) {

                    busStatus.innerHTML =
                        "🟢 Online";

                } else {

                    busStatus.innerHTML =
                        "🔴 Offline";

                }

            }


            // =============================================
            // LAST UPDATED
            // =============================================

            const lastUpdated =
                document.getElementById(
                    "lastUpdated"
                );


            if (lastUpdated) {

                lastUpdated.textContent =
                    data.last_updated ||
                    "--";

            }


            // =============================================
            // UPDATE ROUTE STOP LIST
            // =============================================

            updateRouteStops(data);


        }

        catch (error) {

            console.error(
                "Live tracking update error:",
                error
            );

        }

    }


    // =====================================================
    // UPDATE ROUTE STOPS
    // =====================================================

    function updateRouteStops(data) {

        const routeStops =
            document.getElementById(
                "routeStops"
            );


        if (
            !routeStops ||
            !Array.isArray(data.stops)
        ) {

            return;

        }


        const currentStop =
            data.current_stop
                ? String(
                    data.current_stop
                ).trim().toLowerCase()
                : "";


        const nextStop =
            data.next_stop
                ? String(
                    data.next_stop
                ).trim().toLowerCase()
                : "";


        routeStops.innerHTML = "";


        data.stops.forEach(
            function (stop, index) {

                const stopName =
                    String(
                        stop.stop_name || ""
                    ).trim();


                const stopNameLower =
                    stopName.toLowerCase();


                let stopClass =
                    "route-stop";


                // =========================================
                // CURRENT STOP
                // =========================================

                if (
                    currentStop &&
                    stopNameLower === currentStop
                ) {

                    stopClass +=
                        " current-stop";

                }


                // =========================================
                // NEXT STOP
                // =========================================

                if (
                    nextStop &&
                    stopNameLower === nextStop
                ) {

                    stopClass +=
                        " next-stop";

                }


                const stopElement =
                    document.createElement(
                        "div"
                    );


                stopElement.className =
                    stopClass;


                stopElement.dataset.stop =
                    stopName;


                stopElement.dataset.order =
                    stop.stop_order;


                stopElement.innerHTML = `

                    <div class="stop-number">
                        ${index + 1}
                    </div>

                    <div class="stop-line"></div>

                    <div class="stop-content">

                        <strong>
                            ${escapeHtml(stopName)}
                        </strong>

                        <span>
                            Stop ${stop.stop_order}
                        </span>

                    </div>

                `;


                routeStops.appendChild(
                    stopElement
                );

            }
        );

    }


    // =====================================================
    // SAFE HTML TEXT
    // =====================================================

    function escapeHtml(value) {

        const div =
            document.createElement("div");

        div.textContent =
            value;

        return div.innerHTML;

    }


    // =====================================================
    // FIRST UPDATE
    // =====================================================

    updateLiveInformation();


    // =====================================================
    // AUTOMATIC UPDATE
    // EVERY 10 SECONDS
    // =====================================================

    setInterval(
        updateLiveInformation,
        10000
    );

});