// ==========================================
// DRIVER FIREBASE MESSAGING CONFIGURATION
// ==========================================


// ==========================================
// IMPORT FIREBASE MODULES
// ==========================================

import {
    initializeApp
}
from
"https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js";


import {
    getMessaging,
    getToken,
    onMessage
}
from
"https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging.js";


// ==========================================
// FIREBASE CONFIG
// ==========================================

const firebaseConfig = {

    apiKey:
        "AIzaSyAs_2tuaYLrdCF8JvUOQgYyEX_Lnh62ufI",

    authDomain:
        "college-bus-tracking-sys-6a022.firebaseapp.com",

    projectId:
        "college-bus-tracking-sys-6a022",

    storageBucket:
        "college-bus-tracking-sys-6a022.firebasestorage.app",

    messagingSenderId:
        "544220473884",

    appId:
        "1:544220473884:web:72690d560496222dc1cdd9",

    measurementId:
        "G-NCXZTHHHP1"

};


// ==========================================
// INITIALIZE FIREBASE
// ==========================================

const app = initializeApp(firebaseConfig);

const messaging = getMessaging(app);


// ==========================================
// REGISTER FIREBASE SERVICE WORKER
// ==========================================

const registration =
    await navigator.serviceWorker.register(
        "/static/firebase-messaging-sw.js"
    );


console.log(
    "Driver Firebase Service Worker Registered:",
    registration
);


// ==========================================
// REQUEST NOTIFICATION PERMISSION
// ==========================================

async function requestDriverNotificationPermission() {

    try {

        const permission =
            await Notification.requestPermission();


        console.log(
            "Driver notification permission:",
            permission
        );


        // ==========================================
        // IF PERMISSION IS GRANTED
        // ==========================================

        if (permission === "granted") {

            console.log(
                "Driver notification permission granted."
            );


            // ==========================================
            // WEB PUSH VAPID KEY
            // ==========================================

            const vapidKey =
                "BCpDdLwy_SdgqJ0U56fevVc8LATO2Mp-Pske85ZgQpnBcWwY_OGJjgv0LfR-2_RU-YvEXjz8KkpNvDQL0yVJhWY";


            // ==========================================
            // GENERATE FCM TOKEN
            // ==========================================

            const currentToken =
                await getToken(
                    messaging,
                    {
                        vapidKey: vapidKey,

                        serviceWorkerRegistration:
                            registration
                    }
                );


            // ==========================================
            // CHECK TOKEN
            // ==========================================

            if (currentToken) {

                console.log(
                    "Driver FCM Token:",
                    currentToken
                );


                // ==========================================
                // SAVE TOKEN TO FLASK / MYSQL
                // ==========================================

                const response =
                    await fetch(
                        "/driver/save-fcm-token",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify(
                                    {
                                        fcm_token:
                                            currentToken
                                    }
                                )
                        }
                    );


                const result =
                    await response.json();


                console.log(
                    "Driver FCM Token Save Result:",
                    result
                );

            }

            else {

                console.log(
                    "No Driver FCM token available."
                );

            }

        }

        else {

            console.log(
                "Driver notification permission not granted."
            );

        }

    }

    catch (error) {

        console.error(
            "Driver notification permission error:",
            error
        );

    }

}


// ==========================================
// LISTEN FOR FOREGROUND NOTIFICATIONS
// ==========================================

onMessage(
    messaging,

    async (payload) => {

        console.log(
            "Driver foreground notification received:",
            payload
        );


        const title =
            payload.notification?.title ||
            "College Bus Tracking";


        const body =
            payload.notification?.body ||
            "You have a new notification.";


        console.log(
            "Driver notification title:",
            title
        );

        console.log(
            "Driver notification body:",
            body
        );


        // ==========================================
        // SHOW REAL BROWSER / MOBILE NOTIFICATION
        // ==========================================

        if (
            Notification.permission === "granted"
        ) {

            try {

                const serviceWorkerRegistration =
                    await navigator.serviceWorker.ready;


                await serviceWorkerRegistration
                    .showNotification(

                        title,

                        {
                            body: body,

                            icon:
                                "/static/images/logo.png",

                            badge:
                                "/static/images/logo.png",

                            data: {

                                url:
                                    "/driver_dashboard"

                            }

                        }

                    );


                console.log(
                    "Driver browser notification displayed successfully."
                );

            }

            catch (error) {

                console.error(
                    "Error displaying Driver browser notification:",
                    error
                );

            }

        }


        // ==========================================
        // SEND EVENT TO CURRENT DRIVER PAGE
        // ==========================================

        window.dispatchEvent(

            new CustomEvent(

                "firebaseNotificationReceived",

                {

                    detail: {

                        title:
                            title,

                        body:
                            body,

                        timestamp:
                            new Date()

                    }

                }

            )

        );

    }

);


// ==========================================
// MAKE FUNCTION AVAILABLE GLOBALLY
// ==========================================

window.requestDriverNotificationPermission =
    requestDriverNotificationPermission;


// ==========================================
// AUTOMATICALLY REGISTER FCM
// ==========================================

if (
    Notification.permission === "granted"
) {

    requestDriverNotificationPermission();

}

else if (
    Notification.permission === "default"
) {

    requestDriverNotificationPermission();

}