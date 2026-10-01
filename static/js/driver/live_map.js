/*==========================================================
                DRIVER LIVE MAP
==========================================================*/

document.addEventListener("DOMContentLoaded", () => {

    const mapContainer = document.getElementById("driverMap");

    if (!mapContainer) return;

    // Default Location
    const defaultLat = 21.4973084;
    const defaultLng = 73.0094467;

    // Create Map
    const map = L.map("driverMap").setView(
        [defaultLat, defaultLng],
        16
    );

    // OpenStreetMap
    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom:19,
            attribution:"&copy; OpenStreetMap Contributors"
        }
    ).addTo(map);

    // Bus Icon
    const busIcon = L.icon({

        iconUrl:"/static/images/bus-marker.png",

        iconSize:[48,48],

        iconAnchor:[24,24],

        popupAnchor:[0,-20]

    });

    // Marker
    let busMarker = L.marker(

        [defaultLat, defaultLng],

        {

            icon:busIcon

        }

    ).addTo(map);

    busMarker.bindPopup("<b>College Bus</b>");



    /*====================================
            LOAD LOCATION
    ====================================*/

    function loadBusLocation(){

        fetch("/driver/live_location")

        .then(response=>response.json())

        .then(data=>{

            if(!data.success){

                return;

            }

            const lat=data.latitude;
            const lng=data.longitude;

            // Move Marker
            busMarker.setLatLng([lat,lng]);

            // Center Map
            map.panTo([lat,lng]);

        })

        .catch(error=>{

            console.log(error);

        });

    }

    // First Load
    loadBusLocation();

    // Refresh Every 5 Seconds
    setInterval(loadBusLocation,5000);

});