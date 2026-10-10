// ======================================
// FUTURE STORE V2 PREMIUM JAVASCRIPT
// ======================================

document.addEventListener("DOMContentLoaded", () => {

    initializeDarkMode();
    initializeScrollAnimations();
    initializeAIAssistant();
    initializeAIChatWidget();
    initializeFlashSaleCountdown();
    initializeBackToTop();
    initializeProductCarousel();
    initializeAdminImagePreview();

});

// ======================================
// DARK MODE
// ======================================

function initializeDarkMode() {

    const toggle = document.getElementById("darkModeToggle");

    if (!toggle) return;

    const savedTheme = localStorage.getItem("theme");

    if (savedTheme === "dark") {
        document.body.classList.add("dark-mode");
    }

    toggle.addEventListener("click", () => {

        document.body.classList.toggle("dark-mode");

        if (document.body.classList.contains("dark-mode")) {
            localStorage.setItem("theme", "dark");
        } else {
            localStorage.setItem("theme", "light");
        }

    });

}

// ======================================
// AI ASSISTANT BUTTON (opens the real chat panel — see initializeAIChatWidget)
// ======================================

function initializeAIAssistant() {

    const button = document.getElementById("chatButton");

    if (button) {
        button.addEventListener("click", () => {
            toggleAIChatPanel();
        });
    }

    const launchBtn = document.querySelector(".ai-launch-btn");

    if (launchBtn) {
        launchBtn.addEventListener("click", (e) => {
            e.preventDefault();
            toggleAIChatPanel(true);
        });
    }

}

// ======================================
// TOAST NOTIFICATION
// ======================================

function showToast(message) {

    const toast = document.createElement("div");

    toast.className = "future-toast";

    toast.innerHTML = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("show");
    }, 100);

    setTimeout(() => {

        toast.classList.remove("show");

        setTimeout(() => {
            toast.remove();
        }, 500);

    }, 3000);

}

// ======================================
// FLASH SALE COUNTDOWN
// ======================================

function initializeFlashSaleCountdown() {

    const countdown = document.querySelector(".countdown");

    if (!countdown) return;

    let hours = 12;
    let minutes = 45;
    let seconds = 59;

    setInterval(() => {

        seconds--;

        if (seconds < 0) {
            seconds = 59;
            minutes--;
        }

        if (minutes < 0) {
            minutes = 59;
            hours--;
        }

        if (hours < 0) {
            hours = 12;
            minutes = 45;
            seconds = 59;
        }

        countdown.innerHTML =
            `${hours}h ${minutes}m ${seconds}s`;

    }, 1000);

}

// ======================================
// SCROLL ANIMATIONS (fade-in + slide-up)
// ======================================
// Adds the `.reveal-up` class to cards so the CSS transition in
// style.css (opacity + translateY) is the single source of truth for the
// motion, then flips `.is-visible` on once each card enters the viewport.
// Parent grids get `.reveal-stagger` so style.css can apply a small
// nth-child delay per card, producing a cascading entrance instead of
// every card animating in unison.

function initializeScrollAnimations() {

    const elements = document.querySelectorAll(
        ".product-card, .category-card, .flash-card, .step-card, .faq-item"
    );

    elements.forEach((element) => element.classList.add("reveal-up"));

    document.querySelectorAll(
        ".products-grid, .categories-grid, .flash-grid, .steps-grid"
    ).forEach((grid) => grid.classList.add("reveal-stagger"));

    const observer = new IntersectionObserver((entries) => {

        entries.forEach((entry) => {

            if (entry.isIntersecting) {
                entry.target.classList.add("is-visible");
                observer.unobserve(entry.target);
            }

        });

    }, { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });

    elements.forEach((element) => observer.observe(element));

}

// ======================================
// BACK TO TOP
// ======================================

function initializeBackToTop() {

    const btn =
        document.createElement("button");

    btn.innerHTML = "↑";

    btn.id = "backToTop";

    document.body.appendChild(btn);

    window.addEventListener("scroll", () => {

        if (window.scrollY > 500) {

            btn.classList.add("show");

        } else {

            btn.classList.remove("show");

        }

    });

    btn.addEventListener("click", () => {

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    });

}

