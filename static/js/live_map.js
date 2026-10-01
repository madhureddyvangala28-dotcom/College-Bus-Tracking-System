// ==========================================================
// STUDENT LIVE BUS MAP
// Road Route + Stops + Live Bus + Next Stop + ETA
// ==========================================================

document.addEventListener("DOMContentLoaded", function () {

    // ======================================================
    // GET MAP ELEMENT
    // ======================================================

    const mapElement = document.getElementById("liveMap");

    if (!mapElement) {
        console.error("Live map element not found.");
        return;
    }

    // ======================================================
    // GET DATA FROM HTML
    // ======================================================

    const busId = mapElement.dataset.busid;

    const busNumber =
        mapElement.dataset.bus || "College Bus";

    const driverName =
        mapElement.dataset.driver || "Driver";

    let busLat =
        parseFloat(mapElement.dataset.lat);

    let busLng =
        parseFloat(mapElement.dataset.lng);

    let currentStop =
        mapElement.dataset.currentStop || "";

    let currentSpeed =
        parseFloat(mapElement.dataset.speed || 0);

    let currentEta =
        mapElement.dataset.eta || "--";

    const routeName =
        mapElement.dataset.route || "Bus Route";

    // ======================================================
    // GET ROUTE STOPS FROM FLASK
    // ======================================================

    let routeStops =
        Array.isArray(window.studentRouteStops)
            ? window.studentRouteStops
            : [];

    // ======================================================
    // CLEAN AND VALIDATE STOPS
    // ======================================================

    const validStops = routeStops
        .map(function (stop) {

            return {

                id: stop.id,

                route_id: stop.route_id,

                stop_name:
                    stop.stop_name || "Bus Stop",

                stop_order:
                    parseInt(stop.stop_order || 0, 10),

                latitude:
                    parseFloat(stop.latitude),

                longitude:
                    parseFloat(stop.longitude)

            };

        })

        .filter(function (stop) {

            return (
                Number.isFinite(stop.latitude) &&
                Number.isFinite(stop.longitude)
            );

        })

        .sort(function (a, b) {

            return a.stop_order - b.stop_order;

        });

    console.log("Bus ID:", busId);
    console.log("Route:", routeName);
    console.log("Current Stop:", currentStop);
    console.log("Valid Stops:", validStops);

    // ======================================================
    // FIND INITIAL MAP LOCATION
    // ======================================================

    let initialLat = busLat;
    let initialLng = busLng;

    if (
        !Number.isFinite(initialLat) ||
        !Number.isFinite(initialLng)
    ) {

        if (validStops.length > 0) {

            initialLat =
                validStops[0].latitude;

            initialLng =
                validStops[0].longitude;

        } else {

            // P.P. Savani / Surat fallback
            initialLat = 21.1702;
            initialLng = 72.8311;

        }

    }

    // ======================================================
    // CREATE LEAFLET MAP
    // ======================================================

    const map = L.map("liveMap", {

        zoomControl: true,

        scrollWheelZoom: true,

        attributionControl: true

    }).setView(
        [initialLat, initialLng],
        13
    );

    // ======================================================
    // OPEN STREET MAP
    // ======================================================

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,

            attribution:
                "&copy; OpenStreetMap contributors"
        }
    ).addTo(map);

    // ======================================================
    // MAP LAYERS
    // ======================================================

    let routeShadow = null;

    let routeLine = null;

    let remainingRouteShadow = null;

    let remainingRouteLine = null;

    let stopMarkers = [];

    let busMarker = null;

    // ======================================================
    // HELPER
    // ======================================================

    function escapeHtml(value) {

        const div =
            document.createElement("div");

        div.textContent =
            value == null
                ? ""
                : String(value);

        return div.innerHTML;

    }

    // ======================================================
    // CREATE STOP ICON
    // ======================================================

    function createStopIcon(number, type) {

        let className =
            "student-stop-marker";

        if (type === "current") {

            className += " current";

        }

        else if (type === "next") {

            className += " next";

        }

        return L.divIcon({

            className: "",

            html: `
                <div class="${className}">
                    <span>${number}</span>
                </div>
            `,

            iconSize: [38, 38],

            iconAnchor: [19, 19],

            popupAnchor: [0, -20]

        });

    }

    // ======================================================
// CREATE RED BUS PNG ICON
// ======================================================

