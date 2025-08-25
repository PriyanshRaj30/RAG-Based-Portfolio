// Chat System Configuration
const CHAT_CONFIG = {
    API_ENDPOINT: '/api/chat', // Backend endpoint for chat responses
    TYPING_SPEED: 50, // Milliseconds between characters when typing
    STARTUP_DELAY: 1000, // Delay before starting terminal boot sequence
    MESSAGE_DELAY: 500 // Delay before showing AI response
};

// Global variables
let chatContainer, chatInput;

// Particles Animation
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    const particleCount = 50;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 6 + 's';
        particle.style.animationDuration = (Math.random() * 3 + 3) + 's';
        particlesContainer.appendChild(particle);
    }
}

// Chat System Functions
async function sendMessageToBackend(message) {
    try {
        const response = await fetch(CHAT_CONFIG.API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                timestamp: new Date().toISOString()
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data.response;
    } catch (error) {
        console.error('Error sending message to backend:', error);
        return 'Sorry, I\'m having trouble connecting to my knowledge base. Please try again later.';
    }
}

function addMessage(text, isUser = false) {
    const message = document.createElement('div');
    message.className = `message ${isUser ? 'user' : 'ai'}`;
    
    if (isUser) {
        message.innerHTML = `<span class="message-prefix">[USER]</span> ${text}`;
    } else {
        message.innerHTML = `<span class="message-prefix">[AI]</span> <span class="typing">Ans:${text}</span>`;
    }
    
    chatContainer.appendChild(message);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    if (!isUser) {
        // Simulate typing effect
        const typingElement = message.querySelector('.typing');
        let index = 0;
        const originalText = text;
        typingElement.textContent = '';
        
        function typeChar() {
            if (index < originalText.length) {
                typingElement.textContent += originalText.charAt(index);
                index++;
                setTimeout(typeChar, Math.random() * CHAT_CONFIG.TYPING_SPEED + 20);
            } else {
                typingElement.classList.remove('typing');
            }
        }
        
        setTimeout(typeChar, 300);
    }
}

async function handleUserMessage(userInput) {
    if (!userInput.trim()) return;
    
    // Add user message to chat
    addMessage(userInput, true);
    
    // Show typing indicator
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'message ai typing-indicator';
    typingIndicator.innerHTML = '<span class="message-prefix">[AI]</span> <span class="typing">Thinking...</span>';
    chatContainer.appendChild(typingIndicator);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    try {
        // Get response from backend
        const response = await sendMessageToBackend(userInput);
        
        // Remove typing indicator
        chatContainer.removeChild(typingIndicator);
        
        // Add AI response
        setTimeout(() => {
            addMessage(response);
        }, CHAT_CONFIG.MESSAGE_DELAY);
        
    } catch (error) {
        // Remove typing indicator and show error message
        chatContainer.removeChild(typingIndicator);
        setTimeout(() => {
            addMessage('Sorry, I encountered an error. Please try again.');
        }, CHAT_CONFIG.MESSAGE_DELAY);
    }
}

// Terminal startup animation
function terminalStartup() {
    const startupMessages = [
        "SYSTEM INITIALIZING...",
        "LOADING DEVELOPER PROFILE...",
        "CONNECTING TO NEURAL NETWORK...",
        "READY FOR INTERACTION!"
    ];

    let messageIndex = 0;
    function showStartupMessage() {
        if (messageIndex < startupMessages.length) {
            const message = document.createElement('div');
            message.className = 'message ai';
            message.innerHTML = `<span class="message-prefix">[BOOT]</span> ${startupMessages[messageIndex]}`;
            
            setTimeout(() => {
                if (messageIndex === startupMessages.length - 1) {
                    // Clear startup messages and show welcome
                    setTimeout(() => {
                        chatContainer.innerHTML = `
                            <div class="scanlines"></div>
                            <div class="message ai">
                                <span class="message-prefix">[SYSTEM]</span> Welcome to my portfolio interface...<br>
                                <span class="message-prefix">[AI]</span> Hello! I'm an interactive assistant that knows everything about this developer.<br>
                                <span class="message-prefix">[AI]</span> Ask me anything about skills, projects, experience, or just say hi!<br>
                                <span class="message-prefix">[AI]</span> Try: "What technologies do you work with?" or "Tell me about your projects from template"
                            </div>
                        `;
                    }, 1000);
                }
            }, 500);
            
            messageIndex++;
            setTimeout(showStartupMessage, 800);
        }
    }
    
    // Clear initial content and start boot sequence
    setTimeout(() => {
        chatContainer.innerHTML = '<div class="scanlines"></div>';
        showStartupMessage();
    }, CHAT_CONFIG.STARTUP_DELAY);
}

// Matrix-style text effect for hero title
function matrixEffect() {
    const title = document.querySelector('.hero-title');
    if (!title) return;
    
    const text = title.textContent;
    
    title.addEventListener('mouseenter', () => {
        let iterations = 0;
        const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*";
        
        const interval = setInterval(() => {
            title.textContent = text
                .split("")
                .map((letter, index) => {
                    if (index < iterations) {
                        return text[index];
                    }
                    return letters[Math.floor(Math.random() * letters.length)];
                })
                .join("");
            
            if (iterations >= text.length) {
                clearInterval(interval);
            }
            
            iterations += 1 / 3;
        }, 50);
    });
}

// Smooth scrolling for navigation
function initSmoothScrolling() {
    document.querySelectorAll('nav a').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Active navigation highlighting
function initNavigationHighlighting() {
    window.addEventListener('scroll', () => {
        const sections = document.querySelectorAll('.section, .container');
        const navLinks = document.querySelectorAll('nav a');
        
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            if (window.scrollY >= sectionTop - 200) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href').slice(1) === current) {
                link.classList.add('active');
            }
        });
    });
}

