/* =========================================================
   DRIVER ROUTE DETAILS
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       MOBILE SIDEBAR
    ===================================================== */

    const menuBtn =
        document.getElementById("mobileMenuBtn");

    const sidebar =
        document.querySelector(".sidebar");

    const overlay =
        document.getElementById("sidebarOverlay");


    if (menuBtn) {

        menuBtn.addEventListener("click", function () {

            sidebar.classList.toggle("open");

            overlay.classList.toggle("active");

        });

    }


    if (overlay) {

        overlay.addEventListener("click", function () {

            sidebar.classList.remove("open");

            overlay.classList.remove("active");

        });

    }


    /* =====================================================
       CHECK LEAFLET
    ===================================================== */

    if (typeof L === "undefined") {

        console.error("Leaflet is not loaded.");

        return;

    }


    /* =====================================================
       CHECK ROUTE STOPS
    ===================================================== */

    if (
        typeof routeStops === "undefined" ||
        !Array.isArray(routeStops)
    ) {

        console.error("Route stop data not available.");

        return;

    }


    /* =====================================================
       CREATE MAP
    ===================================================== */

    const mapElement =
        document.getElementById("routeMap");


    if (!mapElement) {

        return;

    }


    const map =
        L.map("routeMap");


    /* =====================================================
       OPENSTREETMAP
    ===================================================== */

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,

            attribution:
                "&copy; OpenStreetMap contributors"
        }
    ).addTo(map);


    /* =====================================================
       VALID COORDINATES
    ===================================================== */

    const validStops = routeStops.filter(function (stop) {

        const lat =
            parseFloat(
                stop.latitude
            );

        const lng =
            parseFloat(
                stop.longitude
            );

        return (
            Number.isFinite(lat) &&
            Number.isFinite(lng)
        );

    });


    /* =====================================================
       NO COORDINATES
    ===================================================== */

    if (validStops.length === 0) {

        map.setView(
            [21.7051, 72.9959],
            10
        );

        return;

    }


    /* =====================================================
       MAP MARKERS
    ===================================================== */

    const routeCoordinates = [];


    validStops.forEach(function (stop, index) {

        const lat =
            parseFloat(
                stop.latitude
            );

        const lng =
            parseFloat(
                stop.longitude
            );


        routeCoordinates.push([
            lat,
            lng
        ]);


        /* ================================================
           CUSTOM STOP ICON
        ================================================= */

        const stopIcon =
            L.divIcon({

                className:
                    "driver-stop-marker",

                html:
                    `
                    <div style="
                        width:32px;
                        height:32px;
                        border-radius:50%;
                        background:#ffc107;
                        border:4px solid #182236;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        color:#182236;
                        font-weight:800;
                        font-size:13px;
                        box-shadow:0 3px 10px rgba(0,0,0,0.25);
                    ">
                        ${index + 1}
                    </div>
                    `,

                iconSize: [
                    32,
                    32
                ],

                iconAnchor: [
                    16,
                    16
                ]

            });


        /* ================================================
           MARKER
        ================================================= */

        const marker =
            L.marker(
                [lat, lng],
                {
                    icon: stopIcon
                }
            ).addTo(map);


        /* ================================================
           POPUP
        ================================================= */

        marker.bindPopup(
            `
            <div style="
                min-width:160px;
                font-family:Arial,sans-serif;
            ">

                <strong style="
                    font-size:16px;
                    color:#182236;
                ">
                    ${index + 1}. ${escapeHtml(
                        stop.stop_name || "Bus Stop"
                    )}
                </strong>

                <br>

                <span style="
                    color:#64748b;
                    font-size:13px;
                ">
                    Route Stop
                </span>

            </div>
            `
        );

    });


    /* =====================================================
       DRAW ROUTE LINE
    ===================================================== */

    if (routeCoordinates.length >= 2) {

        L.polyline(
            routeCoordinates,
            {
                color: "#ef4444",

                weight: 5,

                opacity: 0.9,

                lineJoin: "round",

                lineCap: "round"
            }
        ).addTo(map);

    }


    /* =====================================================
       FIT MAP TO ROUTE
    ===================================================== */

    if (routeCoordinates.length === 1) {

        map.setView(
            routeCoordinates[0],
            15
        );

    } else {

        const bounds =
            L.latLngBounds(
                routeCoordinates
            );

        map.fitBounds(
            bounds,
            {
                padding: [
                    40,
                    40
                ]
            }
        );

    }


    /* =====================================================
       FIX MAP SIZE
    ===================================================== */

    setTimeout(function () {

        map.invalidateSize();

    }, 300);


    /* =====================================================
       ESCAPE HTML
    ===================================================== */

    function escapeHtml(value) {

        return String(value)

            .replace(
                /&/g,
                "&amp;"
            )

            .replace(
                /</g,
                "&lt;"
            )

            .replace(
                />/g,
                "&gt;"
            )

            .replace(
                /"/g,
                "&quot;"
            )

            .replace(
                /'/g,
                "&#039;"
            );

    }

});