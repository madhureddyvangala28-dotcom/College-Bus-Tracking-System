// ==========================================
// ROUTE & STOP COORDINATE MANAGER
// STEP 5.3.2
// LEAFLET + OSRM REAL ROAD ROUTING
// ==========================================


// ==========================================
// GLOBAL VARIABLES
// ==========================================

let map = null;

let marker = null;

let selectedStopId = null;

let routeStopMarkers = [];

let routeLine = null;

let toastTimer = null;

let currentRouteStops = [];


// ==========================================
// DEFAULT MAP LOCATION
// ==========================================

const DEFAULT_LATITUDE = 21.1702;

const DEFAULT_LONGITUDE = 72.8311;

const DEFAULT_ZOOM = 11;


// ==========================================
// INITIALIZE MAP
// ==========================================

map = L.map("coordinateMap").setView(
    [
        DEFAULT_LATITUDE,
        DEFAULT_LONGITUDE
    ],
    DEFAULT_ZOOM
);


// ==========================================
// OPENSTREETMAP TILE
// ==========================================

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution:
            "&copy; OpenStreetMap contributors",

        maxZoom: 19
    }
).addTo(map);


// ==========================================
// MAP CLICK
// ==========================================

map.on("click", function(e) {

    // --------------------------------------
    // STOP MUST BE SELECTED
    // --------------------------------------

    if (!selectedStopId) {

        showCoordinateToast(
            "Select a Stop",
            "Please select a bus stop before choosing a location.",
            "error"
        );

        return;
    }


    // --------------------------------------
    // GET COORDINATES
    // --------------------------------------

    const latitude =
        e.latlng.lat;

    const longitude =
        e.latlng.lng;


    // --------------------------------------
    // REMOVE OLD MARKER
    // --------------------------------------

    removeSelectedMarker();


    // --------------------------------------
    // CREATE NEW MARKER
    // --------------------------------------

    marker = L.marker(
        [
            latitude,
            longitude
        ],
        {
            draggable: true
        }
    ).addTo(map);


    // --------------------------------------
    // POPUP
    // --------------------------------------

    marker
        .bindPopup(
            "<b>Selected Stop Location</b><br>" +
            "Latitude: " +
            latitude.toFixed(7) +
            "<br>" +
            "Longitude: " +
            longitude.toFixed(7)
        )
        .openPopup();


    // --------------------------------------
    // UPDATE INPUTS
    // --------------------------------------

    updateCoordinateInputs(
        latitude,
        longitude
    );


    // --------------------------------------
    // ENABLE SAVE
    // --------------------------------------

    enableSaveButton();


    // --------------------------------------
    // DRAG EVENT
    // --------------------------------------

    attachMarkerDragEvent();

});


// ==========================================
// MARKER DRAG
// ==========================================

function attachMarkerDragEvent() {

    if (!marker) {

        return;

    }


    // Remove old drag event

    marker.off("dragend");


    // Add new drag event

    marker.on(
        "dragend",
        function() {

            const position =
                marker.getLatLng();


            const latitude =
                position.lat;

            const longitude =
                position.lng;


            // Update inputs

            updateCoordinateInputs(
                latitude,
                longitude
            );


            // Enable save

            enableSaveButton();


            // Update popup

            marker
                .bindPopup(
                    "<b>Updated Location</b><br>" +
                    "Latitude: " +
                    latitude.toFixed(7) +
                    "<br>" +
                    "Longitude: " +
                    longitude.toFixed(7)
                )
                .openPopup();

        }
    );

}


// ==========================================
// UPDATE COORDINATE INPUTS
// ==========================================

function updateCoordinateInputs(
    latitude,
    longitude
) {

    const latitudeInput =
        document.getElementById(
            "selectedLatitude"
        );


    const longitudeInput =
        document.getElementById(
            "selectedLongitude"
        );


    if (latitudeInput) {

        latitudeInput.value =
            Number(latitude).toFixed(7);

    }


    if (longitudeInput) {

        longitudeInput.value =
            Number(longitude).toFixed(7);

    }

}