// ======================================
// PRODUCT QUICK VIEW (Future Use)
// ======================================

function quickView(productName) {

    showToast(
        `👀 Quick View: ${productName}`
    );

}

// ======================================
// CART TOAST
// ======================================

function addedToCart(productName) {

    showToast(
        `🛒 ${productName} added to cart`
    );

}

// ======================================
// WISHLIST TOAST
// ======================================

function addedToWishlist(productName) {

    showToast(
        `❤️ ${productName} added to wishlist`
    );

}
// ======================================
// PRODUCT CAROUSEL (Swiper.js, category-tabbed)
// ======================================

function initializeProductCarousel() {

    const tabs = document.querySelectorAll(".carousel-tab");
    const swiperEls = document.querySelectorAll(".future-swiper");

    if (!swiperEls.length || typeof Swiper === "undefined") return;

    // One Swiper instance per category section. Only the active tab's
    // section is visible at a time, but Swiper needs every instance
    // initialized up front (not lazily on tab switch) so its layout
    // calculations are correct once a hidden section becomes visible.
    const swiperInstances = [];

    swiperEls.forEach((el) => {

        const instance = new Swiper(el, {
            loop: el.querySelectorAll(".swiper-slide").length > 4,
            autoplay: {
                delay: 3500,
                disableOnInteraction: false,
                pauseOnMouseEnter: true,
            },
            speed: 600,
            spaceBetween: 22,
            slidesPerView: 1.2,
            pagination: {
                el: el.querySelector(".swiper-pagination"),
                clickable: true,
            },
            navigation: {
                nextEl: el.querySelector(".swiper-button-next"),
                prevEl: el.querySelector(".swiper-button-prev"),
            },
            breakpoints: {
                480:  { slidesPerView: 2,   spaceBetween: 16 },
                768:  { slidesPerView: 3,   spaceBetween: 20 },
                1024: { slidesPerView: 4,   spaceBetween: 22 },
            },
        });

        swiperInstances.push(instance);

    });

    tabs.forEach((tab) => {

        tab.addEventListener("click", () => {

            const targetId = tab.dataset.target;

            tabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");

            swiperEls.forEach((el) => {
                if (el.id === targetId) {
                    el.classList.remove("hidden");
                } else {
                    el.classList.add("hidden");
                }
            });

            // Swiper miscalculates slide widths for elements that were
            // hidden (display:none) during initialization, so re-measure
            // the newly-shown instance now that it's visible.
            const shownIndex = Array.from(swiperEls).findIndex((el) => el.id === targetId);
            if (shownIndex > -1 && swiperInstances[shownIndex]) {
                swiperInstances[shownIndex].update();
            }

        });

    });

}

// ======================================
// AI CHAT WIDGET
// ======================================
// Talks to POST /ai/chat (services/ai_service.py) which answers from the
// real product catalog + a small set of store-policy facts. The panel
// keeps its own in-memory message list for the current page view; the
// server additionally keeps a short rolling history in the session so a
// fresh page load can still feel continuous if extended later.

function toggleAIChatPanel(forceOpen) {

    const panel = document.getElementById("aiChatPanel");
    const button = document.getElementById("chatButton");

    if (!panel || !button) return;

    const shouldOpen = forceOpen === true ? true : !panel.classList.contains("is-open");

    panel.classList.toggle("is-open", shouldOpen);
    button.classList.toggle("is-active", shouldOpen);
    panel.setAttribute("aria-hidden", shouldOpen ? "false" : "true");
    button.setAttribute("aria-expanded", shouldOpen ? "true" : "false");

    if (shouldOpen) {
        const input = document.getElementById("aiChatInput");
        if (input) setTimeout(() => input.focus(), 200);
    }

}

