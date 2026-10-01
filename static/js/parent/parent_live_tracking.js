document.addEventListener("DOMContentLoaded", function () {

    /* ==========================================
       GET MAP ELEMENT
    ========================================== */

    const mapElement = document.getElementById("busMap");

    if (!mapElement) {
        console.error("ERROR: #busMap element was not found.");
        return;
    }


    /* ==========================================
       GET DATA FROM HTML
    ========================================== */

    const busId = mapElement.dataset.busId;

    const initialLatitude = parseFloat(
        mapElement.dataset.latitude
    );

    const initialLongitude = parseFloat(
        mapElement.dataset.longitude
    );

    const initialStop =
        mapElement.dataset.currentStop ||
        "Current Bus Location";


    /* ==========================================
       DEFAULT LOCATION
       HYDERABAD
    ========================================== */

    const DEFAULT_LATITUDE = 17.3850;
    const DEFAULT_LONGITUDE = 78.4867;


    /* ==========================================
       MAP START LOCATION
    ========================================== */

    const startLatitude =
        Number.isFinite(initialLatitude)
            ? initialLatitude
            : DEFAULT_LATITUDE;

    const startLongitude =
        Number.isFinite(initialLongitude)
            ? initialLongitude
            : DEFAULT_LONGITUDE;


    /* ==========================================
       CREATE LEAFLET MAP
    ========================================== */

    const map = L.map("busMap", {
        zoomControl: true
    }).setView(
        [startLatitude, startLongitude],
        13
    );


    /* ==========================================
       OPENSTREETMAP TILE LAYER
    ========================================== */

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,
            attribution:
                "&copy; OpenStreetMap contributors"
        }
    ).addTo(map);


    /* ==========================================
       BUS ICON
    ========================================== */

    const busIcon = L.divIcon({

        className: "custom-bus-marker",

        html: `
            <div class="bus-icon-wrapper">
                <img
                    src="/static/images/bus-marker.png"
                    alt="College Bus"
                >
            </div>
        `,

        iconSize: [70, 70],

        iconAnchor: [35, 35],

        popupAnchor: [0, -35]

    });


    /* ==========================================
       BUS STOP ICON
    ========================================== */

    const stopIcon = L.divIcon({

        className: "custom-stop-marker",

        html: `
            <div class="stop-marker-icon">
                <i class="fa-solid fa-location-dot"></i>
            </div>
        `,

        iconSize: [34, 42],

        iconAnchor: [17, 42],

        popupAnchor: [0, -40]

    });


    /* ==========================================
       CURRENT LOCATION ICON
    ========================================== */

    const currentLocationIcon = L.divIcon({

        className: "custom-current-location",

        html: `
            <div class="current-location-marker">
                <i class="fa-solid fa-location-crosshairs"></i>
            </div>
        `,

        iconSize: [42, 42],

        iconAnchor: [21, 21],

        popupAnchor: [0, -25]

    });


    /* ==========================================
       READ ROUTE STOPS FROM HTML
    ========================================== */

    let routeStops = [];

    const stopsDataElement =
        document.getElementById("routeStopsData");


    if (stopsDataElement) {

        try {

            routeStops = JSON.parse(
                stopsDataElement.textContent
            );

        }
        catch (error) {

            console.error(
                "Could not read route stops:",
                error
            );

            routeStops = [];

        }

    }


    /* ==========================================
       VALIDATE ROUTE STOPS
    ========================================== */

    routeStops = routeStops.filter(function (stop) {

        const lat = parseFloat(stop.latitude);
        const lng = parseFloat(stop.longitude);

        return (
            Number.isFinite(lat) &&
            Number.isFinite(lng)
        );

    });


    console.log("BUS ID:", busId);
    console.log("ROUTE STOPS:", routeStops);


    /* ==========================================
       MAP LAYERS
    ========================================== */

    const stopsLayer = L.layerGroup().addTo(map);

    let routeLayer = null;

    let busMarker = null;


    /* ==========================================
       ADD ALL BUS STOPS
    ========================================== */

    function addStopMarkers() {

        stopsLayer.clearLayers();


        routeStops.forEach(function (stop, index) {

            const latitude =
                parseFloat(stop.latitude);

            const longitude =
                parseFloat(stop.longitude);


            const stopNumber =
                stop.stop_order ||
                index + 1;


            const stopName =
                stop.stop_name ||
                `Stop ${stopNumber}`;


            const marker = L.marker(
                [latitude, longitude],
                {
                    icon: stopIcon
                }
            ).addTo(stopsLayer);


            marker.bindPopup(`
                <div class="stop-popup">

                    <strong>
                        Stop ${stopNumber}
                    </strong>

                    <br>

                    ${stopName}

                </div>
            `);


            marker.bindTooltip(
                `${stopNumber}. ${stopName}`,
                {
                    direction: "top",
                    offset: [0, -35]
                }
            );

        });

    }


    /* ==========================================
       DRAW ROAD-FOLLOWING ROUTE
       USING OSRM ROUTING SERVICE
    ========================================== */

    async function drawRoadRoute() {

        if (routeStops.length < 2) {

            console.warn(
                "At least 2 stops are required to draw a route."
            );

            return;

        }


        try {

            /*
             OSRM FORMAT:

             longitude,latitude;
             longitude,latitude
            */

            const coordinates = routeStops
                .map(function (stop) {

                    return (
                        `${parseFloat(stop.longitude)},` +
                        `${parseFloat(stop.latitude)}`
                    );

                })
                .join(";");


            const routeUrl =
                "https://router.project-osrm.org/route/v1/driving/" +
                coordinates +
                "?overview=full" +
                "&geometries=geojson";


            console.log(
                "Loading road route..."
            );


            const response =
                await fetch(routeUrl);


            if (!response.ok) {

                throw new Error(
                    "Unable to get road route."
                );

            }


            const data =
                await response.json();


            if (
                data.code !== "Ok" ||
                !data.routes ||
                data.routes.length === 0
            ) {

                throw new Error(
                    "Route data is not available."
                );

            }


            const geometry =
                data.routes[0].geometry;


            if (routeLayer) {

                map.removeLayer(
                    routeLayer
                );

            }


            routeLayer = L.geoJSON(
                geometry,
                {

                    style: {

                        color: "#f59e0b",

                        weight: 6,

                        opacity: 0.9,

                        lineJoin: "round",

                        lineCap: "round"

                    }

                }
            ).addTo(map);


            console.log(
                "Road-following route loaded successfully."
            );

        }
        catch (error) {

            console.error(
                "Road route error:",
                error
            );


            /*
             FALLBACK:
             If OSRM is unavailable,
             draw a line connecting stops.
            */

            const fallbackCoordinates =
                routeStops.map(function (stop) {

                    return [
                        parseFloat(stop.latitude),
                        parseFloat(stop.longitude)
                    ];

                });


            if (routeLayer) {

                map.removeLayer(
                    routeLayer
                );

            }


            routeLayer = L.polyline(
                fallbackCoordinates,
                {

                    color: "#f59e0b",

                    weight: 5,

                    opacity: 0.8,

                    dashArray: "10, 8"

                }
            ).addTo(map);

        }

    }


    /* ==========================================
       CREATE OR UPDATE BUS MARKER
    ========================================== */

    function updateBusMarker(
        latitude,
        longitude,
        currentStop,
        speed,
        status,
        lastUpdated,
        eta
    ) {

        if (
            !Number.isFinite(latitude) ||
            !Number.isFinite(longitude)
        ) {

            console.warn(
                "Invalid live GPS location."
            );

            return;

        }


        const position = [
            latitude,
            longitude
        ];


        if (!busMarker) {

            busMarker = L.marker(
                position,
                {
                    icon: busIcon,
                    zIndexOffset: 1000
                }
            ).addTo(map);

        }
        else {

            busMarker.setLatLng(
                position
            );

        }


        busMarker.bindPopup(`

            <div class="bus-popup">

                <strong>
                    <i class="fa-solid fa-bus"></i>
                    College Bus
                </strong>

                <hr>

                <b>Current Location:</b>
                ${currentStop || "Location Available"}

                <br>

                <b>Speed:</b>
                ${speed || 0} km/h

                <br>

                <b>Status:</b>
                ${status || "Live"}

                <br>

                <b>Updated:</b>
                ${lastUpdated || "Now"}

                <br>

                <b>ETA:</b>
                ${eta || "Not Available"}

            </div>

        `);


        /*
         Update optional information in page
        */

        updatePageInformation(
            currentStop,
            speed,
            status,
            lastUpdated,
            eta
        );

    }


    /* ==========================================
       UPDATE INFORMATION ON PAGE
    ========================================== */

    function updatePageInformation(
        currentStop,
        speed,
        status,
        lastUpdated,
        eta
    ) {

        const currentLocationElement =
            document.getElementById(
                "currentLocation"
            );

        const busSpeedElement =
            document.getElementById(
                "busSpeed"
            );

        const busStatusElement =
            document.getElementById(
                "busStatus"
            );

        const updatedTimeElement =
            document.getElementById(
                "lastUpdated"
            );

        const etaElement =
            document.getElementById(
                "estimatedArrival"
            );


        if (currentLocationElement) {

            currentLocationElement.textContent =
                currentStop ||
                "Location Not Available";

        }


        if (busSpeedElement) {

            busSpeedElement.textContent =
                `${speed || 0} km/h`;

        }


        if (busStatusElement) {

            busStatusElement.textContent =
                status ||
                "Live";

        }


        if (updatedTimeElement) {

            updatedTimeElement.textContent =
                lastUpdated ||
                "No Data";

        }


        if (etaElement) {

            etaElement.textContent =
                eta ||
                "Not Available";

        }

    }


    /* ==========================================
       GET INITIAL BUS DATA
    ========================================== */

    if (
        Number.isFinite(initialLatitude) &&
        Number.isFinite(initialLongitude)
    ) {

        updateBusMarker(

            initialLatitude,

            initialLongitude,

            initialStop,

            mapElement.dataset.speed || 0,

            mapElement.dataset.status || "Live",

            mapElement.dataset.lastUpdated || "Now",

            mapElement.dataset.eta || "Not Available"

        );

    }


    /* ==========================================
       GET LIVE LOCATION FROM FLASK API
    ========================================== */

    async function getLiveBusLocation() {

        if (!busId) {

            console.warn(
                "Bus ID is not available."
            );

            return;

        }


        try {

            const response =
                await fetch(
                    `/parent/live_location/${busId}`
                );


            if (!response.ok) {

                throw new Error(
                    "Live location API request failed."
                );

            }


            const data =
                await response.json();


            console.log(
                "LIVE LOCATION DATA:",
                data
            );


            if (!data.success) {

                console.warn(
                    data.message ||
                    "Live location unavailable."
                );

                return;

            }


            const latitude =
                parseFloat(data.latitude);

            const longitude =
                parseFloat(data.longitude);


            if (
                !Number.isFinite(latitude) ||
                !Number.isFinite(longitude)
            ) {

                console.warn(
                    "GPS coordinates are empty."
                );

                return;

            }


            let status =
                data.trip_status;


            if (!status || status === "") {

                if (parseFloat(data.speed) > 0) {

                    status = "Moving";

                }
                else {

                    status = "Stopped";

                }

            }


            updateBusMarker(

                latitude,

                longitude,

                data.current_stop,

                data.speed,

                status,

                data.last_updated,

                data.eta

            );


            /*
             Move map to latest bus location
             only if this is the first location
            */

            if (!map._liveLocationLoaded) {

                map.setView(
                    [latitude, longitude],
                    14
                );

                map._liveLocationLoaded = true;

            }

        }
        catch (error) {

            console.error(
                "Live location error:",
                error
            );

        }

    }


    /* ==========================================
       FIT MAP TO ROUTE + BUS
    ========================================== */

    function fitMapToData() {

        const points = [];


        routeStops.forEach(function (stop) {

            points.push([
                parseFloat(stop.latitude),
                parseFloat(stop.longitude)
            ]);

        });


        if (
            Number.isFinite(initialLatitude) &&
            Number.isFinite(initialLongitude)
        ) {

            points.push([
                initialLatitude,
                initialLongitude
            ]);

        }


        if (points.length > 0) {

            const bounds =
                L.latLngBounds(points);


            map.fitBounds(
                bounds,
                {
                    padding: [60, 60],
                    maxZoom: 15
                }
            );

        }

    }


    /* ==========================================
       INITIALIZE MAP
    ========================================== */

    addStopMarkers();

    drawRoadRoute();

    fitMapToData();

    getLiveBusLocation();


    /* ==========================================
       AUTO REFRESH LIVE LOCATION
       EVERY 10 SECONDS
    ========================================== */

    setInterval(
        getLiveBusLocation,
        10000
    );


    /* ==========================================
       FIX MAP SIZE
    ========================================== */

    setTimeout(function () {

        map.invalidateSize();

    }, 500);


    window.addEventListener(
        "resize",
        function () {

            map.invalidateSize();

        }
    );


});