// ==========================================
// ENABLE SAVE BUTTON
// ==========================================

function enableSaveButton() {

    const button =
        document.getElementById(
            "saveCoordinateBtn"
        );


    if (button) {

        button.disabled = false;

    }

}


// ==========================================
// DISABLE SAVE BUTTON
// ==========================================

function disableSaveButton() {

    const button =
        document.getElementById(
            "saveCoordinateBtn"
        );


    if (button) {

        button.disabled = true;

    }

}


// ==========================================
// REMOVE SELECTED MARKER
// ==========================================

function removeSelectedMarker() {

    if (marker) {

        map.removeLayer(marker);

        marker = null;

    }

}


// ==========================================
// CLEAR ROUTE STOP MARKERS
// ==========================================

function clearRouteMarkers() {

    routeStopMarkers.forEach(
        function(routeMarker) {

            map.removeLayer(
                routeMarker
            );

        }
    );


    routeStopMarkers = [];

}


// ==========================================
// CLEAR ROAD ROUTE
// ==========================================

function clearRouteLine() {

    if (routeLine) {

        map.removeLayer(
            routeLine
        );

        routeLine = null;

    }

}


// ==========================================
// RESET ROUTE INFORMATION
// STEP 5.3.2
// ==========================================

function resetRouteInformation() {

    const distanceElement =
        document.getElementById(
            "routeDistance"
        );


    const durationElement =
        document.getElementById(
            "routeDuration"
        );


    const totalStopsElement =
        document.getElementById(
            "routeTotalStops"
        );


    const mappedStopsElement =
        document.getElementById(
            "routeMappedStops"
        );


    const coverageElement =
        document.getElementById(
            "routeCoverage"
        );


    const coverageBar =
        document.getElementById(
            "routeCoverageBar"
        );


    const mappingMessage =
        document.getElementById(
            "routeMappingMessage"
        );


    if (distanceElement) {

        distanceElement.textContent =
            "—";

    }


    if (durationElement) {

        durationElement.textContent =
            "—";

    }


    if (totalStopsElement) {

        totalStopsElement.textContent =
            "—";

    }


    if (mappedStopsElement) {

        mappedStopsElement.textContent =
            "—";

    }


    if (coverageElement) {

        coverageElement.textContent =
            "0%";

    }


    if (coverageBar) {

        coverageBar.style.width =
            "0%";

    }


    if (mappingMessage) {

        mappingMessage.textContent =
            "Select a route to view information.";

    }

}


// ==========================================
// UPDATE ROUTE INFORMATION
// STEP 5.3.2
// ==========================================

function updateRouteInformation(
    distanceKm,
    durationMinutes,
    totalStops,
    mappedStops
) {

    const distanceElement =
        document.getElementById(
            "routeDistance"
        );


    const durationElement =
        document.getElementById(
            "routeDuration"
        );


    const totalStopsElement =
        document.getElementById(
            "routeTotalStops"
        );


    const mappedStopsElement =
        document.getElementById(
            "routeMappedStops"
        );


    const coverageElement =
        document.getElementById(
            "routeCoverage"
        );


    const coverageBar =
        document.getElementById(
            "routeCoverageBar"
        );


    const mappingMessage =
        document.getElementById(
            "routeMappingMessage"
        );


    // ======================================
    // DISTANCE
    // ======================================

    if (distanceElement) {

        distanceElement.textContent =
            Number(distanceKm).toFixed(2) +
            " km";

    }


    // ======================================
    // TRAVEL TIME
    // ======================================

    if (durationElement) {

        const minutes =
            Number(durationMinutes);


        if (minutes < 60) {

            durationElement.textContent =
                minutes +
                " min";

        }

        else {

            const hours =
                Math.floor(
                    minutes / 60
                );


            const remainingMinutes =
                minutes % 60;


            if (remainingMinutes === 0) {

                durationElement.textContent =
                    hours +
                    " hr";

            }

            else {

                durationElement.textContent =
                    hours +
                    " hr " +
                    remainingMinutes +
                    " min";

            }

        }

    }


    // ======================================
    // TOTAL STOPS
    // ======================================

    if (totalStopsElement) {

        totalStopsElement.textContent =
            totalStops;

    }


    // ======================================
    // MAPPED STOPS
    // ======================================

    if (mappedStopsElement) {

        mappedStopsElement.textContent =
            mappedStops +
            " / " +
            totalStops;

    }


    // ======================================
    // COVERAGE
    // ======================================

    let coverage = 0;


    if (totalStops > 0) {

        coverage =
            Math.round(
                (
                    mappedStops /
                    totalStops
                ) * 100
            );

    }


    if (coverageElement) {

        coverageElement.textContent =
            coverage +
            "%";

    }


    if (coverageBar) {

        coverageBar.style.width =
            coverage +
            "%";

    }


    // ======================================
    // MESSAGE
    // ======================================

    if (mappingMessage) {

        if (
            mappedStops === totalStops &&
            totalStops > 0
        ) {

            mappingMessage.textContent =
                "All stops have coordinates.";

        }

        else {

            const missing =
                totalStops -
                mappedStops;


            mappingMessage.textContent =
                missing +
                " stop" +
                (
                    missing === 1
                        ? ""
                        : "s"
                ) +
                " still need coordinates.";

        }

    }

}


