// ==========================================
// PARENT FIREBASE MESSAGING CONFIGURATION
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
// FIREBASE VAPID KEY
// ==========================================

const vapidKey =
    "BCpDdLwy_SdgqJ0U56fevVc8LATO2Mp-Pske85ZgQpnBcWwY_OGJjgv0LfR-2_RU-YvEXjz8KkpNvDQL0yVJhWY";


// ==========================================
// REGISTER SERVICE WORKER
// ==========================================

let registration = null;


async function registerParentServiceWorker() {

    try {

        registration =
            await navigator.serviceWorker.register(
                "/static/firebase-messaging-sw.js"
            );


        console.log(
            "Parent Firebase Service Worker Registered:",
            registration
        );


        return registration;

    }

    catch (error) {

        console.error(
            "Parent Service Worker Registration Error:",
            error
        );

        throw error;

    }

}


// ==========================================
// GET AND SAVE PARENT FCM TOKEN
// ==========================================

async function getAndSaveParentFCMToken() {

    try {

        // ======================================
        // MAKE SURE SERVICE WORKER EXISTS
        // ======================================

        if (!registration) {

            registration =
                await registerParentServiceWorker();

        }


        // ======================================
        // GENERATE / GET FCM TOKEN
        // ======================================

        const currentToken =
            await getToken(
                messaging,
                {
                    vapidKey: vapidKey,

                    serviceWorkerRegistration:
                        registration
                }
            );


        // ======================================
        // TOKEN FOUND
        // ======================================

        if (currentToken) {

            console.log(
                "Parent FCM Token:",
                currentToken
            );


            // ==================================
            // SAVE TOKEN TO FLASK / MYSQL
            // ==================================

            const response =
                await fetch(
                    "/parent/save-fcm-token",
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
                "Parent FCM Token Save Result:",
                result
            );


            return currentToken;

        }

        else {

            console.log(
                "No Parent FCM token available."
            );

            return null;

        }

    }

    catch (error) {

        console.error(
            "Parent FCM Token Error:",
            error
        );

        return null;

    }

}


// ==========================================
// REQUEST NOTIFICATION PERMISSION
// ==========================================

async function requestParentNotificationPermission() {

    try {

        console.log(
            "Current Parent notification permission:",
            Notification.permission
        );


        // ======================================
        // IF ALREADY GRANTED
        // ======================================

        if (
            Notification.permission === "granted"
        ) {

            console.log(
                "Parent notification permission already granted."
            );


            return await
                getAndSaveParentFCMToken();

        }


        // ======================================
        // IF DEFAULT → ASK USER
        // ======================================

        if (
            Notification.permission === "default"
        ) {

            const permission =
                await Notification.requestPermission();


            console.log(
                "Parent notification permission:",
                permission
            );


            if (permission === "granted") {

                console.log(
                    "Parent notification permission granted."
                );


                return await
                    getAndSaveParentFCMToken();

            }

            else {

                console.log(
                    "Parent notification permission was not granted."
                );

                return null;

            }

        }


        // ======================================
        // IF BLOCKED
        // ======================================

        if (
            Notification.permission === "denied"
        ) {

            console.log(
                "Parent notifications are blocked."
            );

            return null;

        }

    }

    catch (error) {

        console.error(
            "Parent notification permission error:",
            error
        );

        return null;

    }

}


// ==========================================
// LISTEN FOR FOREGROUND NOTIFICATIONS
// ==========================================

onMessage(
    messaging,

    async (payload) => {

        console.log(
            "🔥 Parent foreground notification received:",
            payload
        );


        // ======================================
        // GET NOTIFICATION TITLE
        // ======================================

        const title =
            payload.notification?.title ||
            payload.data?.title ||
            "College Bus Tracking";


        // ======================================
        // GET NOTIFICATION BODY
        // ======================================

        const body =
            payload.notification?.body ||
            payload.data?.body ||
            "You have a new notification.";


        console.log(
            "Parent notification title:",
            title
        );


        console.log(
            "Parent notification body:",
            body
        );


        // ======================================
        // SHOW REAL BROWSER / MOBILE POPUP
        // ======================================

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

                            tag:
                                "parent-notification",

                            renotify:
                                true,

                            data: {

                                url:
                                    "/parent_dashboard"

                            }

                        }

                    );


                console.log(
                    "✅ Parent browser notification displayed successfully."
                );

            }

            catch (error) {

                console.error(
                    "❌ Error displaying Parent browser notification:",
                    error
                );

            }

        }

        else {

            console.log(
                "Parent notification permission is not granted."
            );

        }


        // ======================================
        // SEND EVENT TO CURRENT PARENT PAGE
        // ======================================

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
// INITIALIZE PARENT FIREBASE
// ==========================================

async function initializeParentFirebase() {

    try {

        // ======================================
        // REGISTER SERVICE WORKER
        // ======================================

        await registerParentServiceWorker();


        // ======================================
        // IF PERMISSION ALREADY GRANTED
        // GET AND SAVE TOKEN AUTOMATICALLY
        // ======================================

        if (
            Notification.permission === "granted"
        ) {

            await getAndSaveParentFCMToken();

        }


        console.log(
            "🔥 Parent Firebase Messaging Initialized Successfully"
        );

    }

    catch (error) {

        console.error(
            "Parent Firebase Initialization Error:",
            error
        );

    }

}


// ==========================================
// MAKE FUNCTION AVAILABLE GLOBALLY
// ==========================================

window.requestParentNotificationPermission =
    requestParentNotificationPermission;


// ==========================================
// START FIREBASE
// ==========================================

initializeParentFirebase();