function initializeAIChatWidget() {

    const panel = document.getElementById("aiChatPanel");
    const form = document.getElementById("aiChatForm");
    const input = document.getElementById("aiChatInput");
    const messages = document.getElementById("aiChatMessages");
    const closeBtn = document.getElementById("aiChatClose");
    const resetBtn = document.getElementById("aiChatReset");

    if (!panel || !form || !input || !messages) return;

    closeBtn?.addEventListener("click", () => toggleAIChatPanel(false));

    // Quick-reply chips send their own label as the user's message.
    messages.querySelectorAll(".ai-quick-reply").forEach((chip) => {
        chip.addEventListener("click", () => {
            sendAIChatMessage(chip.textContent.trim());
        });
    });

    resetBtn?.addEventListener("click", async () => {

        try {
            await fetch("/ai/chat/reset", { method: "POST" });
        } catch (err) {
            // Non-fatal — the panel still resets visually even if the
            // server-side history clear fails (e.g. offline demo use).
        }

        messages.innerHTML = `
            <div class="ai-chat-msg ai-chat-msg-bot">
                <p>New conversation started. What can I help you find?</p>
            </div>
        `;

    });

    form.addEventListener("submit", (e) => {
        e.preventDefault();

        const text = input.value.trim();
        if (!text) return;

        input.value = "";
        sendAIChatMessage(text);

    });

}

function sendAIChatMessage(text) {

    const messages = document.getElementById("aiChatMessages");
    const sendBtn = document.querySelector(".ai-chat-send-btn");

    if (!messages) return;

    appendAIChatBubble(text, "user");

    // Remove any quick-reply chips once the conversation is underway —
    // they're only useful as a first-message prompt.
    messages.querySelectorAll(".ai-chat-quick-replies").forEach((el) => el.remove());

    const typingEl = document.createElement("div");
    typingEl.className = "ai-chat-typing";
    typingEl.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(typingEl);
    messages.scrollTop = messages.scrollHeight;

    if (sendBtn) sendBtn.disabled = true;

    fetch("/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
    })
        .then((res) => res.json())
        .then((data) => {

            typingEl.remove();

            if (data.error) {
                appendAIChatBubble("Sorry, something went wrong. Please try again.", "bot");
                return;
            }

            appendAIChatBubble(data.reply, "bot");

            if (Array.isArray(data.products) && data.products.length) {
                appendAIChatProducts(data.products);
            }

        })
        .catch(() => {
            typingEl.remove();
            appendAIChatBubble(
                "I'm having trouble connecting right now. Please try again in a moment.",
                "bot"
            );
        })
        .finally(() => {
            if (sendBtn) sendBtn.disabled = false;
        });

}

function appendAIChatBubble(text, role) {

    const messages = document.getElementById("aiChatMessages");
    if (!messages) return;

    const bubble = document.createElement("div");
    bubble.className = `ai-chat-msg ai-chat-msg-${role}`;

    const p = document.createElement("p");
    p.textContent = text;
    bubble.appendChild(p);

    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;

}

function appendAIChatProducts(products) {

    const messages = document.getElementById("aiChatMessages");
    if (!messages) return;

    const wrap = document.createElement("div");
    wrap.className = "ai-chat-products";

    products.forEach((p) => {

        const card = document.createElement("a");
        card.className = "ai-chat-product-card";
        card.href = `/product/${p.id}`;

        const img = document.createElement("img");
        img.src = p.image || "/static/images/placeholder.svg";
        img.alt = p.name;
        img.onerror = function () { this.src = "/static/images/placeholder.svg"; };

        const info = document.createElement("div");
        const name = document.createElement("strong");
        name.textContent = p.name;
        const price = document.createElement("span");
        price.textContent = `$${Number(p.price).toFixed(2)}`;
        info.appendChild(name);
        info.appendChild(price);

        card.appendChild(img);
        card.appendChild(info);
        wrap.appendChild(card);

    });

    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;

}

// ======================================
// ADMIN: live image URL preview on the
// Add/Edit Product form
// ======================================

function initializeAdminImagePreview() {

    const input = document.getElementById("image");
    const preview = document.getElementById("adminImagePreview");

    if (!input || !preview) return;

    const img = preview.querySelector("img") || document.createElement("img");
    if (!preview.contains(img)) preview.appendChild(img);

    function update() {

        const url = input.value.trim();

        if (!url) {
            preview.classList.add("is-empty");
            img.style.display = "none";
            return;
        }

        img.src = url;
        img.style.display = "block";
        preview.classList.remove("is-empty");

        img.onerror = () => {
            img.src = "/static/images/placeholder.svg";
        };

    }

    input.addEventListener("input", update);
    update();

}