// ==========================================
// REAL ROAD ROUTE USING OSRM
// STEP 5.3.1
// ==========================================

async function drawRealRoadRoute(stops) {

    // --------------------------------------
    // REMOVE OLD ROUTE
    // --------------------------------------

    clearRouteLine();


    // --------------------------------------
    // VALIDATE STOPS
    // --------------------------------------

    if (
        !Array.isArray(stops) ||
        stops.length < 2
    ) {

        console.log(
            "Not enough stops for road routing."
        );

        return;

    }


    // --------------------------------------
    // SORT STOPS
    // --------------------------------------

    const sortedStops =
        [...stops].sort(
            function(a, b) {

                return (
                    Number(a.stop_order) -
                    Number(b.stop_order)
                );

            }
        );


    // --------------------------------------
    // GET STOPS WITH COORDINATES
    // --------------------------------------

    const validStops =
        sortedStops.filter(
            function(stop) {

                return (
                    stop.latitude !== null &&
                    stop.latitude !== "" &&
                    stop.latitude !== undefined &&
                    stop.longitude !== null &&
                    stop.longitude !== "" &&
                    stop.longitude !== undefined
                );

            }
        );


    // --------------------------------------
    // NEED AT LEAST TWO
    // --------------------------------------

    if (validStops.length < 2) {

        console.log(
            "At least 2 stops need coordinates."
        );

        return;

    }


    // --------------------------------------
    // CREATE OSRM COORDINATES
    // --------------------------------------
    // OSRM uses:
    // longitude,latitude
    // --------------------------------------

    const coordinates =
        validStops
            .map(
                function(stop) {

                    return (
                        parseFloat(
                            stop.longitude
                        ) +
                        "," +
                        parseFloat(
                            stop.latitude
                        )
                    );

                }
            )
            .join(";");


    // --------------------------------------
    // OSRM URL
    // --------------------------------------

    const url =
        "https://router.project-osrm.org/" +
        "route/v1/driving/" +
        coordinates +
        "?overview=full" +
        "&geometries=geojson" +
        "&steps=false";


    console.log(
        "OSRM Request:",
        url
    );


    try {

        // ----------------------------------
        // REQUEST OSRM
        // ----------------------------------

        const response =
            await fetch(url);


        if (!response.ok) {

            throw new Error(
                "OSRM request failed."
            );

        }


        // ----------------------------------
        // JSON
        // ----------------------------------

        const data =
            await response.json();


        console.log(
            "OSRM Response:",
            data
        );


        // ----------------------------------
        // CHECK RESULT
        // ----------------------------------

        if (
            data.code !== "Ok" ||
            !data.routes ||
            data.routes.length === 0
        ) {

            throw new Error(
                "No road route returned by OSRM."
            );

        }


        // ----------------------------------
        // FIRST ROUTE
        // ----------------------------------

        const route =
            data.routes[0];


        // ----------------------------------
        // ROAD GEOMETRY
        // ----------------------------------

        const roadCoordinates =
            route.geometry.coordinates.map(
                function(coordinate) {

                    return [
                        coordinate[1],
                        coordinate[0]
                    ];

                }
            );


        // ----------------------------------
        // DRAW ROAD ROUTE
        // ----------------------------------

        routeLine =
            L.polyline(
                roadCoordinates,
                {
                    color: "#2563eb",

                    weight: 6,

                    opacity: 0.9,

                    lineJoin: "round",

                    lineCap: "round"
                }
            ).addTo(map);


        // ----------------------------------
        // REAL DISTANCE
        // ----------------------------------

        const distanceMeters =
            Number(route.distance);


        const distanceKm =
            distanceMeters / 1000;


        // ----------------------------------
        // REAL DURATION
        // ----------------------------------

        const durationSeconds =
            Number(route.duration);


        const durationMinutes =
            Math.round(
                durationSeconds / 60
            );


        // ----------------------------------
        // SAVE GLOBAL INFORMATION
        // ----------------------------------

        window.currentRouteDistanceKm =
            distanceKm;


        window.currentRouteDurationMinutes =
            durationMinutes;


        window.currentRouteMappedStops =
            validStops.length;


        window.currentRouteTotalStops =
            sortedStops.length;


        // ==================================
        // STEP 5.3.2
        // UPDATE INFORMATION CARD
        // ==================================

        updateRouteInformation(
            distanceKm,
            durationMinutes,
            sortedStops.length,
            validStops.length
        );


        // ----------------------------------
        // CONSOLE
        // ----------------------------------

        console.log(
            "Real Route Distance:",
            distanceKm.toFixed(2),
            "km"
        );


        console.log(
            "Real Route Duration:",
            durationMinutes,
            "minutes"
        );


        console.log(
            "Mapped Stops:",
            validStops.length,
            "/",
            sortedStops.length
        );


        // ----------------------------------
        // ROUTE POPUP
        // ----------------------------------

        routeLine.bindPopup(
            `
            <div style="
                min-width:190px;
                text-align:center;
                line-height:1.7;
            ">

                <strong>
                    Real Road Route
                </strong>

                <br>

                📏 Distance:
                ${distanceKm.toFixed(2)} km

                <br>

                ⏱ Duration:
                ${durationMinutes} minutes

                <br>

                🚏 Stops:
                ${validStops.length}
                /
                ${sortedStops.length}

            </div>
            `
        );


        console.log(
            "OSRM route successfully loaded."
        );

    }

    catch (error) {

        console.error(
            "OSRM routing error:",
            error
        );


        showCoordinateToast(
            "Route Error",
            "Unable to calculate the real road route.",
            "error"
        );

    }

}


