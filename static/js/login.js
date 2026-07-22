/*=========================================
        LOGIN PAGE JAVASCRIPT
=========================================*/

// ===============================
// Get Elements
// ===============================

const studentBtn = document.getElementById("studentBtn");
const driverBtn = document.getElementById("driverBtn");

const roleInput = document.getElementById("role");

const usernameInput = document.querySelector("input[name='username']");

const passwordInput = document.getElementById("password");

const togglePassword = document.querySelector(".toggle-password");


// ===============================
// Default Role
// ===============================

roleInput.value = "student";


// ===============================
// Student Button
// ===============================

studentBtn.addEventListener("click", function () {

    studentBtn.classList.add("active");

    driverBtn.classList.remove("active");

    roleInput.value = "student";

    usernameInput.placeholder = "Enter Roll Number";

});


// ===============================
// Driver Button
// ===============================

driverBtn.addEventListener("click", function () {

    driverBtn.classList.add("active");

    studentBtn.classList.remove("active");

    roleInput.value = "driver";

    usernameInput.placeholder = "Enter Driver ID";

});


// ===============================
// Show / Hide Password
// ===============================

togglePassword.addEventListener("click", function () {

    if (passwordInput.type === "password") {

        passwordInput.type = "text";

        togglePassword.classList.remove("fa-eye");

        togglePassword.classList.add("fa-eye-slash");

    } else {

        passwordInput.type = "password";

        togglePassword.classList.remove("fa-eye-slash");

        togglePassword.classList.add("fa-eye");

    }

});


// ===============================
// Form Validation
// ===============================

const loginForm = document.querySelector("form");

loginForm.addEventListener("submit", function (event) {

    if (usernameInput.value.trim() === "") {

        alert("Please enter your Roll Number or Driver ID.");

        usernameInput.focus();

        event.preventDefault();

        return;

    }

    if (passwordInput.value.trim() === "") {

        alert("Please enter your Password.");

        passwordInput.focus();

        event.preventDefault();

        return;

    }

});


// ===============================
// Console
// ===============================

console.log("College Bus Tracking Login Loaded Successfully.");