// Custom cursor effect
function initCustomCursor() {
    const cursor = document.createElement('div');
    cursor.className = 'custom-cursor';
    document.body.appendChild(cursor);

    document.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX - 10 + 'px';
        cursor.style.top = e.clientY - 10 + 'px';
    });

    document.addEventListener('mousedown', () => {
        cursor.style.transform = 'scale(0.8)';
    });

    document.addEventListener('mouseup', () => {
        cursor.style.transform = 'scale(1)';
    });

    // Add hover effects for interactive elements
    document.querySelectorAll('a, button, .project-card, .contact-item').forEach(element => {
        element.addEventListener('mouseenter', () => {
            cursor.style.transform = 'scale(1.5)';
            cursor.style.background = 'var(--cyber-pink)';
            cursor.style.boxShadow = '0 0 20px var(--cyber-pink)';
        });
        
        element.addEventListener('mouseleave', () => {
            cursor.style.transform = 'scale(1)';
            cursor.style.background = 'var(--terminal-green)';
            cursor.style.boxShadow = '0 0 10px var(--terminal-green)';
        });
    });
}

// Intersection Observer for animations
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Add animation styles to cards
    document.querySelectorAll('.project-card, .skill-category, .contact-item').forEach(card => {
        observer.observe(card);
    });
}

// Chat input event listener
function initChatInput() {
    chatInput = document.getElementById('chat-input');
    chatContainer = document.getElementById('chat-container');
    
    if (chatInput) {
        chatInput.addEventListener('keypress', async function(e) {
            if (e.key === 'Enter') {
                const userInput = this.value.trim();
                if (userInput) {
                    await handleUserMessage(userInput);
                    this.value = '';
                }
            }
        });
    }
}

// Easter eggs and special interactions
function initEasterEggs() {
    // Konami code
    let konamiCode = '';
    const konami = '38384040373937396665';
    
    document.addEventListener('keydown', (e) => {
        konamiCode += e.keyCode;
        if (konamiCode === konami) {
            addMessage("🎮 KONAMI CODE ACTIVATED! You found the secret developer mode! This developer appreciates attention to detail and curiosity. Bonus points for you!");
            konamiCode = '';
        } else if (konamiCode.length > 20) {
            konamiCode = konamiCode.slice(-10);
        }
    });
    
    // Secret developer console messages
    console.log('%c🚀 Welcome to the Developer Portfolio!', 'color: #00ff41; font-size: 18px; font-weight: bold;');
    console.log('%cLooking at the code? I appreciate your curiosity!', 'color: #00d4ff; font-size: 14px;');
    console.log('%cFeel free to reach out if you have any questions.', 'color: #ff006e; font-size: 14px;');
}

// Performance monitoring
function initPerformanceMonitoring() {
    window.addEventListener('load', () => {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        console.log(`🚀 Portfolio loaded in ${loadTime}ms - Optimized for maximum impact!`);
    });
}

// Error handling for chat system
function handleChatError(error) {
    console.error('Chat system error:', error);
    addMessage('Oops! Something went wrong. Please refresh the page and try again.');
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    try {
        // Initialize core components
        createParticles();
        initChatInput();
        initSmoothScrolling();
        initNavigationHighlighting();
        initCustomCursor();
        initScrollAnimations();
        
        // Initialize effects and animations
        terminalStartup();
        matrixEffect();
        
        // Initialize easter eggs and monitoring
        initEasterEggs();
        initPerformanceMonitoring();
        
        // Focus chat input after startup
        setTimeout(() => {
            if (chatInput) {
                chatInput.focus();
            }
        }, 3000);
        
    } catch (error) {
        console.error('Error initializing portfolio:', error);
    }
});

// Export functions for potential external use
window.PortfolioApp = {
    sendMessage: handleUserMessage,
    addMessage: addMessage,
    config: CHAT_CONFIG
};