// ==========================================
// DISPLAY ROUTE STOP MARKERS
// ==========================================

function displayRouteStopMarkers(
    stops
) {

    // --------------------------------------
    // REMOVE OLD MARKERS
    // --------------------------------------

    clearRouteMarkers();


    if (
        !Array.isArray(stops) ||
        stops.length === 0
    ) {

        return;

    }


    // --------------------------------------
    // SORT
    // --------------------------------------

    const sortedStops =
        [...stops].sort(
            function(a, b) {

                return (
                    Number(a.stop_order) -
                    Number(b.stop_order)
                );

            }
        );


    const bounds = [];


    // --------------------------------------
    // CREATE MARKERS
    // --------------------------------------

    sortedStops.forEach(
        function(stop) {

            // ------------------------------
            // CHECK COORDINATES
            // ------------------------------

            if (
                stop.latitude === null ||
                stop.latitude === "" ||
                stop.latitude === undefined ||
                stop.longitude === null ||
                stop.longitude === "" ||
                stop.longitude === undefined
            ) {

                return;

            }


            const latitude =
                parseFloat(
                    stop.latitude
                );


            const longitude =
                parseFloat(
                    stop.longitude
                );


            if (
                Number.isNaN(latitude) ||
                Number.isNaN(longitude)
            ) {

                return;

            }


            // ------------------------------
            // CREATE MARKER
            // ------------------------------

            const routeMarker =
                L.marker(
                    [
                        latitude,
                        longitude
                    ]
                ).addTo(map);


            // ------------------------------
            // POPUP
            // ------------------------------

            routeMarker.bindPopup(
                `
                <div style="
                    min-width:180px;
                    text-align:center;
                    line-height:1.6;
                ">

                    <strong>
                        Stop
                        ${escapeHtml(
                            stop.stop_order
                        )}
                    </strong>

                    <br>

                    ${escapeHtml(
                        stop.stop_name
                    )}

                    <br>

                    <small>
                        ${latitude.toFixed(7)},
                        ${longitude.toFixed(7)}
                    </small>

                </div>
                `
            );


            // ------------------------------
            // CLICK MARKER
            // ------------------------------

            routeMarker.on(
                "click",
                function() {

                    const stopCard =
                        document.querySelector(
                            '.stop-card[data-stop-id="' +
                            stop.id +
                            '"]'
                        );


                    if (stopCard) {

                        stopCard.click();

                    }

                }
            );


            routeStopMarkers.push(
                routeMarker
            );


            bounds.push(
                [
                    latitude,
                    longitude
                ]
            );

        }
    );


    // --------------------------------------
    // FIT MAP
    // --------------------------------------

    if (bounds.length > 0) {

        map.fitBounds(
            bounds,
            {
                padding: [
                    50,
                    50
                ],

                maxZoom: 16
            }
        );

    }

}


