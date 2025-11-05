document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.getAttribute("data-page");
  if (page) console.log(`Loaded: ${page}`);

  // === MAP INITIALIZATION ===
  window.initMap = function(lat = -1.286389, lng = 36.817223) {
    const mapElement = document.getElementById("map");
    if (!mapElement) return;

    const location = { lat: parseFloat(lat), lng: parseFloat(lng) };
    const map = new google.maps.Map(mapElement, {
      zoom: 14,
      center: location
    });

    new google.maps.Marker({
      position: location,
      map: map
    });
  };

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => initMap(pos.coords.latitude, pos.coords.longitude),
      () => initMap()
    );
  } else {
    initMap();
  }

  // === FORM VALIDATION ===
  if (page === "signup") {
    const signupForm = document.querySelector("form[action='/signup']");
    if (signupForm) {
      signupForm.addEventListener("submit", (e) => {
        const email = signupForm.querySelector("input[name='email']");
        const password = signupForm.querySelector("input[name='password']");
        const name = signupForm.querySelector("input[name='name']");

        if (!email.value.includes("@")) {
          alert("Please enter a valid email.");
          e.preventDefault();
        }
        if (password.value.length < 6) {
          alert("Password must be at least 6 characters.");
          e.preventDefault();
        }
        if (name.value.trim() === "") {
          alert("Name cannot be empty.");
          e.preventDefault();
        }
      });
    }
  }

  // === CHAT ===
  if (page === "chat") {
    const sendBtn = document.getElementById("sendMessage");
    const messageBox = document.getElementById("message");
    const messageList = document.getElementById("messages");

    if (sendBtn && messageBox && messageList) {
      sendBtn.addEventListener("click", () => {
        const msg = messageBox.value.trim();
        if (msg !== "") {
          const div = document.createElement("div");
          div.className = "user-message";
          div.textContent = msg;
          messageList.appendChild(div);
          messageBox.value = "";
        }
      });
    }
  }

  // === DARK MODE ===
  const themeToggle = document.getElementById('themeToggle');
  const body = document.getElementById('body');
  const icon = themeToggle ? themeToggle.querySelector('i') : null;

  if (themeToggle && icon) {
    themeToggle.addEventListener('click', () => {
      body.classList.toggle('dark-mode');
      if (body.classList.contains('dark-mode')) {
        icon.classList.replace('fa-moon', 'fa-sun');
        localStorage.setItem('theme', 'dark');
      } else {
        icon.classList.replace('fa-sun', 'fa-moon');
        localStorage.setItem('theme', 'light');
      }
    });

    if (localStorage.getItem('theme') === 'dark') {
      body.classList.add('dark-mode');
      icon.classList.replace('fa-moon', 'fa-sun');
    }
  }
});
