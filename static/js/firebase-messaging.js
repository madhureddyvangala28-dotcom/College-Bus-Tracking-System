// ==========================================
// FIREBASE MESSAGING CONFIGURATION
// ==========================================

// Import Firebase modules
import { initializeApp } from
    "https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js";

import {
    getMessaging,
    getToken,
    onMessage
} from
    "https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging.js";


// ==========================================
// FIREBASE CONFIG
// ==========================================

const firebaseConfig = {

    apiKey: "AIzaSyAs_2tuaYLrdCF8JvUOQgYyEX_Lnh62ufI",

    authDomain: "college-bus-tracking-sys-6a022.firebaseapp.com",

    projectId: "college-bus-tracking-sys-6a022",

    storageBucket: "college-bus-tracking-sys-6a022.firebasestorage.app",

    messagingSenderId: "544220473884",

    appId: "1:544220473884:web:72690d560496222dc1cdd9",

    measurementId: "G-NCXZTHHHP1"

};


// ==========================================
// INITIALIZE FIREBASE
// ==========================================

const app = initializeApp(firebaseConfig);

const messaging = getMessaging(app);

// ==========================================
// REGISTER FIREBASE SERVICE WORKER
// ==========================================

const registration = await navigator.serviceWorker.register(
    "/static/firebase-messaging-sw.js"
);

console.log(
    "Firebase Service Worker Registered:",
    registration
);

// ==========================================
// REQUEST NOTIFICATION PERMISSION
// ==========================================

async function requestNotificationPermission() {

    try {

        // ==========================================
        // REQUEST NOTIFICATION PERMISSION
        // ==========================================

        const permission = await Notification.requestPermission();

        console.log(
            "Notification permission:",
            permission
        );


        // ==========================================
        // IF PERMISSION IS GRANTED
        // ==========================================

        if (permission === "granted") {

            console.log(
                "Notification permission granted."
            );


            // ==========================================
            // WEB PUSH VAPID KEY
            // ==========================================

            const vapidKey =
                "BCpDdLwy_SdgqJ0U56fevVc8LATO2Mp-Pske85ZgQpnBcWwY_OGJjgv0LfR-2_RU-YvEXjz8KkpNvDQL0yVJhWY";


            // ==========================================
            // GENERATE FCM TOKEN
            // ==========================================

            const currentToken = await getToken(
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
                    "FCM Token:",
                    currentToken
                );


                // ==========================================
                // SAVE FCM TOKEN TO FLASK / MYSQL
                // ==========================================

                const response = await fetch(
                    "/student/save-fcm-token",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type": "application/json"
                        },

                        body: JSON.stringify({
                            fcm_token: currentToken
                        })
                    }
                );


                const result = await response.json();


                console.log(
                    "FCM Token Save Result:",
                    result
                );

            }
        }

    }

    catch (error) {

        console.error(
            "Notification permission error:",
            error
        );

    }

}
// ==========================================
// LISTEN FOR FOREGROUND NOTIFICATIONS
// ==========================================

onMessage(messaging, async (payload) => {

    console.log(
        "Foreground notification received:",
        payload
    );

    const title =
        payload.notification?.title ||
        "College Bus Tracking";

    const body =
        payload.notification?.body ||
        "You have a new notification.";

    console.log("Notification title:", title);
    console.log("Notification body:", body);


    // ==========================================
    // SHOW REAL BROWSER NOTIFICATION
    // ==========================================

    if (Notification.permission === "granted") {

        try {

            const registration =
                await navigator.serviceWorker.ready;


            await registration.showNotification(
                title,
                {
                    body: body,
                    icon: "/static/images/logo.png",
                    badge: "/static/images/logo.png",

                    data: {
                        url: "/student_dashboard"
                    }
                }
            );


            console.log(
                "Browser notification displayed successfully."
            );

        }

        catch (error) {

            console.error(
                "Error displaying browser notification:",
                error
            );

        }

    }
    // ==========================================
    // UPDATE DASHBOARD NOTIFICATION UI
    // ==========================================

    // Send notification data to the current page
    window.dispatchEvent(

        new CustomEvent(
            "firebaseNotificationReceived",
            {

                detail: {

                    title: title,

                    body: body,

                    timestamp: new Date()

                }

            }
        )

    );

});
// ==========================================
// MAKE FUNCTION AVAILABLE
// ==========================================

window.requestNotificationPermission =
    requestNotificationPermission;