// ==========================================
// ROUTE DROPDOWN
// ==========================================

const routeSelect =
    document.getElementById(
        "routeSelect"
    );


if (routeSelect) {

    routeSelect.addEventListener(
        "change",
        function() {

            const routeId =
                this.value;


            // ==================================
            // RESET VARIABLES
            // ==================================

            selectedStopId = null;

            currentRouteStops = [];


            // ==================================
            // REMOVE MARKERS / ROUTE
            // ==================================

            removeSelectedMarker();

            clearRouteMarkers();

            clearRouteLine();


            // ==================================
            // RESET INFORMATION CARD
            // ==================================

            resetRouteInformation();


            // ==================================
            // DISABLE SAVE
            // ==================================

            disableSaveButton();


            // ==================================
            // CLEAR INPUTS
            // ==================================

            const stopNameInput =
                document.getElementById(
                    "selectedStopName"
                );


            const latitudeInput =
                document.getElementById(
                    "selectedLatitude"
                );


            const longitudeInput =
                document.getElementById(
                    "selectedLongitude"
                );


            if (stopNameInput) {

                stopNameInput.value = "";

            }


            if (latitudeInput) {

                latitudeInput.value = "";

            }


            if (longitudeInput) {

                longitudeInput.value = "";

            }


            // ==================================
            // STOP LIST
            // ==================================

            const stopList =
                document.getElementById(
                    "stopList"
                );


            if (stopList) {

                stopList.innerHTML = "";

            }


            // ==================================
            // NO ROUTE
            // ==================================

            if (routeId === "") {

                map.setView(
                    [
                        DEFAULT_LATITUDE,
                        DEFAULT_LONGITUDE
                    ],
                    DEFAULT_ZOOM
                );

                return;

            }


            // ==================================
            // FETCH ROUTE STOPS
            // ==================================

            fetch(
                "/admin/get_route_stops/" +
                encodeURIComponent(
                    routeId
                )
            )


            .then(
                function(response) {

                    if (!response.ok) {

                        throw new Error(
                            "Failed to load stops."
                        );

                    }


                    return response.json();

                }
            )


            .then(
                function(data) {

                    if (
                        !Array.isArray(data)
                    ) {

                        throw new Error(
                            "Invalid stop data."
                        );

                    }


                    // ==================================
                    // SAVE STOPS
                    // ==================================

                    currentRouteStops =
                        data;


                    // ==================================
                    // EMPTY ROUTE
                    // ==================================

                    if (data.length === 0) {

                        if (stopList) {

                            stopList.innerHTML = `
                                <div class="empty-stops">
                                    No stops found for this route.
                                </div>
                            `;

                        }

                        return;

                    }


                    // ==================================
                    // BUILD STOP LIST
                    // ==================================

                    let html = "";


                    data.forEach(
                        function(stop) {

                            let icon =
                                "🔴";


                            // Has coordinates

                            if (
                                stop.latitude !== null &&
                                stop.latitude !== "" &&
                                stop.latitude !== undefined &&
                                stop.longitude !== null &&
                                stop.longitude !== "" &&
                                stop.longitude !== undefined
                            ) {

                                icon =
                                    "🟢";

                            }


                            html += `
                                <div
                                    class="stop-card"
                                    data-stop-id="${stop.id}"
                                    onclick="selectStop(
                                        event,
                                        ${stop.id},
                                        '${escapeJs(
                                            stop.stop_name
                                        )}',
                                        '${stop.latitude ?? ""}',
                                        '${stop.longitude ?? ""}'
                                    )"
                                >

                                    <span class="stop-status">
                                        ${icon}
                                    </span>

                                    <span class="stop-name">
                                        ${stop.stop_order}.
                                        ${escapeHtml(
                                            stop.stop_name
                                        )}
                                    </span>

                                </div>
                            `;

                        }
                    );


                    if (stopList) {

                        stopList.innerHTML =
                            html;

                    }


                    // ==================================
                    // DISPLAY STOP MARKERS
                    // ==================================

                    displayRouteStopMarkers(
                        data
                    );


                    // ==================================
                    // STEP 5.3.1
                    // REAL OSRM ROAD ROUTE
                    // ==================================

                    drawRealRoadRoute(
                        data
                    );

                }
            )


            .catch(
                function(error) {

                    console.error(
                        "Route stops error:",
                        error
                    );


                    if (stopList) {

                        stopList.innerHTML = `
                            <div class="empty-stops">
                                Unable to load bus stops.
                            </div>
                        `;

                    }


                    showCoordinateToast(
                        "Loading Error",
                        "Unable to load route stops.",
                        "error"
                    );

                }
            );

        }
    );

}