function createBusIcon() {

    return L.divIcon({

        className: "student-live-bus-wrapper",

        html: `
            <div class="student-live-bus">
                <img
                    src="/static/images/bus-marker.png"
                    alt="Bus"
                >
            </div>
        `,

        iconSize: [64, 64],

        iconAnchor: [32, 32],

        popupAnchor: [0, -32]

    });

}
    // ======================================================
    // FIND CURRENT STOP INDEX
    // ======================================================

    function getCurrentStopIndex() {

        if (!currentStop) {
            return -1;
        }

        const current =
            currentStop.trim().toLowerCase();

        return validStops.findIndex(
            function (stop) {

                return (
                    stop.stop_name
                        .trim()
                        .toLowerCase() === current
                );

            }
        );

    }

    // ======================================================
    // GET NEXT STOP
    // ======================================================

    function getNextStop() {

        const currentIndex =
            getCurrentStopIndex();

        if (
            currentIndex >= 0 &&
            currentIndex < validStops.length - 1
        ) {

            return validStops[currentIndex + 1];

        }

        return null;

    }

    // ======================================================
    // DRAW STOP MARKERS
    // ======================================================

    function drawRouteStops() {

        // Remove old markers
        stopMarkers.forEach(function (marker) {

            map.removeLayer(marker);

        });

        stopMarkers = [];

        if (validStops.length === 0) {

            console.warn(
                "No valid route stops found."
            );

            return;

        }

        const currentIndex =
            getCurrentStopIndex();

        const nextIndex =
            currentIndex >= 0
                ? currentIndex + 1
                : -1;

        validStops.forEach(
            function (stop, index) {

                let markerType =
                    "normal";

                if (index === currentIndex) {

                    markerType =
                        "current";

                }

                else if (index === nextIndex) {

                    markerType =
                        "next";

                }

                const marker =
                    L.marker(
                        [
                            stop.latitude,
                            stop.longitude
                        ],
                        {
                            icon:
                                createStopIcon(
                                    stop.stop_order ||
                                    index + 1,
                                    markerType
                                ),

                            zIndexOffset: 500
                        }
                    ).addTo(map);

                // ==================================================
                // STOP POPUP
                // ==================================================

                let statusText =
                    "Route Stop";

                if (index === currentIndex) {

                    statusText =
                        "Current Stop";

                }

                else if (index === nextIndex) {

                    statusText =
                        "Next Stop";

                }

                marker.bindPopup(`

                    <div class="map-stop-popup">

                        <div class="popup-stop-number">

                            Stop ${escapeHtml(
                                stop.stop_order ||
                                index + 1
                            )}

                        </div>

                        <h3>

                            ${escapeHtml(
                                stop.stop_name
                            )}

                        </h3>

                        <p>

                            <i class="fa-solid fa-location-dot"></i>

                            ${statusText}

                        </p>

                    </div>

                `);

                stopMarkers.push(marker);

            }
        );

    }

    // ======================================================
    // GET ROAD ROUTE USING OSRM
    // ======================================================

    async function getRoadRoute(points) {

        if (!points || points.length < 2) {

            return null;

        }

        /*
         * OSRM expects:
         * longitude,latitude
         */

        const coordinates =
            points
                .map(function (point) {

                    return (
                        point[1] +
                        "," +
                        point[0]
                    );

                })
                .join(";");

        const url =
            "https://router.project-osrm.org/route/v1/driving/" +
            coordinates +
            "?overview=full&geometries=geojson&steps=false";

        try {

            const response =
                await fetch(url, {
                    method: "GET",
                    cache: "no-cache"
                });

            if (!response.ok) {

                throw new Error(
                    "OSRM request failed: " +
                    response.status
                );

            }

            const data =
                await response.json();

            if (
                data.code !== "Ok" ||
                !data.routes ||
                !data.routes.length
            ) {

                throw new Error(
                    "No road route returned."
                );

            }

            return data.routes[0];

        }

        catch (error) {

            console.error(
                "Road route error:",
                error
            );

            return null;

        }

    }

    // ======================================================
    // DRAW ROAD ROUTE
    // ======================================================

    async function drawRoadRoute() {

        if (validStops.length < 2) {

            console.warn(
                "At least two stops are required."
            );

            return;

        }

        const points =
            validStops.map(function (stop) {

                return [
                    stop.latitude,
                    stop.longitude
                ];

            });

        const roadRoute =
            await getRoadRoute(points);

        // ==================================================
        // REMOVE OLD ROUTE
        // ==================================================

        if (routeShadow) {

            map.removeLayer(routeShadow);

            routeShadow = null;

        }

        if (routeLine) {

            map.removeLayer(routeLine);

            routeLine = null;

        }

        // ==================================================
        // ROAD ROUTE SUCCESS
        // ==================================================

        if (roadRoute) {

            const roadCoordinates =
                roadRoute.geometry.coordinates
                    .map(function (coordinate) {

                        return [
                            coordinate[1],
                            coordinate[0]
                        ];

                    });

            // White outer border
            routeShadow =
                L.polyline(
                    roadCoordinates,
                    {
                        color: "#FFFFFF",

                        weight: 12,

                        opacity: 0.95,

                        lineCap: "round",

                        lineJoin: "round"
                    }
                ).addTo(map);

            // Yellow road route
            routeLine =
                L.polyline(
                    roadCoordinates,
                    {
                        color: "#FFC107",

                        weight: 7,

                        opacity: 1,

                        lineCap: "round",

                        lineJoin: "round"
                    }
                ).addTo(map);

            routeLine.bindPopup(`

                <div class="map-route-popup">

                    <strong>
                        ${escapeHtml(routeName)}
                    </strong>

                    <p>
                        ${validStops.length}
                        route stops
                    </p>

                    <p>
                        Road route
                    </p>

                </div>

            `);

            console.log(
                "Road route successfully drawn."
            );

            return;

        }

        // ==================================================
        // FALLBACK
        // ==================================================

        console.warn(
            "OSRM unavailable. Drawing fallback route."
        );

        const fallbackCoordinates =
            validStops.map(function (stop) {

                return [
                    stop.latitude,
                    stop.longitude
                ];

            });

        routeShadow =
            L.polyline(
                fallbackCoordinates,
                {
                    color: "#FFFFFF",

                    weight: 11,

                    opacity: 0.95,

                    lineCap: "round",

                    lineJoin: "round"
                }
            ).addTo(map);

        routeLine =
            L.polyline(
                fallbackCoordinates,
                {
                    color: "#FFC107",

                    weight: 6,

                    opacity: 1,

                    dashArray: "10 8",

                    lineCap: "round",

                    lineJoin: "round"
                }
            ).addTo(map);

    }

    // ======================================================
    // DRAW REMAINING ROAD ROUTE
    // BUS -> NEXT STOP
    // ======================================================

    async function drawRemainingRoute() {

        // Remove previous remaining route

        if (remainingRouteShadow) {

            map.removeLayer(
                remainingRouteShadow
            );

            remainingRouteShadow = null;

        }

        if (remainingRouteLine) {

            map.removeLayer(
                remainingRouteLine
            );

            remainingRouteLine = null;

        }

        const nextStop =
            getNextStop();

        if (
            !nextStop ||
            !Number.isFinite(busLat) ||
            !Number.isFinite(busLng)
        ) {

            return;

        }

        const points = [

            [
                busLat,
                busLng
            ],

            [
                nextStop.latitude,
                nextStop.longitude
            ]

        ];

        const roadRoute =
            await getRoadRoute(points);

        if (!roadRoute) {

            return;

        }

        const roadCoordinates =
            roadRoute.geometry.coordinates
                .map(function (coordinate) {

                    return [
                        coordinate[1],
                        coordinate[0]
                    ];

                });

        remainingRouteShadow =
            L.polyline(
                roadCoordinates,
                {
                    color: "#FFFFFF",

                    weight: 9,

                    opacity: 0.9,

                    lineCap: "round",

                    lineJoin: "round"
                }
            ).addTo(map);

        remainingRouteLine =
            L.polyline(
                roadCoordinates,
                {
                    color: "#16A34A",

                    weight: 5,

                    opacity: 1,

                    dashArray: "8 8",

                    lineCap: "round",

                    lineJoin: "round"
                }
            ).addTo(map);

    }

    // ======================================================
    // DRAW BUS MARKER
    // ======================================================

    function drawBusMarker() {

        if (busMarker) {

            map.removeLayer(busMarker);

            busMarker = null;

        }

        if (
            !Number.isFinite(busLat) ||
            !Number.isFinite(busLng)
        ) {

            console.warn(
                "Bus GPS coordinates unavailable."
            );

            return;

        }

        busMarker =
            L.marker(
                [
                    busLat,
                    busLng
                ],
                {
                    icon:
                        createBusIcon(),

                    zIndexOffset: 2000
                }
            ).addTo(map);

        updateBusPopup();

    }

    // ======================================================
    // BUS POPUP
    // ======================================================

    function updateBusPopup() {

        if (!busMarker) {
            return;
        }

        const nextStop =
            getNextStop();

        busMarker.bindPopup(`

            <div class="map-bus-popup">

                <h3>

                    <i class="fa-solid fa-bus"></i>

                    ${escapeHtml(busNumber)}

                </h3>

                <p>

                    <strong>Driver:</strong>

                    ${escapeHtml(driverName)}

                </p>

                <p>

                    <strong>Current Stop:</strong>

                    ${escapeHtml(
                        currentStop || "--"
                    )}

                </p>

                <p>

                    <strong>Next Stop:</strong>

                    ${escapeHtml(
                        nextStop
                            ? nextStop.stop_name
                            : "--"
                    )}

                </p>

                <p>

                    <strong>Speed:</strong>

                    ${
                        Number.isFinite(
                            currentSpeed
                        )
                            ? currentSpeed.toFixed(1)
                            : "0.0"
                    }
                    km/h

                </p>

                <p>

                    <strong>ETA:</strong>

                    ${escapeHtml(
                        currentEta
                    )}

                </p>

                <div class="live-status">

                    <span></span>

                    Live

                </div>

            </div>

        `);

    }

    // ======================================================
    // FIT MAP TO ROUTE
    // ======================================================

    function fitMapToRoute() {

        const points = [];

        validStops.forEach(
            function (stop) {

                points.push([
                    stop.latitude,
                    stop.longitude
                ]);

            }
        );

        if (
            Number.isFinite(busLat) &&
            Number.isFinite(busLng)
        ) {

            points.push([
                busLat,
                busLng
            ]);

        }

        if (points.length === 0) {

            return;

        }

        const bounds =
            L.latLngBounds(points);

        map.fitBounds(
            bounds,
            {
                padding: [45, 45],

                maxZoom: 15
            }
        );

    }

    // ======================================================
    // UPDATE LEFT SIDE INFORMATION
    // ======================================================

    function updatePageInformation(data) {

        const currentStopElement =
            document.getElementById(
                "currentStop"
            );

        const nextStopElement =
            document.getElementById(
                "nextStop"
            );

        const distanceElement =
            document.getElementById(
                "distanceRemaining"
            );

        const etaElement =
            document.getElementById(
                "busEta"
            );

        const speedElement =
            document.getElementById(
                "busSpeed"
            );

        const statusElement =
            document.getElementById(
                "busStatus"
            );

        const updatedElement =
            document.getElementById(
                "lastUpdated"
            );

        if (currentStopElement) {

            currentStopElement.textContent =
                currentStop || "--";

        }

        const nextStop =
            getNextStop();

        if (nextStopElement) {

            nextStopElement.textContent =
                nextStop
                    ? nextStop.stop_name
                    : "Destination";

        }

        if (etaElement) {

            etaElement.textContent =
                currentEta || "--";

        }

        if (speedElement) {

            speedElement.textContent =
                Number.isFinite(currentSpeed)
                    ? currentSpeed.toFixed(1) +
                      " km/h"
                    : "0.0 km/h";

        }

        if (statusElement) {

            const tripStatus =
                data.trip_status ||
                "Offline";

            if (
                tripStatus.toLowerCase() ===
                "online"
            ) {

                statusElement.innerHTML =
                    "🟢 Online";

            } else {

                statusElement.innerHTML =
                    "🔴 Offline";

            }

        }

        if (updatedElement) {

            updatedElement.textContent =
                data.last_updated ||
                "--";

        }

        // Distance is calculated below
        updateDistanceToNextStop();

    }

    // ======================================================
    // CALCULATE DISTANCE TO NEXT STOP
    // ======================================================

    function calculateDistance(
        lat1,
        lng1,
        lat2,
        lng2
    ) {

        const earthRadius = 6371;

        const dLat =
            (lat2 - lat1) *
            Math.PI / 180;

        const dLng =
            (lng2 - lng1) *
            Math.PI / 180;

        const a =
            Math.sin(dLat / 2) *
            Math.sin(dLat / 2) +

            Math.cos(
                lat1 * Math.PI / 180
            ) *

            Math.cos(
                lat2 * Math.PI / 180
            ) *

            Math.sin(dLng / 2) *
            Math.sin(dLng / 2);

        const c =
            2 *
            Math.atan2(
                Math.sqrt(a),
                Math.sqrt(1 - a)
            );

        return earthRadius * c;

    }

    // ======================================================
    // UPDATE DISTANCE
    // ======================================================

    function updateDistanceToNextStop() {

        const element =
            document.getElementById(
                "distanceRemaining"
            );

        if (!element) {
            return;
        }

        const nextStop =
            getNextStop();

        if (
            !nextStop ||
            !Number.isFinite(busLat) ||
            !Number.isFinite(busLng)
        ) {

            element.textContent =
                "--";

            return;

        }

        const distance =
            calculateDistance(
                busLat,
                busLng,
                nextStop.latitude,
                nextStop.longitude
            );

        element.textContent =
            distance.toFixed(2) +
            " km";

    }

    // ======================================================
    // DRAW INITIAL MAP
    // ======================================================

    drawRouteStops();

    drawBusMarker();

    fitMapToRoute();

    // Road route is asynchronous
    drawRoadRoute();

    drawRemainingRoute();

    // ======================================================
    // FIX LEAFLET SIZE
    // ======================================================

    setTimeout(function () {

        map.invalidateSize();

    }, 400);

    // ======================================================
    // GET LIVE BUS LOCATION
    // ======================================================

    async function updateBusLocation() {

        if (!busId) {

            console.warn(
                "Bus ID missing."
            );

            return;

        }

        try {

            const response =
                await fetch(
                    `/student/live_location/${busId}`,
                    {
                        method: "GET",

                        cache: "no-cache"
                    }
                );

            if (!response.ok) {

                throw new Error(
                    "Live location request failed: " +
                    response.status
                );

            }

            const data =
                await response.json();

            if (
                !data ||
                data.success === false
            ) {

                console.warn(
                    "No live bus location."
                );

                return;

            }

            const newLat =
                parseFloat(
                    data.latitude
                );

            const newLng =
                parseFloat(
                    data.longitude
                );

            if (
                !Number.isFinite(newLat) ||
                !Number.isFinite(newLng)
            ) {

                console.warn(
                    "Invalid GPS coordinates."
                );

                return;

            }

            // ==================================================
            // UPDATE VARIABLES
            // ==================================================

            busLat = newLat;

            busLng = newLng;

            currentStop =
                data.current_stop ||
                currentStop ||
                "";

            currentSpeed =
                parseFloat(
                    data.speed || 0
                );

            currentEta =
                data.eta || "--";

            // ==================================================
            // UPDATE BUS MARKER
            // ==================================================

            if (!busMarker) {

                drawBusMarker();

            }

            else {

                busMarker.setLatLng([
                    busLat,
                    busLng
                ]);

                updateBusPopup();

            }

            // ==================================================
            // UPDATE STOP MARKERS
            // ==================================================

            drawRouteStops();

            // ==================================================
            // UPDATE LEFT SIDE DATA
            // ==================================================

            updatePageInformation(data);

            // ==================================================
            // UPDATE REMAINING ROAD
            // ==================================================

            await drawRemainingRoute();

            // ==================================================
            // KEEP BUS VISIBLE
            // ==================================================

            if (
                !map.getBounds().contains([
                    busLat,
                    busLng
                ])
            ) {

                map.panTo(
                    [
                        busLat,
                        busLng
                    ],
                    {
                        animate: true,

                        duration: 1
                    }
                );

            }

        }

        catch (error) {

            console.error(
                "Live bus map update error:",
                error
            );

        }

    }

    // ======================================================
    // INITIAL LIVE UPDATE
    // ======================================================

    updateBusLocation();

    // ======================================================
    // UPDATE EVERY 10 SECONDS
    // ======================================================

    setInterval(
        updateBusLocation,
        10000
    );

    // ======================================================
    // WINDOW RESIZE
    // ======================================================

    window.addEventListener(
        "resize",
        function () {

            setTimeout(
                function () {

                    map.invalidateSize();

                },
                200
            );

        }
    );

});