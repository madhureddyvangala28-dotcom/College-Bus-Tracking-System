/*==========================================================*
 * DRIVER LIVE TRACKING
 *==========================================================*/

document.addEventListener("DOMContentLoaded", function () {

    /*======================================================*
     * MAP INITIALIZATION
     *======================================================*/

    const map = L.map("map").setView(
        [21.4850, 73.2100],
        13
    );


    /*======================================================*
     * MAP TILE
     *======================================================*/

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            attribution: "&copy; OpenStreetMap Contributors",
            maxZoom: 19
        }
    ).addTo(map);


    /*======================================================*
     * BUS ICON
     *======================================================*/

    const busIcon = L.icon({

        iconUrl: "/static/images/bus-marker.png",

        iconSize: [45, 45],

        iconAnchor: [22, 45],

        popupAnchor: [0, -40]

    });


    /*======================================================*
     * STOP ICON
     *======================================================*/

    const stopIcon = L.divIcon({

        className: "custom-stop-marker",

        html: `
            <div style="
                width: 28px;
                height: 28px;
                border-radius: 50%;
                background: #16a34a;
                border: 4px solid white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.35);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 12px;
                font-weight: bold;
            ">
                📍
            </div>
        `,

        iconSize: [28, 28],

        iconAnchor: [14, 28],

        popupAnchor: [0, -28]

    });


    /*======================================================*
     * VARIABLES
     *======================================================*/

    let driverMarker = null;

    let watchId = null;

    let animationFrame = null;

    let previousLocation = null;

    let previousTime = null;

    let previousSpeed = 0;

    let routeLine = null;

    let stopMarkers = [];


    /*======================================================*
     * GET ROUTE STOPS FROM FLASK
     *======================================================*/

    const routeStops = Array.isArray(window.driverRouteStops)
        ? window.driverRouteStops
        : [];


    console.log("======================================");

    console.log("ROUTE STOPS FROM FLASK:");

    console.log(routeStops);

    console.log("TOTAL STOPS:", routeStops.length);

    console.log(
        "CURRENT STOP:",
        window.driverCurrentStop
    );

    console.log(
        "CURRENT STOP ORDER:",
        window.driverCurrentStopOrder
    );

    console.log("======================================");


    /*======================================================*
     * DRAW ACTUAL ROAD ROUTE USING OSRM
     *======================================================*/

    async function drawRoadRoute(routeCoordinates) {

        if (!routeCoordinates || routeCoordinates.length < 2) {

            console.warn(
                "⚠ Not enough coordinates to create road route."
            );

            return;

        }


        /*--------------------------------------------------*
         * CREATE OSRM COORDINATE STRING
         *
         * OSRM format:
         *
         * longitude,latitude;
         * longitude,latitude;
         * longitude,latitude
         *--------------------------------------------------*/

        const osrmCoordinates = routeCoordinates
            .map(function (coordinate) {

                const latitude = coordinate[0];

                const longitude = coordinate[1];

                return (
                    longitude +
                    "," +
                    latitude
                );

            })
            .join(";");


        /*--------------------------------------------------*
         * OSRM ROUTING URL
         *--------------------------------------------------*/

        const osrmUrl =
            "https://router.project-osrm.org/route/v1/driving/" +
            osrmCoordinates +
            "?overview=full&geometries=geojson&steps=false";


        console.log(
            "🚗 Requesting actual road route from OSRM..."
        );

        console.log(
            "OSRM URL:",
            osrmUrl
        );


        try {

            /*------------------------------------------------*
             * REQUEST ROAD ROUTE
             *------------------------------------------------*/

            const response = await fetch(osrmUrl);


            if (!response.ok) {

                throw new Error(
                    "OSRM HTTP Error: " +
                    response.status
                );

            }


            const data = await response.json();


            console.log(
                "OSRM RESPONSE:",
                data
            );


            /*------------------------------------------------*
             * CHECK ROUTE RESPONSE
             *------------------------------------------------*/

            if (
                data.code !== "Ok" ||
                !data.routes ||
                data.routes.length === 0
            ) {

                console.error(
                    "❌ OSRM could not find a road route.",
                    data
                );

                return;

            }


            /*------------------------------------------------*
             * GET FIRST ROUTE
             *------------------------------------------------*/

            const roadRoute = data.routes[0];


            /*------------------------------------------------*
             * REMOVE OLD ROUTE
             *------------------------------------------------*/

            if (routeLine) {

                map.removeLayer(routeLine);

                routeLine = null;

            }


            /*------------------------------------------------*
             * GET ROAD GEOMETRY
             *
             * OSRM returns:
             *
             * [longitude, latitude]
             *
             * Leaflet requires:
             *
             * [latitude, longitude]
             *------------------------------------------------*/

            if (
                !roadRoute.geometry ||
                !roadRoute.geometry.coordinates
            ) {

                console.error(
                    "❌ No road geometry received from OSRM."
                );

                return;

            }


            const roadCoordinates =
                roadRoute.geometry.coordinates.map(
                    function (point) {

                        return [
                            point[1],
                            point[0]
                        ];

                    }
                );


            /*------------------------------------------------*
             * DRAW ACTUAL ROAD ROUTE
             *------------------------------------------------*/

            routeLine = L.polyline(

                roadCoordinates,

                {

                    color: "#2563eb",

                    weight: 6,

                    opacity: 0.9,

                    lineJoin: "round",

                    lineCap: "round"

                }

            ).addTo(map);


            /*------------------------------------------------*
             * KEEP ROUTE BEHIND MARKERS
             *------------------------------------------------*/

            routeLine.bringToBack();


            /*------------------------------------------------*
             * ROUTE DISTANCE
             *------------------------------------------------*/

            const distanceKm =
                roadRoute.distance / 1000;


            /*------------------------------------------------*
             * ROUTE DURATION
             *------------------------------------------------*/

            const durationMinutes =
                Math.round(
                    roadRoute.duration / 60
                );


            console.log(
                "======================================"
            );

            console.log(
                "✅ ACTUAL ROAD ROUTE CREATED"
            );

            console.log(
                "Road Distance:",
                distanceKm.toFixed(2),
                "km"
            );

            console.log(
                "Road Duration:",
                durationMinutes,
                "minutes"
            );

            console.log(
                "Road Points:",
                roadCoordinates.length
            );

            console.log(
                "======================================"
            );


            /*------------------------------------------------*
             * UPDATE ROUTE INFORMATION CARD
             *------------------------------------------------*/

            const routeDistance =
                document.getElementById(
                    "routeDistance"
                );


            const routeDuration =
                document.getElementById(
                    "routeDuration"
                );


            if (routeDistance) {

                routeDistance.textContent =
                    distanceKm.toFixed(2) +
                    " km";

            }


            if (routeDuration) {

                const hours =
                    Math.floor(
                        durationMinutes / 60
                    );

                const minutes =
                    durationMinutes % 60;


                if (hours > 0) {

                    routeDuration.textContent =
                        hours +
                        " hr " +
                        minutes +
                        " min";

                }

                else {

                    routeDuration.textContent =
                        minutes +
                        " min";

                }

            }


        }

        catch (error) {

            console.error(
                "❌ Road route error:",
                error
            );

        }

    }


    /*======================================================*
     * DISPLAY ROUTE STOPS
     *======================================================*/

    function displayRouteStops() {

        if (
            !routeStops ||
            routeStops.length === 0
        ) {

            console.warn(
                "⚠ No route stops received from Flask."
            );

            return;

        }


        /*--------------------------------------------------*
         * CLEAR OLD STOP MARKERS
         *--------------------------------------------------*/

        stopMarkers.forEach(
            function (marker) {

                map.removeLayer(marker);

            }
        );


        stopMarkers = [];


        /*--------------------------------------------------*
         * SORT STOPS BY STOP ORDER
         *--------------------------------------------------*/

        const sortedStops = [...routeStops].sort(
            function (a, b) {

                return (
                    Number(a.stop_order || 0) -
                    Number(b.stop_order || 0)
                );

            }
        );


        console.log(
            "SORTED ROUTE STOPS:",
            sortedStops
        );


        /*--------------------------------------------------*
         * STORE VALID STOP COORDINATES
         *--------------------------------------------------*/

        const routeCoordinates = [];


        /*--------------------------------------------------*
         * CREATE STOP MARKERS
         *--------------------------------------------------*/

        sortedStops.forEach(
            function (stop, index) {

                /*--------------------------------------------*
                 * CONVERT COORDINATES TO NUMBERS
                 *--------------------------------------------*/

                const latitude =
                    parseFloat(stop.latitude);

                const longitude =
                    parseFloat(stop.longitude);


                /*--------------------------------------------*
                 * CHECK COORDINATES
                 *--------------------------------------------*/

                if (
                    Number.isNaN(latitude) ||
                    Number.isNaN(longitude)
                ) {

                    console.warn(
                        "⚠ Stop has invalid coordinates:",
                        stop
                    );

                    return;

                }


                /*--------------------------------------------*
                 * SAVE COORDINATES
                 *--------------------------------------------*/

                routeCoordinates.push([

                    latitude,

                    longitude

                ]);


                /*--------------------------------------------*
                 * CREATE STOP MARKER
                 *--------------------------------------------*/

                const marker = L.marker(

                    [
                        latitude,
                        longitude
                    ],

                    {
                        icon: stopIcon
                    }

                ).addTo(map);


                /*--------------------------------------------*
                 * POPUP
                 *--------------------------------------------*/

                marker.bindPopup(`

                    <div style="
                        min-width:180px;
                        font-family:Arial,sans-serif;
                    ">

                        <strong>
                            📍 Stop ${index + 1}
                        </strong>

                        <br><br>

                        <b>
                            ${stop.stop_name || "Bus Stop"}
                        </b>

                        <br>

                        <small>
                            Stop Order:
                            ${stop.stop_order}
                        </small>

                    </div>

                `);


                /*--------------------------------------------*
                 * SAVE MARKER
                 *--------------------------------------------*/

                stopMarkers.push(marker);

            }
        );


        /*==================================================*
         * CHECK ROUTE COORDINATES
         *==================================================*/

        console.log(
            "VALID STOP COORDINATES:",
            routeCoordinates
        );


        /*==================================================*
         * DRAW ACTUAL ROAD ROUTE
         *==================================================*/

        if (routeCoordinates.length >= 2) {

            drawRoadRoute(
                routeCoordinates
            );

        }

        else {

            console.warn(
                "⚠ At least 2 mapped stops are required."
            );

        }


        /*==================================================*
         * FIT MAP TO STOPS
         *==================================================*/

        if (routeCoordinates.length > 0) {

            const routeBounds =
                L.latLngBounds(
                    routeCoordinates
                );


            map.fitBounds(

                routeBounds,

                {
                    padding: [50, 50]
                }

            );

        }


        /*==================================================*
         * UPDATE TOTAL STOPS
         *==================================================*/

        const routeTotalStops =
            document.getElementById(
                "routeTotalStops"
            );


        if (routeTotalStops) {

            routeTotalStops.textContent =
                sortedStops.length;

        }


        /*==================================================*
         * UPDATE MAPPED STOPS
         *==================================================*/

        const routeMappedStops =
            document.getElementById(
                "routeMappedStops"
            );


        if (routeMappedStops) {

            routeMappedStops.textContent =
                routeCoordinates.length;

        }


        /*==================================================*
         * UPDATE COVERAGE
         *==================================================*/

        const routeCoverage =
            document.getElementById(
                "routeCoverage"
            );


        const routeCoverageBar =
            document.getElementById(
                "routeCoverageBar"
            );


        const coverage =
            sortedStops.length > 0
                ? Math.round(
                    (
                        routeCoordinates.length /
                        sortedStops.length
                    ) * 100
                )
                : 0;


        if (routeCoverage) {

            routeCoverage.textContent =
                coverage + "%";

        }


        if (routeCoverageBar) {

            routeCoverageBar.style.width =
                coverage + "%";

        }


        /*==================================================*
         * UPDATE MAPPING MESSAGE
         *==================================================*/

        const routeMappingMessage =
            document.getElementById(
                "routeMappingMessage"
            );


        if (routeMappingMessage) {

            if (coverage === 100) {

                routeMappingMessage.textContent =
                    "All bus stops are mapped.";

            }

            else {

                routeMappingMessage.textContent =
                    routeCoordinates.length +
                    " of " +
                    sortedStops.length +
                    " stops have coordinates.";

            }

        }


        console.log(
            "======================================"
        );

        console.log(
            "✅ Route stops displayed:",
            routeCoordinates.length
        );

        console.log(
            "======================================"
        );

    }


    /*======================================================*
     * SMOOTH BUS MARKER ANIMATION
     *======================================================*/

    function animateMarker(
        start,
        end,
        duration = 1000
    ) {

        if (!driverMarker) {

            return;

        }


        const startTime =
            performance.now();


        function animate(currentTime) {

            const elapsed =
                currentTime -
                startTime;


            const progress =
                Math.min(
                    elapsed / duration,
                    1
                );


            const lat =
                start[0] +
                (
                    end[0] -
                    start[0]
                ) *
                progress;


            const lng =
                start[1] +
                (
                    end[1] -
                    start[1]
                ) *
                progress;


            driverMarker.setLatLng([

                lat,

                lng

            ]);


            if (progress < 1) {

                animationFrame =
                    requestAnimationFrame(
                        animate
                    );

            }

        }


        animationFrame =
            requestAnimationFrame(
                animate
            );

    }


    /*======================================================*
     * HAVERSINE DISTANCE
     *======================================================*/

    function calculateDistance(
        lat1,
        lon1,
        lat2,
        lon2
    ) {

        const R = 6371000;


        const dLat =
            (
                lat2 -
                lat1
            ) *
            Math.PI /
            180;


        const dLon =
            (
                lon2 -
                lon1
            ) *
            Math.PI /
            180;


        const a =

            Math.sin(
                dLat / 2
            ) *
            Math.sin(
                dLat / 2
            )

            +

            Math.cos(
                lat1 *
                Math.PI /
                180
            )

            *

            Math.cos(
                lat2 *
                Math.PI /
                180
            )

            *

            Math.sin(
                dLon / 2
            ) *
            Math.sin(
                dLon / 2
            );


        const c =
            2 *
            Math.atan2(

                Math.sqrt(a),

                Math.sqrt(
                    1 - a
                )

            );


        return R * c;

    }


    /*======================================================*
     * CALCULATE SPEED
     *======================================================*/

    function calculateSpeed(
        latitude,
        longitude
    ) {

        const now =
            Date.now();


        if (!previousLocation) {

            previousLocation = [

                latitude,

                longitude

            ];


            previousTime =
                now;


            return 0;

        }


        const distance =
            calculateDistance(

                previousLocation[0],

                previousLocation[1],

                latitude,

                longitude

            );


        /*--------------------------------------------------*
         * IGNORE MOVEMENT LESS THAN 5 METERS
         *--------------------------------------------------*/

        if (distance < 5) {

            previousLocation = [

                latitude,

                longitude

            ];


            previousTime =
                now;


            return previousSpeed.toFixed(1);

        }


        const timeSeconds =
            (
                now -
                previousTime
            ) /
            1000;


        /*--------------------------------------------------*
         * IGNORE VERY FAST UPDATES
         *--------------------------------------------------*/

        if (timeSeconds < 1) {

            return previousSpeed.toFixed(1);

        }


        previousLocation = [

            latitude,

            longitude

        ];


        previousTime =
            now;


        if (timeSeconds <= 0) {

            return 0;

        }


        let speed =
            (
                distance /
                timeSeconds
            ) *
            3.6;


        /*--------------------------------------------------*
         * MAXIMUM SPEED
         *--------------------------------------------------*/

        if (speed > 90) {

            speed = 90;

        }


        /*--------------------------------------------------*
         * IGNORE VERY SLOW MOVEMENT
         *--------------------------------------------------*/

        if (speed < 1) {

            speed = 0;

        }


        /*--------------------------------------------------*
         * SMOOTH SPEED
         *--------------------------------------------------*/

        speed =
            (
                previousSpeed *
                0.7
            )
            +
            (
                speed *
                0.3
            );


        previousSpeed =
            speed;


        return speed.toFixed(1);

    }


    /*======================================================*
     * UPDATE DRIVER LOCATION
     *======================================================*/

    function updateDriverLocation(position) {

        const latitude =
            position.coords.latitude;


        const longitude =
            position.coords.longitude;


        /*==================================================*
         * GPS ACCURACY
         *==================================================*/

        if (
            position.coords.accuracy > 100
        ) {

            console.log(
                "Poor GPS Accuracy:",
                position.coords.accuracy
            );

        }


        /*==================================================*
         * SPEED
         *==================================================*/

        const speed =
            calculateSpeed(

                latitude,

                longitude

            );


        /*==================================================*
         * UPDATE DETAILS
         *==================================================*/

        const latitudeElement =
            document.getElementById(
                "latitude"
            );


        const longitudeElement =
            document.getElementById(
                "longitude"
            );


        const speedElement =
            document.getElementById(
                "speed"
            );


        const lastUpdateElement =
            document.getElementById(
                "lastUpdate"
            );


        if (latitudeElement) {

            latitudeElement.textContent =
                latitude.toFixed(6);

        }


        if (longitudeElement) {

            longitudeElement.textContent =
                longitude.toFixed(6);

        }


        if (speedElement) {

            speedElement.textContent =
                speed +
                " km/h";

        }


        if (lastUpdateElement) {

            lastUpdateElement.textContent =
                new Date().toLocaleTimeString();

        }


        /*==================================================*
         * CURRENT LOCATION
         *==================================================*/

        const currentLocation = [

            latitude,

            longitude

        ];


        /*==================================================*
         * FIRST LOCATION
         *==================================================*/

        if (!driverMarker) {

            driverMarker =
                L.marker(

                    currentLocation,

                    {
                        icon: busIcon
                    }

                )

                .addTo(map)

                .bindPopup(
                    "🚌 College Bus"
                );

        }


        /*==================================================*
         * MOVE BUS
         *==================================================*/

        else {

            cancelAnimationFrame(
                animationFrame
            );


            const oldPosition =
                driverMarker.getLatLng();


            animateMarker(

                [

                    oldPosition.lat,

                    oldPosition.lng

                ],

                currentLocation,

                1000

            );

        }


        /*==================================================*
         * MAP FOLLOW BUS
         *==================================================*/

        map.panTo(

            currentLocation,

            {

                animate: true,

                duration: 1

            }

        );


        /*==================================================*
         * SEND LOCATION TO SERVER
         *==================================================*/

        fetch(

            "/driver/update_location",

            {

                method: "POST",

                headers: {

                    "Content-Type":
                        "application/json"

                },

                body: JSON.stringify({

                    latitude:
                        latitude,

                    longitude:
                        longitude,

                    speed:
                        parseFloat(speed)

                })

            }

        )

        .then(
            function (response) {

                return response.json();

            }
        )

        .then(
            function (data) {

                if (data.success) {

                    console.log(
                        "✅ Location Updated"
                    );

                }

                else {

                    console.log(
                        data.message
                    );

                }

            }
        )

        .catch(
            function (error) {

                console.error(
                    "Location Update Error:",
                    error
                );

            }
        );

    }


    /*======================================================*
     * GPS ERROR
     *======================================================*/

    function locationError(error) {

        console.error(
            "GPS Error:",
            error
        );


        if (error.code === 1) {

            alert(
                "GPS permission denied. Please allow location access."
            );

        }

        else if (error.code === 2) {

            alert(
                "GPS position unavailable."
            );

        }

        else if (error.code === 3) {

            alert(
                "GPS request timed out."
            );

        }

        else {

            alert(
                "Unable to access GPS."
            );

        }

    }


    /*======================================================*
     * START TRACKING
     *======================================================*/

    function startTracking() {

        if (!navigator.geolocation) {

            alert(
                "Geolocation is not supported."
            );

            return;

        }


        watchId =
            navigator.geolocation.watchPosition(

                updateDriverLocation,

                locationError,

                {

                    enableHighAccuracy: true,

                    maximumAge: 2000,

                    timeout: 15000

                }

            );

    }


    /*======================================================*
     * START ROUTE DISPLAY
     *======================================================*/

    displayRouteStops();


    /*======================================================*
     * START GPS
     *======================================================*/

    startTracking();

});