// ==========================================
// SELECT STOP
// ==========================================

function selectStop(
    event,
    id,
    name,
    lat,
    lng
) {

    selectedStopId =
        id;


    // ======================================
    // REMOVE ACTIVE CLASS
    // ======================================

    document
        .querySelectorAll(
            ".stop-card"
        )
        .forEach(
            function(card) {

                card.classList.remove(
                    "active"
                );

            }
        );


    // ======================================
    // ACTIVE STOP
    // ======================================

    if (
        event &&
        event.currentTarget
    ) {

        event.currentTarget.classList.add(
            "active"
        );

    }


    // ======================================
    // STOP NAME
    // ======================================

    const stopNameInput =
        document.getElementById(
            "selectedStopName"
        );


    if (stopNameInput) {

        stopNameInput.value =
            name;

    }


    // ======================================
    // CHECK COORDINATES
    // ======================================

    const hasCoordinates =
        lat !== "" &&
        lat !== null &&
        lat !== undefined &&
        lat !== "null" &&
        lng !== "" &&
        lng !== null &&
        lng !== undefined &&
        lng !== "null";


    // ======================================
    // EXISTING COORDINATES
    // ======================================

    if (hasCoordinates) {

        const latitude =
            parseFloat(lat);


        const longitude =
            parseFloat(lng);


        if (
            !Number.isNaN(latitude) &&
            !Number.isNaN(longitude)
        ) {

            // ------------------------------
            // UPDATE INPUTS
            // ------------------------------

            updateCoordinateInputs(
                latitude,
                longitude
            );


            // ------------------------------
            // REMOVE OLD MARKER
            // ------------------------------

            removeSelectedMarker();


            // ------------------------------
            // CREATE MARKER
            // ------------------------------

            marker =
                L.marker(
                    [
                        latitude,
                        longitude
                    ],
                    {
                        draggable: true
                    }
                )
                .addTo(map);


            // ------------------------------
            // POPUP
            // ------------------------------

            marker
                .bindPopup(
                    "<b>" +
                    escapeHtml(name) +
                    "</b><br>" +
                    "Coordinates saved"
                )
                .openPopup();


            // ------------------------------
            // MOVE MAP
            // ------------------------------

            map.flyTo(
                [
                    latitude,
                    longitude
                ],
                17,
                {
                    animate: true,
                    duration: 1
                }
            );


            // ------------------------------
            // DRAG EVENT
            // ------------------------------

            attachMarkerDragEvent();


            // ------------------------------
            // ENABLE SAVE
            // ------------------------------

            enableSaveButton();

        }

    }


    // ======================================
    // NO COORDINATES
    // ======================================

    else {

        const latitudeInput =
            document.getElementById(
                "selectedLatitude"
            );


        const longitudeInput =
            document.getElementById(
                "selectedLongitude"
            );


        if (latitudeInput) {

            latitudeInput.value = "";

        }


        if (longitudeInput) {

            longitudeInput.value = "";

        }


        // Remove marker

        removeSelectedMarker();


        // Disable save

        disableSaveButton();


        // Return map to default

        map.setView(
            [
                DEFAULT_LATITUDE,
                DEFAULT_LONGITUDE
            ],
            DEFAULT_ZOOM
        );

    }

}


