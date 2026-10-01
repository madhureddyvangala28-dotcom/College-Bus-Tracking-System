// ==========================================
// FIREBASE MESSAGING SERVICE WORKER
// ==========================================


// ==========================================
// IMPORT FIREBASE COMPAT LIBRARIES
// ==========================================

importScripts(
    "https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js"
);

importScripts(
    "https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js"
);


// ==========================================
// FIREBASE CONFIGURATION
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

firebase.initializeApp(firebaseConfig);


// ==========================================
// INITIALIZE FIREBASE MESSAGING
// ==========================================

const messaging =
    firebase.messaging();


// ==========================================
// BACKGROUND NOTIFICATIONS
// ==========================================

messaging.onBackgroundMessage(

    (payload) => {

        console.log(
            "🔥 Firebase background notification received:",
            payload
        );


        // ======================================
        // GET NOTIFICATION TITLE
        // ======================================

        const notificationTitle =

            payload.notification?.title ||

            payload.data?.title ||

            "College Bus Tracking";


        // ======================================
        // GET NOTIFICATION BODY
        // ======================================

        const notificationBody =

            payload.notification?.body ||

            payload.data?.body ||

            "You have a new notification.";


        // ======================================
        // GET TARGET URL
        // ======================================

        const targetUrl =

            payload.data?.url ||

            "/";


        // ======================================
        // NOTIFICATION OPTIONS
        // ======================================

        const notificationOptions = {

            body:
                notificationBody,

            icon:
                "/static/images/logo.png",

            badge:
                "/static/images/logo.png",

            tag:
                "college-bus-notification",

            renotify:
                true,

            data: {

                url:
                    targetUrl

            }

        };


        // ======================================
        // SHOW MOBILE / BROWSER NOTIFICATION
        // ======================================

        self.registration.showNotification(

            notificationTitle,

            notificationOptions

        );


        console.log(
            "✅ Background notification displayed."
        );

    }

);


// ==========================================
// NOTIFICATION CLICK EVENT
// ==========================================

self.addEventListener(

    "notificationclick",

    (event) => {

        console.log(
            "Notification clicked:",
            event.notification
        );


        // ======================================
        // CLOSE NOTIFICATION
        // ======================================

        event.notification.close();


        // ======================================
        // GET TARGET URL
        // ======================================

        const targetUrl =

            event.notification.data?.url ||

            "/";


        // ======================================
        // OPEN / FOCUS APPLICATION
        // ======================================

        event.waitUntil(

            clients.matchAll({

                type:
                    "window",

                includeUncontrolled:
                    true

            })

            .then(

                (clientList) => {

                    // ==================================
                    // CHECK IF APP IS ALREADY OPEN
                    // ==================================

                    for (

                        const client of clientList

                    ) {

                        if (

                            client.url.includes(
                                targetUrl
                            )

                            &&

                            "focus" in client

                        ) {

                            return client.focus();

                        }

                    }


                    // ==================================
                    // OPEN NEW WINDOW
                    // ==================================

                    if (

                        clients.openWindow

                    ) {

                        return clients.openWindow(
                            targetUrl
                        );

                    }

                }

            )

        );

    }

);