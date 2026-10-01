function openAddStopModal(){

    document
    .getElementById("addStopModal")
    .style.display="flex";

}

function closeAddStopModal(){

    document
    .getElementById("addStopModal")
    .style.display="none";

}

function openEditModal(id, route, name, order){

    document.getElementById("editStopId").value=id;

    document.getElementById("editRoute").value=route;

    document.getElementById("editStopName").value=name;

    document.getElementById("editStopOrder").value=order;

    document.getElementById("editModal").style.display="flex";

}

function closeEditModal(){

    document.getElementById("editModal").style.display="none";

}

function openDeleteModal(id,name){

    document.getElementById("deleteStopName").innerText=name;

    document.getElementById("deleteForm").action=
    "/admin/delete_bus_stop/"+id;

    document.getElementById("deleteModal").style.display="flex";

}

function closeDeleteModal(){

    document.getElementById("deleteModal").style.display="none";

}

function openCoordinateModal(id,name){

    document.getElementById("coordinateStopName").innerHTML=name;

    document.getElementById("coordinateModal").style.display="flex";

}

function closeCoordinateModal(){

    document.getElementById("coordinateModal").style.display="none";

}