// ==========================================
// SAVE COORDINATES
// ==========================================

const saveCoordinateButton =
    document.getElementById(
        "saveCoordinateBtn"
    );


if (saveCoordinateButton) {

    saveCoordinateButton.addEventListener(
        "click",
        function() {

            // ==================================
            // INPUTS
            // ==================================

            const latitudeInput =
                document.getElementById(
                    "selectedLatitude"
                );


            const longitudeInput =
                document.getElementById(
                    "selectedLongitude"
                );


            const latitude =
                latitudeInput
                    ? latitudeInput.value
                    : "";


            const longitude =
                longitudeInput
                    ? longitudeInput.value
                    : "";


            // ==================================
            // VALIDATE STOP
            // ==================================

            if (!selectedStopId) {

                showCoordinateToast(
                    "No Stop Selected",
                    "Please select a bus stop first.",
                    "error"
                );

                return;

            }


            // ==================================
            // VALIDATE COORDINATES
            // ==================================

            if (
                latitude === "" ||
                longitude === ""
            ) {

                showCoordinateToast(
                    "Location Required",
                    "Please select a location on the map.",
                    "error"
                );

                return;

            }


            const latitudeNumber =
                parseFloat(latitude);


            const longitudeNumber =
                parseFloat(longitude);


            if (
                Number.isNaN(latitudeNumber) ||
                Number.isNaN(longitudeNumber)
            ) {

                showCoordinateToast(
                    "Invalid Coordinates",
                    "Please select a valid location.",
                    "error"
                );

                return;

            }


            // ==================================
            // SAVE BUTTON STATE
            // ==================================

            const originalText =
                saveCoordinateButton.innerHTML;


            saveCoordinateButton.disabled =
                true;


            saveCoordinateButton.innerHTML = `
                <i class="fas fa-spinner fa-spin"></i>
                Saving...
            `;


            // ==================================
            // SEND TO FLASK
            // ==================================

            fetch(
                "/admin/save_stop_coordinates",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        stop_id:
                            selectedStopId,

                        latitude:
                            latitudeNumber,

                        longitude:
                            longitudeNumber

                    })

                }
            )


            .then(
                function(response) {

                    return response.json()
                        .then(
                            function(data) {

                                return {
                                    ok:
                                        response.ok,

                                    data:
                                        data
                                };

                            }
                        );

                }
            )


            .then(
                function(result) {

                    const data =
                        result.data;


                    // ==================================
                    // SUCCESS
                    // ==================================

                    if (
                        result.ok &&
                        data.status === "success"
                    ) {

                        showCoordinateToast(
                            "Coordinates Saved",
                            data.message ||
                            "Coordinates saved successfully.",
                            "success"
                        );


                        // ----------------------------------
                        // REFRESH CURRENT ROUTE
                        // ----------------------------------

                        if (
                            routeSelect &&
                            routeSelect.value
                        ) {

                            routeSelect.dispatchEvent(
                                new Event(
                                    "change"
                                )
                            );

                        }

                    }


                    // ==================================
                    // FAILED
                    // ==================================

                    else {

                        showCoordinateToast(
                            "Save Failed",
                            data.message ||
                            "Unable to save coordinates.",
                            "error"
                        );

                    }

                }
            )


            .catch(
                function(error) {

                    console.error(
                        "Save coordinates error:",
                        error
                    );


                    showCoordinateToast(
                        "Connection Error",
                        "Unable to connect to the server.",
                        "error"
                    );

                }
            )


            .finally(
                function() {

                    saveCoordinateButton.disabled =
                        false;


                    saveCoordinateButton.innerHTML =
                        originalText;

                }
            );

        }
    );

}


