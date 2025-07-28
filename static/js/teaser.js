// Carrousel swiper
const swiper = new Swiper('.swiper', {
    loop: true,
    autoplay: {
        delay: 4000,
        disableOnInteraction: false,
    },
    pagination: {
        el: '.swiper-pagination',
        clickable: true,
    },
    navigation: {
        nextEl: '.swiper-button-next',
        prevEl: '.swiper-button-prev',
    },
    effect: 'fade',
    fadeEffect: {
        crossFade: true,
    }
});

// Afficher l'heure
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('fr-FR', {
        hour: '2-digit', 
        minute: '2-digit'
    });
    document.getElementById('current-time').textContent = timeString;
}

async function updateWeatherCard() {
    try {

        console.log("Début géolocalisation...");

        // Géolocalisation
        // navigator.geolocation.getCurrentPosition(
        //     (pos) => console.log("Position:", pos.coords.latitude, pos.coords.longitude),
        //     (err) => console.error("Erreur géoloc:", err)
        // )
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 1000,
                maximumAge: 0
            });
        });

        console.log("Position obtenue:", position.coords.latitude, position.coords.longitude);

        // Appel à FastAPI
        const response = await fetch(`/api/meteo?lat=${position.coords.latitude}&lon=${position.coords.longitude}`);
        console.log("Status response:", response.status);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log("Données météo reçues:", data);

        // Mise à jour de l'interface
        updateWeatherUI(data);
        // document.getElementById('weather-location').textContent = data.ville;
        // document.getElementById('weather-temp').textContent = `${data.temperature}°C`;
        // document.getElementById('weather-desc').textContent = data.description;
        // document.getElementById('weather-icon').className = `fas ${data.icone}`;
    } catch (error) {
        console.error("Erreur de géolocalisation ou API", error);
        console.log("Fallback vers Paris...");
        // Paris si erreur
        updateWeatherUI({
                ville: "Paris",
                temperature: "23",
                description: "Données indisponibles",
                icone: "fa-cloud"
            }, true);
        // fetch('/api/meteo?ville=Paris')
        //     .then(response => response.json())
        //     .then(data => {
        //         document.getElementById('weather-location').textContent = data.ville + " (par défaut)";
        //         document.getElementById('weather-temp').textContent = `${data.temperature}°C`;
        //         document.getElementById('weather-desc').textContent = data.description;
        //         document.getElementById('weather-icon').className = `fas ${data.icone}`;
        //     });
    }
}

function updateWeatherUI(data, isFallback = false) {
    console.log("Mise à jour de l'UI météo:", data);

    const locationText = isFallback ? `${data.ville}` : data.ville;

    document.getElementById('weather-temp').textContent = `${data.temperature}°C`;
    document.getElementById('weather-desc').textContent = data.description;
    document.getElementById('weather-icon').className = `fas ${data.icone}`;

    // Maj de l'icone
    const iconElement = document.getElementById('weather-icon');
    iconElement.className = `fas ${data.icone} text-2xl mr-4 text-blue-300`;
}

// function updateWeatherCard(data, isFallback = false) {
//     const locationText = isFallback ? `${data.ville} (par défaut)` : data.ville;
    
//     document.getElementById('weather-location').textContent = locationText;
//     document.getElementById('weather-temp').textContent = `${data.temperature}°C`;
//     document.getElementById('weather-desc').textContent = data.description;
    
//     // Correction de la typo et ajout des classes CSS complètes
//     const iconElement = document.getElementById('weather-icon');
//     iconElement.className = `fas ${data.icone} text-2xl mr-4 text-blue-300`;
// }

// MUSIQUE
async function updateMusic() {
    try {
        const response = await fetch('/api/musique/now-playing');
        const data = await response.json();

        const musicCard = document.getElementById('music-card');
        musicCard.querySelector('.track-title').textContent = data.titre;
        musicCard.querySelector('.track-artist').textContent = data.artiste;

        const coverImg = musicCard.querySelector('#music-cover');
        if (data.cover && data.cover.startsWith('http')) {
            coverImg.src = data.cover; //Image venant de Deezer
        } else {
                coverImg.src = `/static/media/${data.cover || 'musique.jpg'}`;  //Image locale
            }
            
        const audioPlayer = musicCard.querySelector('#music-preview');
        if (data.preview) {
            audioPlayer.src = data.preview;
            audioPlayer.style.display = 'block';
        } else {
            audioPlayer.style.display = 'none';
        }
    } catch (error) {
        console.error("Erreur de lecture", error)
    }
}

// Initisalisation
document.addEventListener('DOMContentLoaded', function(){
    console.log("Initisalisation de l'application");

    updateTime();
    updateWeatherCard();
    updateMusic();

    setInterval(updateTime, 1000);
    setInterval(updateWeatherCard, 3600000);
    setInterval(updateMusic, 180000);
    
})

// Actualisation
// updateTime();
// updateWeatherCard();
// updateMusic();
// setInterval(updateTime, 1000);
// setInterval(updateWeatherCard, 3600000);
// setInterval(updateMusic, 180000);