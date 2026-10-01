/* =====================================================
   ADMIN LIVE FLEET
===================================================== */

document.addEventListener("DOMContentLoaded", function () {


    /* =================================================
       DATA
    ================================================= */

    const data = window.adminFleetData || {};

    let buses = data.buses || [];

    const routes = data.routes || [];

    const stops = data.stops || [];


    /* =================================================
       MAP
    ================================================= */

    const map = L.map("fleetMap", {
        zoomControl: true
    }).setView([21.17, 72.83], 11);


    /* =================================================
       TILE LAYER
    ================================================= */

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,
            attribution:
                '&copy; OpenStreetMap contributors'
        }
    ).addTo(map);


    /* =================================================
       LAYERS
    ================================================= */

    const routeLayer = L.layerGroup().addTo(map);

    const stopLayer = L.layerGroup().addTo(map);

    const busLayer = L.layerGroup().addTo(map);


    /* =================================================
       MARKERS
    ================================================= */

    const busMarkers = {};

    const routeLines = {};

    const stopMarkers = {};


    /* =================================================
       CREATE BUS ICON
    ================================================= */

    function createBusIcon(status) {

        return L.divIcon({

            className: "admin-bus-wrapper",

            html: `
                <div class="admin-bus-marker ${status}">
                    <i class="fa-solid fa-bus"></i>
                </div>
            `,

            iconSize: [48, 48],

            iconAnchor: [24, 24],

            popupAnchor: [0, -24]

        });

    }


    /* =================================================
       GET BUS STATUS
    ================================================= */

    function getBusStatus(bus) {

        const speed =
            parseFloat(bus.speed || 0);

        if (bus.trip_status === "Online") {

            if (speed > 0) {

                return "moving";

            }

            return "stopped";

        }

        return "offline";

    }


    /* =================================================
       CREATE BUS POPUP
    ================================================= */

    function createBusPopup(bus) {

        const speed =
            parseFloat(bus.speed || 0).toFixed(1);

        const status =
            getBusStatus(bus);


        let statusText = "Offline";


        if (status === "moving") {

            statusText = "🟢 Moving";

        } else if (status === "stopped") {

            statusText = "🟡 Stopped";

        } else {

            statusText = "🔴 Offline";

        }


        return `

            <div class="fleet-popup">

                <h3>
                    🚌 ${bus.bus_number || "Bus"}
                </h3>

                <div class="popup-driver">
                    ${bus.driver_name || "Driver not assigned"}
                </div>


                <div class="popup-row">

                    <span>Route</span>

                    <strong>
                        ${bus.route_name || "—"}
                    </strong>

                </div>


                <div class="popup-row">

                    <span>Current Stop</span>

                    <strong>
                        ${bus.current_stop || "—"}
                    </strong>

                </div>


                <div class="popup-row">

                    <span>Speed</span>

                    <strong>
                        ${speed} km/h
                    </strong>

                </div>


                <div class="popup-row">

                    <span>ETA</span>

                    <strong>
                        ${bus.eta || "—"}
                    </strong>

                </div>


                <div class="popup-row">

                    <span>Status</span>

                    <strong>
                        ${statusText}
                    </strong>

                </div>


                <div class="popup-row">

                    <span>Updated</span>

                    <strong>
                        ${bus.last_updated || "—"}
                    </strong>

                </div>

            </div>

        `;

    }


    /* =================================================
       DRAW ROUTES USING ACTUAL ROADS
       
       IMPORTANT:
       The old code used L.polyline(), which connected
       stops using straight lines.

       This version sends all route stops to OSRM and
       receives actual road geometry.
    ================================================= */

    async function drawRoutes() {

        routeLayer.clearLayers();


        /* ---------------------------------------------
           Clear previously stored route lines
        --------------------------------------------- */

        Object.keys(routeLines).forEach(routeId => {

            delete routeLines[routeId];

        });


        /* ---------------------------------------------
           Group stops according to route
        --------------------------------------------- */

        const grouped = {};


        stops.forEach(stop => {

            const routeId = stop.route_id;

            if (!routeId) {

                return;

            }


            if (!grouped[routeId]) {

                grouped[routeId] = [];

            }


            grouped[routeId].push(stop);

        });


        /* ---------------------------------------------
           Calculate road route for every route
        --------------------------------------------- */

        for (const routeId of Object.keys(grouped)) {


            /* -----------------------------------------
               Sort stops by stop order
            ----------------------------------------- */

            const routeStops =
                grouped[routeId]
                    .filter(stop => {

                        return (
                            stop.latitude !== null &&
                            stop.longitude !== null &&
                            Number.isFinite(
                                Number(stop.latitude)
                            ) &&
                            Number.isFinite(
                                Number(stop.longitude)
                            )
                        );

                    })
                    .sort(
                        (a, b) =>
                            Number(a.stop_order) -
                            Number(b.stop_order)
                    );


            /* -----------------------------------------
               At least 2 stops are required
            ----------------------------------------- */

            if (routeStops.length < 2) {

                console.warn(
                    "Not enough stops for route:",
                    routeId
                );

                continue;

            }


            /* -----------------------------------------
               Convert coordinates to OSRM format

               OSRM requires:

               longitude,latitude

               Example:

               72.1234,21.1234
            ----------------------------------------- */

            const coordinates =
                routeStops
                    .map(stop => {

                        return (
                            Number(stop.longitude) +
                            "," +
                            Number(stop.latitude)
                        );

                    })
                    .join(";");


            /* -----------------------------------------
               OSRM routing URL

               overview=full
               = complete road geometry

               geometries=geojson
               = easy to draw with Leaflet
            ----------------------------------------- */

            const routingUrl =
                "https://router.project-osrm.org/route/v1/driving/" +
                coordinates +
                "?overview=full&geometries=geojson&steps=false";


            try {


                /* -------------------------------------
                   Request road route
                ------------------------------------- */

                const response =
                    await fetch(
                        routingUrl,
                        {
                            method: "GET",
                            cache: "no-store"
                        }
                    );


                if (!response.ok) {

                    throw new Error(
                        "OSRM request failed: " +
                        response.status
                    );

                }


                /* -------------------------------------
                   Convert response to JSON
                ------------------------------------- */

                const result =
                    await response.json();


                /* -------------------------------------
                   Validate OSRM result
                ------------------------------------- */

                if (
                    result.code !== "Ok" ||
                    !result.routes ||
                    !result.routes.length ||
                    !result.routes[0].geometry
                ) {

                    console.warn(
                        "No road route returned for route:",
                        routeId
                    );

                    continue;

                }


                /* -------------------------------------
                   Actual road geometry
                ------------------------------------- */

                const geometry =
                    result.routes[0].geometry;


                /* -------------------------------------
                   Draw actual road-following route
                ------------------------------------- */

                const line =
                    L.geoJSON(
                        geometry,
                        {

                            style: {

                                color: "#ffc107",

                                weight: 6,

                                opacity: 0.90,

                                lineJoin: "round",

                                lineCap: "round"

                            }

                        }
                    );


                /* -------------------------------------
                   Route tooltip
                ------------------------------------- */

                line.bindTooltip(
                    getRouteName(routeId),
                    {
                        sticky: true
                    }
                );


                /* -------------------------------------
                   Add route to map
                ------------------------------------- */

                line.addTo(routeLayer);


                /* -------------------------------------
                   Save route reference
                ------------------------------------- */

                routeLines[routeId] = line;


            } catch (error) {

                console.error(
                    "Road route calculation failed for route:",
                    routeId,
                    error
                );

            }

        }

    }


    /* =================================================
       GET ROUTE NAME
    ================================================= */

    function getRouteName(routeId) {

        const route =
            routes.find(
                r =>
                    String(r.route_id) ===
                    String(routeId)
            );


        return route
            ? route.route_name
            : "Route";

    }


    /* =================================================
       DRAW STOPS
    ================================================= */

    function drawStops() {

        stopLayer.clearLayers();


        stops.forEach(stop => {


            if (
                stop.latitude === null ||
                stop.longitude === null
            ) {

                return;

            }


            const stopIcon =
                L.divIcon({

                    className:
                        "admin-stop-wrapper",

                    html: `
                        <div style="
                            width:14px;
                            height:14px;
                            background:#ffc107;
                            border:3px solid #ffffff;
                            border-radius:50%;
                            box-shadow:0 2px 7px rgba(0,0,0,.35);
                        "></div>
                    `,

                    iconSize: [14, 14],

                    iconAnchor: [7, 7]

                });


            const marker =
                L.marker(
                    [
                        Number(stop.latitude),
                        Number(stop.longitude)
                    ],
                    {
                        icon: stopIcon
                    }
                );


            marker.bindPopup(`

                <div>

                    <strong>
                        📍 ${stop.stop_name}
                    </strong>

                    <br>

                    <span>
                        Stop ${stop.stop_order}
                    </span>

                    <br>

                    <small>
                        ${getRouteName(stop.route_id)}
                    </small>

                </div>

            `);


            marker.addTo(stopLayer);


            stopMarkers[stop.id] =
                marker;

        });

    }


    /* =================================================
       DRAW BUSES
    ================================================= */

    function drawBuses() {

        busLayer.clearLayers();


        buses.forEach(bus => {


            if (
                bus.latitude === null ||
                bus.longitude === null
            ) {

                return;

            }


            const lat =
                Number(bus.latitude);

            const lng =
                Number(bus.longitude);


            if (
                !Number.isFinite(lat) ||
                !Number.isFinite(lng)
            ) {

                return;

            }


            const status =
                getBusStatus(bus);


            const marker =
                L.marker(
                    [lat, lng],
                    {
                        icon:
                            createBusIcon(status)
                    }
                );


            marker.bindPopup(
                createBusPopup(bus)
            );


            marker.addTo(busLayer);


            marker.on(
                "click",
                function () {

                    selectBus(bus);

                }
            );


            busMarkers[bus.bus_id] =
                marker;

        });

    }


    /* =================================================
       SELECT BUS
    ================================================= */

    function selectBus(bus) {

        const marker =
            busMarkers[bus.bus_id];


        if (marker) {

            map.flyTo(
                marker.getLatLng(),
                15,
                {
                    duration: 1
                }
            );


            marker.openPopup();

        }


        document
            .querySelectorAll(".fleet-item")
            .forEach(item => {

                item.classList.remove(
                    "selected"
                );

            });


        const item =
            document.querySelector(
                `.fleet-item[data-bus-id="${bus.bus_id}"]`
            );


        if (item) {

            item.classList.add(
                "selected"
            );

        }


        showSelectedBus(bus);

    }


    /* =================================================
       SELECTED BUS PANEL
    ================================================= */

    function showSelectedBus(bus) {

        const card =
            document.getElementById(
                "selectedBusCard"
            );


        if (!card) {

            return;

        }


        document.getElementById(
            "selectedBusNumber"
        ).textContent =
            bus.bus_number || "Bus";


        document.getElementById(
            "selectedDriver"
        ).textContent =
            bus.driver_name ||
            "Driver not assigned";


        document.getElementById(
            "selectedRoute"
        ).textContent =
            bus.route_name || "—";


        document.getElementById(
            "selectedStop"
        ).textContent =
            bus.current_stop || "—";


        const speed =
            parseFloat(
                bus.speed || 0
            ).toFixed(1);


        document.getElementById(
            "selectedSpeed"
        ).textContent =
            `${speed} km/h`;


        document.getElementById(
            "selectedEta"
        ).textContent =
            bus.eta || "—";


        const status =
            getBusStatus(bus);


        let statusText =
            "🔴 Offline";


        if (status === "moving") {

            statusText =
                "🟢 Moving";

        } else if (status === "stopped") {

            statusText =
                "🟡 Stopped";

        }


        document.getElementById(
            "selectedStatus"
        ).textContent =
            statusText;


        document.getElementById(
            "selectedUpdated"
        ).textContent =
            bus.last_updated
                ? `Updated ${bus.last_updated}`
                : "No update";


        card.classList.add("show");

    }


    /* =================================================
       CLOSE SELECTED BUS
    ================================================= */

    const closeSelected =
        document.getElementById(
            "closeSelected"
        );


    if (closeSelected) {

        closeSelected.addEventListener(
            "click",
            function () {


                const selectedCard =
                    document.getElementById(
                        "selectedBusCard"
                    );


                if (selectedCard) {

                    selectedCard.classList.remove(
                        "show"
                    );

                }


                document
                    .querySelectorAll(
                        ".fleet-item"
                    )
                    .forEach(item => {

                        item.classList.remove(
                            "selected"
                        );

                    });

            }
        );

    }


    /* =================================================
       BUS LIST CLICK
    ================================================= */

    document
        .querySelectorAll(".fleet-item")
        .forEach(item => {

            item.addEventListener(
                "click",
                function () {

                    const busId =
                        this.dataset.busId;


                    const bus =
                        buses.find(
                            b =>
                                String(
                                    b.bus_id
                                ) ===
                                String(busId)
                        );


                    if (bus) {

                        selectBus(bus);

                    }

                }
            );

        });


    /* =================================================
       SEARCH
    ================================================= */

    const search =
        document.getElementById(
            "busSearch"
        );


    if (search) {

        search.addEventListener(
            "input",
            function () {

                const value =
                    this.value
                        .toLowerCase()
                        .trim();


                document
                    .querySelectorAll(
                        ".fleet-item"
                    )
                    .forEach(item => {

                        const bus =
                            (
                                item.dataset.busNumber ||
                                ""
                            ).toLowerCase();


                        const driver =
                            (
                                item.dataset.driver ||
                                ""
                            ).toLowerCase();


                        const match =
                            bus.includes(value) ||
                            driver.includes(value);


                        item.style.display =
                            match
                                ? "flex"
                                : "none";

                    });

            }
        );

    }


    /* =================================================
       FILTERS
    ================================================= */

    document
        .querySelectorAll(
            ".filter-btn"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                function () {


                    document
                        .querySelectorAll(
                            ".filter-btn"
                        )
                        .forEach(btn =>
                            btn.classList.remove(
                                "active"
                            )
                        );


                    this.classList.add(
                        "active"
                    );


                    const filter =
                        this.dataset.filter;


                    document
                        .querySelectorAll(
                            ".fleet-item"
                        )
                        .forEach(item => {


                            if (
                                filter === "all"
                            ) {

                                item.style.display =
                                    "flex";

                                return;

                            }


                            item.style.display =
                                item.dataset.status ===
                                filter
                                    ? "flex"
                                    : "none";

                        });

                }
            );

        });


    /* =================================================
       FIT ALL BUSES
    ================================================= */

    const fitFleet =
        document.getElementById(
            "fitFleet"
        );


    if (fitFleet) {

        fitFleet.addEventListener(
            "click",
            function () {

                const points = [];


                buses.forEach(bus => {

                    if (
                        bus.latitude !== null &&
                        bus.longitude !== null
                    ) {

                        const lat =
                            Number(bus.latitude);

                        const lng =
                            Number(bus.longitude);


                        if (
                            Number.isFinite(lat) &&
                            Number.isFinite(lng)
                        ) {

                            points.push([
                                lat,
                                lng
                            ]);

                        }

                    }

                });


                if (points.length) {

                    map.fitBounds(
                        points,
                        {
                            padding: [40, 40]
                        }
                    );

                }

            }
        );

    }


    /* =================================================
       CENTER ACTIVE BUSES
    ================================================= */

    const locateFleet =
        document.getElementById(
            "locateFleet"
        );


    if (locateFleet) {

        locateFleet.addEventListener(
            "click",
            function () {

                const points = [];


                buses.forEach(bus => {

                    if (
                        bus.latitude !== null &&
                        bus.longitude !== null &&
                        bus.trip_status ===
                        "Online"
                    ) {

                        const lat =
                            Number(bus.latitude);

                        const lng =
                            Number(bus.longitude);


                        if (
                            Number.isFinite(lat) &&
                            Number.isFinite(lng)
                        ) {

                            points.push([
                                lat,
                                lng
                            ]);

                        }

                    }

                });


                if (points.length) {

                    map.fitBounds(
                        points,
                        {
                            padding: [50, 50]
                        }
                    );

                }

            }
        );

    }


    /* =================================================
       ROUTE BUTTONS
       
       The road route is loaded asynchronously.
       Therefore, if the admin clicks too early,
       show a loading message instead of saying
       that there are no stops.
    ================================================= */

    document
        .querySelectorAll(
            ".show-route-btn"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                function () {


                    const routeId =
                        this.dataset.route;


                    const line =
                        routeLines[routeId];


                    /* ---------------------------------
                       Route still loading
                    --------------------------------- */

                    if (!line) {

                        alert(
                            "Road route is still loading. Please try again in a moment."
                        );

                        return;

                    }


                    /* ---------------------------------
                       Zoom to complete road route
                    --------------------------------- */

                    map.fitBounds(
                        line.getBounds(),
                        {
                            padding: [50, 50]
                        }
                    );


                    /* ---------------------------------
                       Open route tooltip
                    --------------------------------- */

                    if (
                        typeof line.openTooltip ===
                        "function"
                    ) {

                        line.openTooltip();

                    }

                }
            );

        });


    /* =================================================
       INITIALIZE
    ================================================= */

    /*
       IMPORTANT:
       drawRoutes() is asynchronous because it requests
       the actual road geometry from OSRM.
    */

    drawRoutes();

    drawStops();

    drawBuses();


    /* =================================================
       FIT INITIAL MAP
    ================================================= */

    const initialPoints = [];


    buses.forEach(bus => {

        if (
            bus.latitude !== null &&
            bus.longitude !== null
        ) {

            const lat =
                Number(bus.latitude);

            const lng =
                Number(bus.longitude);


            if (
                Number.isFinite(lat) &&
                Number.isFinite(lng)
            ) {

                initialPoints.push([

                    lat,

                    lng

                ]);

            }

        }

    });


    if (initialPoints.length) {

        map.fitBounds(
            initialPoints,
            {
                padding: [50, 50]
            }
        );

    } else {

        const allStopPoints =
            stops
                .filter(
                    stop =>
                        stop.latitude !== null &&
                        stop.longitude !== null
                )
                .map(
                    stop => [

                        Number(stop.latitude),

                        Number(stop.longitude)

                    ]
                );


        if (allStopPoints.length) {

            map.fitBounds(
                allStopPoints,
                {
                    padding: [50, 50]
                }
            );

        }

    }


    /* =================================================
       LAST SYNC
    ================================================= */

    function updateSyncTime() {

        const element =
            document.getElementById(
                "lastSync"
            );


        if (!element) {

            return;

        }


        const now =
            new Date();


        element.textContent =
            "Updated " +
            now.toLocaleTimeString(
                [],
                {
                    hour: "2-digit",
                    minute: "2-digit"
                }
            );

    }


    updateSyncTime();


    /* =================================================
       REFRESH LIVE DATA
    ================================================= */

    async function refreshFleet() {

        try {


            const response =
                await fetch(
                    "{{ url_for('admin_live_fleet_data') }}",
                    {
                        cache: "no-store"
                    }
                );


            if (!response.ok) {

                throw new Error(
                    "Failed to load fleet data"
                );

            }


            const result =
                await response.json();


            if (
                result.success &&
                Array.isArray(result.buses)
            ) {

                buses =
                    result.buses;


                updateBusMarkers();

                updateStatistics();

                updateSyncTime();

            }


        } catch (error) {

            console.error(
                "Fleet update error:",
                error
            );

        }

    }


    /* =================================================
       UPDATE BUS MARKERS
    ================================================= */

    function updateBusMarkers() {

        busLayer.clearLayers();


        buses.forEach(bus => {


            if (
                bus.latitude === null ||
                bus.longitude === null
            ) {

                return;

            }


            const lat =
                Number(bus.latitude);

            const lng =
                Number(bus.longitude);


            if (
                !Number.isFinite(lat) ||
                !Number.isFinite(lng)
            ) {

                return;

            }


            const status =
                getBusStatus(bus);


            const marker =
                L.marker(
                    [lat, lng],
                    {
                        icon:
                            createBusIcon(status)
                    }
                );


            marker.bindPopup(
                createBusPopup(bus)
            );


            marker.on(
                "click",
                function () {

                    selectBus(bus);

                }
            );


            marker.addTo(busLayer);


            busMarkers[bus.bus_id] =
                marker;

        });

    }


    /* =================================================
       UPDATE STATISTICS
    ================================================= */

    function updateStatistics() {

        let online = 0;

        let moving = 0;

        let stopped = 0;

        let offline = 0;


        buses.forEach(bus => {

            const status =
                getBusStatus(bus);


            if (status === "moving") {

                online++;

                moving++;

            } else if (status === "stopped") {

                online++;

                stopped++;

            } else {

                offline++;

            }

        });


        const totalBuses =
            document.getElementById(
                "totalBuses"
            );

        if (totalBuses) {

            totalBuses.textContent =
                buses.length;

        }


        const onlineBuses =
            document.getElementById(
                "onlineBuses"
            );

        if (onlineBuses) {

            onlineBuses.textContent =
                online;

        }


        const movingBuses =
            document.getElementById(
                "movingBuses"
            );

        if (movingBuses) {

            movingBuses.textContent =
                moving;

        }


        const stoppedBuses =
            document.getElementById(
                "stoppedBuses"
            );

        if (stoppedBuses) {

            stoppedBuses.textContent =
                stopped;

        }


        const offlineBuses =
            document.getElementById(
                "offlineBuses"
            );

        if (offlineBuses) {

            offlineBuses.textContent =
                offline;

        }


        const busCountBadge =
            document.getElementById(
                "busCountBadge"
            );

        if (busCountBadge) {

            busCountBadge.textContent =
                buses.length;

        }

    }


    /* =================================================
       AUTO UPDATE
       Every 10 seconds
    ================================================= */

    setInterval(
        refreshFleet,
        10000
    );

});