// ==========================================
// ESCAPE HTML
// ==========================================

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


// ==========================================
// ESCAPE JAVASCRIPT STRING
// ==========================================

function escapeJs(value) {

    return String(value)

        .replace(
            /\\/g,
            "\\\\"
        )

        .replace(
            /'/g,
            "\\'"
        )

        .replace(
            /\r?\n/g,
            " "
        );

}


// ==========================================
// TOAST
// ==========================================

function showCoordinateToast(
    title,
    message,
    type = "success"
) {

    const toast =
        document.getElementById(
            "coordinateToast"
        );


    const toastTitle =
        document.getElementById(
            "toastTitle"
        );


    const toastMessage =
        document.getElementById(
            "toastMessage"
        );


    // ======================================
    // IF TOAST DOES NOT EXIST
    // ======================================

    if (
        !toast ||
        !toastTitle ||
        !toastMessage
    ) {

        console.log(
            title +
            ": " +
            message
        );

        return;

    }


    // ======================================
    // ICON
    // ======================================

    const toastIcon =
        toast.querySelector(
            ".toast-icon i"
        );


    // ======================================
    // TEXT
    // ======================================

    toastTitle.textContent =
        title;


    toastMessage.textContent =
        message;


    // ======================================
    // REMOVE OLD CLASSES
    // ======================================

    toast.classList.remove(
        "toast-success",
        "toast-error"
    );


    // ======================================
    // SUCCESS
    // ======================================

    if (type === "success") {

        toast.classList.add(
            "toast-success"
        );


        toast.style.borderLeftColor =
            "#16a34a";


        if (toastIcon) {

            toastIcon.className =
                "fas fa-check";

        }

    }


    // ======================================
    // ERROR
    // ======================================

    else {

        toast.classList.add(
            "toast-error"
        );


        toast.style.borderLeftColor =
            "#dc2626";


        if (toastIcon) {

            toastIcon.className =
                "fas fa-xmark";

        }

    }


    // ======================================
    // SHOW
    // ======================================

    toast.classList.add(
        "show"
    );


    // ======================================
    // AUTO HIDE
    // ======================================

    clearTimeout(
        toastTimer
    );


    toastTimer =
        setTimeout(
            function() {

                hideCoordinateToast();

            },
            4000
        );

}


// ==========================================
// HIDE TOAST
// ==========================================

function hideCoordinateToast() {

    const toast =
        document.getElementById(
            "coordinateToast"
        );


    if (toast) {

        toast.classList.remove(
            "show"
        );

    }

}


// ==========================================
// MAP RESIZE
// ==========================================

window.addEventListener(
    "load",
    function() {

        setTimeout(
            function() {

                if (map) {

                    map.invalidateSize();

                }

            },
            300
        );

    }
);