const mapDiv=document.getElementById("liveMap");

let latitude=parseFloat(mapDiv.dataset.lat);
let longitude=parseFloat(mapDiv.dataset.lng);

const map=L.map("liveMap").setView([latitude,longitude],15);

L.tileLayer(
'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
{
maxZoom:19
}
).addTo(map);


// ============================
// Bus Icon
// ============================

const busIcon=L.icon({

iconUrl:"/static/images/map/bus-marker-red.png",

iconSize:[60,60],

iconAnchor:[30,60],

popupAnchor:[0,-50]

});


// ============================
// Marker
// ============================

let marker=L.marker(
[latitude,longitude],
{
icon:busIcon
}
).addTo(map);


// ============================
// Popup
// ============================

function updatePopup(data){

marker.bindPopup(

`<b>${data.bus_number}</b>

<br>

👨 Driver : ${data.driver_name}

<br>

📍 Stop : ${data.current_stop}

<br>

🚍 Speed : ${data.speed} km/h

<br>

⏰ ETA : ${data.eta}`

);

}


// First Popup

updatePopup({

bus_number:mapDiv.dataset.bus,

driver_name:mapDiv.dataset.driver,

current_stop:mapDiv.dataset.stop,

speed:mapDiv.dataset.speed,

eta:mapDiv.dataset.eta

});


// ============================
// Live Update
// ============================

function loadLiveLocation(){

fetch("/student/live_location")

.then(response=>response.json())

.then(data=>{

marker.setLatLng([

parseFloat(data.latitude),

parseFloat(data.longitude)

]);

updatePopup(data);

map.panTo([

parseFloat(data.latitude),

parseFloat(data.longitude)

]);

})

.catch(error=>{

console.log(error);

});

}


// Every 5 Seconds

setInterval(loadLiveLocation,5000);