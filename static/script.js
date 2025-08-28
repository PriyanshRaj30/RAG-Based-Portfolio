// Apple-Inspired Portfolio JavaScript with Enhanced Email Integration

// Configuration
const CONFIG = {
  API_ENDPOINT: '/api/chat',
  TYPING_SPEED: 30,
  SCROLL_THRESHOLD: 0.1,
  ANIMATION_DURATION: 600,
  CHAT_AUTO_SCROLL: true,
  SMOOTH_SCROLL_DURATION: 800
};

// State management
const state = {
  isTyping: false,
  currentSection: 'home',
  animatedElements: new Set(),
  chatHistory: [],
  scrollPosition: 0,
  username: null
};

// DOM elements
const elements = {
  nav: null,
  navLinks: null,
  chatInput: null,
  chatMessages: null,
  sendButton: null,
  sections: null
};

// Utility functions
const utils = {
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  throttle(func, limit) {
    let inThrottle;
    return function() {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  },

  easeOutQuart(t) {
    return 1 - (--t) * t * t * t;
  },

  generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  },

  formatTime(date) {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }
};

// Notification system
const notifications = {
  show(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style the notification
    Object.assign(notification.style, {
      position: 'fixed',
      top: '20px',
      right: '20px',
      padding: '12px 20px',
      borderRadius: '8px',
      color: 'white',
      fontWeight: '500',
      zIndex: '10000',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      transition: 'all 0.3s ease',
      backgroundColor: type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#3B82F6',
      opacity: '0',
      transform: 'translateX(100%)'
    });
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
      notification.style.opacity = '1';
      notification.style.transform = 'translateX(0)';
    }, 10);
    
    // Remove after duration
    setTimeout(() => {
      notification.style.opacity = '0';
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, duration);
  },

  success(message) {
    this.show(message, 'success');
  },

  error(message) {
    this.show(message, 'error');
  },

  info(message) {
    this.show(message, 'info');
  }
};

// Username management
const userManager = {
  getUsername() {
    if (!state.username) {
      state.username = sessionStorage.getItem('chat_username') || null;
    }
    return state.username || 'Anonymous User';
  },

  setUsername(username) {
    if (username && username.trim()) {
      const cleanUsername = username.trim();
      state.username = cleanUsername;
      sessionStorage.setItem('chat_username', cleanUsername);
      console.log('Username set:', cleanUsername);
      return true;
    }
    return false;
  },

  hasUsername() {
    return this.getUsername() !== 'Anonymous User';
  },

  clearUsername() {
    state.username = null;
    sessionStorage.removeItem('chat_username');
  },

  promptForUsername() {
    const username = prompt("Please enter your name (optional):", "");
    if (username !== null && username.trim()) {
      if (this.setUsername(username)) {
        notifications.success(`Nice to meet you, ${username.trim()}!`);
        return username.trim();
      }
    }
    return null;
  },

  detectUsernameInMessage(message) {
    const namePatterns = [
      /my name is ([a-zA-Z]{2,20})/i,
      /i'm ([a-zA-Z]{2,20})/i,
      /i am ([a-zA-Z]{2,20})/i,
      /call me ([a-zA-Z]{2,20})/i,
      /it's ([a-zA-Z]{2,20})/i,
      /this is ([a-zA-Z]{2,20})/i
    ];

    // Check if message is a simple single name response
    const singleWordMatch = message.trim().match(/^([a-zA-Z]{2,20})$/);
    if (singleWordMatch) {
      const word = singleWordMatch[1].toLowerCase();
      const commonWords = ['hello', 'hi', 'hey', 'yes', 'no', 'ok', 'sure', 'thanks', 'thank', 'please'];
      if (!commonWords.includes(word)) {
        return singleWordMatch[1];
      }
    }

    for (const pattern of namePatterns) {
      const match = message.match(pattern);
      if (match && match[1]) {
        const detectedName = match[1];
        const commonWords = ['hello', 'hi', 'hey', 'yes', 'no', 'ok', 'sure', 'fine', 'good', 'bad'];
        if (!commonWords.includes(detectedName.toLowerCase())) {
          return detectedName;
        }
      }
    }
    return null;
  }
};

// Email functionality
const emailManager = {
  async sendChatHistory(customEmail = null, customUsername = null) {
    try {
      let username = customUsername || userManager.getUsername();
      let email = customEmail || "priyanshraj3020@gmail.com";
      
      // If no username and not provided, prompt for it
      if (username === 'Anonymous User' && !customUsername) {
        const promptedUsername = userManager.promptForUsername();
        if (promptedUsername) {
          username = promptedUsername;
        }
      }
      
      const sessionId = chat.getSessionId();
      
      // Check if there's any chat history
      if (state.chatHistory.length === 0) {
        notifications.error('No chat history to send.');
        return false;
      }
      
      notifications.info('Sending chat history...');
      
      const response = await fetch("/api/chat/email_histories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          username: username,
          to_email: email
        }),
        keepalive: true
      });
      
      const result = await response.json();
      
      if (result.success) {
        notifications.success(`Chat history sent successfully to ${result.details.recipient}`);
        console.log(`Chat history emailed to ${result.details.recipient} for user: ${result.details.username}`);
        return true;
      } else {
        notifications.error(`Failed to send email: ${result.error || 'Unknown error'}`);
        console.error("Failed to email chat history:", result);
        return false;
      }
      
    } catch (error) {
      console.error("Error sending chat history:", error);
      notifications.error('Error sending chat history. Please check your connection.');
      return false;
    }
  },

  async sendOnPageUnload() {
    // Check if there's any meaningful chat history to send
    if (state.chatHistory.length <= 1) return; // Don't send if only welcome message
    
    const sessionId = chat.getSessionId();
    const username = userManager.getUsername();
    
    try {
      await fetch("/api/chat/email_histories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          username: username,
          to_email: "priyanshraj3020@gmail.com"
        }),
        keepalive: true
      });
    } catch (error) {
      console.error("Failed to send chat history on page unload:", error);
    }
  }
};

// Navigation functionality
const navigation = {
  init() {
    elements.navLinks = document.querySelectorAll('.nav-link');
    elements.sections = document.querySelectorAll('.section, .hero-section');
    this.bindEvents();
    this.updateActiveLink();
  },

  bindEvents() {
    elements.navLinks.forEach(link => {
      link.addEventListener('click', this.handleNavClick.bind(this));
    });
    window.addEventListener('scroll', utils.throttle(this.handleScroll.bind(this), 16));
  },

  handleNavClick(event) {
    event.preventDefault();
    const href = event.target.getAttribute('href');
    const targetSection = document.querySelector(href);
    if (targetSection) this.scrollToSection(targetSection);
  },

  scrollToSection(section) {
    const headerOffset = 80;
    const elementPosition = section.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
    window.scrollTo({ top: offsetPosition, behavior: 'smooth' });
  },

  handleScroll() {
    this.updateNavBackground();
    this.updateActiveLink();
    this.triggerScrollAnimations();
    state.scrollPosition = window.pageYOffset;
  },

  updateNavBackground() {
    const nav = document.querySelector('.nav');
    const links = document.querySelectorAll('.nav-link');
    const navlogo = document.querySelector('#nav-logo');
    if (window.pageYOffset > 750) {
      nav.style.background = 'rgba(255, 255, 255, 0.95)';
      links.forEach(link => link.style.color = 'rgba(0, 68, 255, 0.92)');
      navlogo.style.color = 'rgb(4, 33, 194)';
    } else {
      nav.style.background = 'rgba(0, 0, 0, 0.8)';
      links.forEach(link => link.style.color = "#aeaeb2");
      navlogo.style.color = 'rgb(76, 121, 212)';
    }
  },

  updateActiveLink() {
    let current = 'home';
    elements.sections.forEach(section => {
      const sectionTop = section.getBoundingClientRect().top;
      if (sectionTop <= 100 && sectionTop > -section.offsetHeight + 100) {
        current = section.getAttribute('id');
      }
    });
    if (current !== state.currentSection) {
      state.currentSection = current;
      elements.navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${current}`) {
          link.classList.add('active');
        }
      });
    }
  },

  triggerScrollAnimations() {
    const animatableElements = document.querySelectorAll('.project-card, .skill-category, .contact-card');
    animatableElements.forEach(element => {
      const elementId = element.dataset.animateId || utils.generateId();
      element.dataset.animateId = elementId;
      if (state.animatedElements.has(elementId)) return;
      const rect = element.getBoundingClientRect();
      const isVisible = rect.top <= window.innerHeight * 0.8 && rect.bottom >= 0;
      if (isVisible) {
        element.classList.add('animate-on-scroll', 'animated');
        state.animatedElements.add(elementId);
      }
    });
  }
};

// Chat functionality
const chat = {
  waitingForName: false,

  init() {
    elements.chatInput = document.getElementById('chat-input');
    elements.chatMessages = document.getElementById('chat-messages');
    elements.sendButton = document.getElementById('send-button');
    this.bindEvents();
    this.showWelcomeMessage();
    this.addEmailButton();
  },

  bindEvents() {
    elements.chatInput.addEventListener('keydown', this.handleKeyDown.bind(this));
    elements.chatInput.addEventListener('input', this.handleInputChange.bind(this));
    elements.sendButton.addEventListener('click', this.handleSendClick.bind(this));
  },

  handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  },

  handleInputChange(event) {
    const hasText = event.target.value.trim().length > 0;
    elements.sendButton.disabled = !hasText || state.isTyping;
    if (event.target.tagName === 'TEXTAREA') {
      event.target.style.height = 'auto';
      event.target.style.height = event.target.scrollHeight + 'px';
    }
  },

  handleSendClick() {
    this.sendMessage();
  },

  async sendMessage() {
    const message = elements.chatInput.value.trim();
    if (!message || state.isTyping) return;
  
    this.addMessage(message, 'user');
    elements.chatInput.value = '';
    elements.sendButton.disabled = true;
  
    // Check for username detection
    this.handleUsernameDetection(message);
  
    // 🚨 NEW CONDITION: If last assistant message was asking for name, skip backend
    const lastAssistantMsg = [...elements.chatMessages.querySelectorAll('.message.assistant')]
      .pop()?.innerText.trim();
  
    if (lastAssistantMsg &&
        lastAssistantMsg.includes("By the way, what should I call you? (This will help personalize our conversation)")) {
      // Don’t call backend, just wait for username handling
      return;
    }
  
    // Continue with typing indicator + backend call
    const typingId = this.showTypingIndicator();
    state.isTyping = true;
  
    try {
      const response = await this.sendToBackend(message);
      this.removeTypingIndicator(typingId);
      await this.addMessageWithTyping(response, 'assistant');
    } catch (error) {
      console.error('Chat error:', error);
      this.removeTypingIndicator(typingId);
      this.addMessage("I apologize, but I'm having trouble processing your request. Please try again.", 'assistant');
    } finally {
      state.isTyping = false;
      this.handleInputChange({ target: elements.chatInput });
      elements.chatInput.focus();
    }
  },
  
  handleUsernameDetection(message) {
    if (!userManager.hasUsername() || this.waitingForName) {
      const detectedName = userManager.detectUsernameInMessage(message);
      if (detectedName) {
        if (userManager.setUsername(detectedName)) {
          this.waitingForName = false;
          setTimeout(() => {
            this.addMessage(`Nice to meet you, ${detectedName}! Feel free to ask me anything about Priyansh's background.`, 'assistant');
          }, 1000);
        }
      }
    }
  },

  async sendToBackend(message) {
    const response = await fetch(CONFIG.API_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        timestamp: new Date().toISOString(),
        session_id: this.getSessionId(),
        username: userManager.getUsername()
      })
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return data.response;
  },

  getSessionId() {
    let sessionId = sessionStorage.getItem('chat_session_id');
    if (!sessionId) {
      sessionId = utils.generateId();
      sessionStorage.setItem('chat_session_id', sessionId);
    }
    return sessionId;
  },

  addMessage(content, sender) {
    const messageElement = this.createMessageElement(content, sender);
    elements.chatMessages.appendChild(messageElement);
    this.scrollToBottom();
    state.chatHistory.push({
      id: utils.generateId(),
      content,
      sender,
      timestamp: new Date()
    });
    return messageElement;
  },

  async addMessageWithTyping(content, sender) {
    const messageElement = this.createMessageElement('', sender);
    const contentElement = messageElement.querySelector('.message-content p');
    elements.chatMessages.appendChild(messageElement);
    
    let processedContent = content;
    if (sender === 'assistant' && typeof marked !== 'undefined') {
      processedContent = marked.parse(content);
      contentElement.innerHTML = '';
    }
    
    if (sender === 'assistant') {
      await this.typeText(contentElement, processedContent, sender === 'assistant');
    } else {
      contentElement.textContent = content;
    }
    
    this.scrollToBottom();
    state.chatHistory.push({
      id: utils.generateId(),
      content,
      sender,
      timestamp: new Date()
    });
  },

  async typeText(element, text, isHTML = false) {
    if (isHTML) {
      await new Promise(resolve => setTimeout(resolve, 300));
      element.innerHTML = text;
      return;
    }
    element.textContent = '';
    for (let i = 0; i < text.length; i++) {
      element.textContent += text[i];
      this.scrollToBottom();
      await new Promise(resolve => setTimeout(resolve, CONFIG.TYPING_SPEED));
    }
  },

  createMessageElement(content, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    const paragraph = document.createElement('p');
    paragraph.textContent = content;
    contentDiv.appendChild(paragraph);
    messageDiv.appendChild(contentDiv);
    return messageDiv;
  },

  showTypingIndicator() {
    const typingId = utils.generateId();
    const typingElement = document.createElement('div');
    typingElement.className = 'message assistant typing-indicator';
    typingElement.dataset.typingId = typingId;
    typingElement.innerHTML = `
      <div class="message-content">
        <div class="typing-dots">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      </div>
    `;
    elements.chatMessages.appendChild(typingElement);
    this.scrollToBottom();
    return typingId;
  },

  removeTypingIndicator(typingId) {
    const typingElement = elements.chatMessages.querySelector(`[data-typing-id="${typingId}"]`);
    if (typingElement) typingElement.remove();
  },

  scrollToBottom() {
    if (CONFIG.CHAT_AUTO_SCROLL) {
      elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }
  },

  showWelcomeMessage() {
    setTimeout(() => {
      this.addMessage("Hello! I'm Priyansh's AI assistant. Feel free to ask me anything about his skills, projects, or experience!", 'assistant');
      
      // Ask for name if not known
      setTimeout(() => {
        if (!userManager.hasUsername()) {
          this.waitingForName = true;
          this.addMessage("By the way, what should I call you? (This will help personalize our conversation)", 'assistant');
        } else {
          this.addMessage(`Welcome back, ${userManager.getUsername()}!`, 'assistant');
        }
      }, 2000);
    }, 1000);
  },

  addEmailButton() {
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer && !document.querySelector('.email-history-btn')) {
      const emailButton = document.createElement('button');
      emailButton.textContent = '📧 Email History';
      emailButton.className = 'email-history-btn';
      emailButton.onclick = () => emailManager.sendChatHistory();
      emailButton.title = 'Send chat history to email';
      
      Object.assign(emailButton.style, {
        position: 'absolute',
        top: '10px',
        right: '10px',
        padding: '8px 12px',
        background: '#007AFF',
        color: 'white',
        border: 'none',
        borderRadius: '6px',
        cursor: 'pointer',
        fontSize: '12px',
        fontWeight: '500',
        boxShadow: '0 2px 8px rgba(0,122,255,0.2)',
        transition: 'all 0.2s ease',
        zIndex: '100'
      });
      
      emailButton.addEventListener('mouseover', () => {
        emailButton.style.background = '#0056CC';
        emailButton.style.transform = 'translateY(-1px)';
      });
      
      emailButton.addEventListener('mouseout', () => {
        emailButton.style.background = '#007AFF';
        emailButton.style.transform = 'translateY(0)';
      });
      
      chatContainer.style.position = 'relative';
      chatContainer.appendChild(emailButton);
    }
  }
};

// Performance optimization
const performance = {
  init() {
    this.optimizeImages();
    this.preloadCriticalResources();
    this.monitorPerformance();
  },

  optimizeImages() {
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.classList.add('loaded');
          observer.unobserve(img);
        }
      });
    });
    images.forEach(img => imageObserver.observe(img));
  },

  preloadCriticalResources() {
    const fontLinks = [
      'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
    ];
    fontLinks.forEach(href => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'style';
      link.href = href;
      document.head.appendChild(link);
    });
  },

  monitorPerformance() {
    if ('performance' in window) {
      window.addEventListener('load', () => {
        const perfData = performance.getEntriesByType('navigation')[0];
        const loadTime = perfData.loadEventEnd - perfData.fetchStart;
        console.log(`Portfolio loaded in ${loadTime}ms`);
      });
    }
  }
};

// Accessibility enhancements
const accessibility = {
  init() {
    this.setupKeyboardNavigation();
    this.setupFocusManagement();
    this.setupReducedMotion();
  },

  setupKeyboardNavigation() {
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') elements.chatInput.blur();
      if (event.altKey) {
        switch (event.key) {
          case '1':
            navigation.scrollToSection(document.querySelector('#home')); break;
          case '2':
            navigation.scrollToSection(document.querySelector('#projects')); break;
          case '3':
            navigation.scrollToSection(document.querySelector('#skills')); break;
          case '4':
            navigation.scrollToSection(document.querySelector('#contact')); break;
        }
      }
    });
  },

  setupFocusManagement() {
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Tab') document.body.classList.add('keyboard-navigation');
    });
    document.addEventListener('mousedown', () => {
      document.body.classList.remove('keyboard-navigation');
    });
  },

  setupReducedMotion() {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (prefersReducedMotion.matches) {
      document.documentElement.style.setProperty('--transition-base', 'none');
      document.documentElement.style.setProperty('--transition-smooth', 'none');
      CONFIG.TYPING_SPEED = 10;
    }
  }
};

// Error handling
const errorHandler = {
  init() {
    window.addEventListener('error', this.handleError.bind(this));
    window.addEventListener('unhandledrejection', this.handlePromiseRejection.bind(this));
  },

  handleError(event) {
    console.error('Script error:', event.error);
    this.logError('Script Error', event.error);
  },

  handlePromiseRejection(event) {
    console.error('Unhandled promise rejection:', event.reason);
    this.logError('Promise Rejection', event.reason);
  },

  logError(type, error) {
    const errorLog = {
      type,
      message: error.message || error,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      username: userManager.getUsername()
    };
    console.log('Error logged:', errorLog);
  }
};

// Page unload event handler
window.addEventListener("beforeunload", async (event) => {
  await emailManager.sendOnPageUnload();
});

// Visibility change handler (for mobile/tab switching)
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === 'hidden') {
    emailManager.sendOnPageUnload();
  }
});

// Main initialization
document.addEventListener('DOMContentLoaded', () => {
  try {
    // Initialize all modules
    navigation.init();
    chat.init();
    performance.init();
    accessibility.init();
    errorHandler.init();
    
    // Mark page as loaded
    document.body.classList.add('loaded');
    
    // Focus chat input after everything is loaded
    setTimeout(() => {
      if (elements.chatInput) elements.chatInput.focus();
    }, 2000);
    
    console.log('Portfolio initialized successfully');
    console.log('Current user:', userManager.getUsername());
    
  } catch (error) {
    console.error('Initialization error:', error);
    errorHandler.logError('Initialization Error', error);
    notifications.error('Failed to initialize portfolio. Please refresh the page.');
  }
});

// Public API - Export functions for external access
window.PortfolioApp = {
  // Core modules
  navigation,
  chat,
  performance,
  accessibility,
  utils,
  
  // State and config
  state,
  CONFIG,
  
  // User management
  userManager,
  
  // Email functionality
  emailManager,
  
  // Notifications
  notifications,
  
  // Public methods
  sendChatHistory: () => emailManager.sendChatHistory(),
  setUsername: (name) => userManager.setUsername(name),
  getUsername: () => userManager.getUsername(),
  showNotification: (message, type) => notifications.show(message, type),
  
  // Dev/debug methods
  clearUsername: () => userManager.clearUsername(),
  getChatHistory: () => state.chatHistory,
  getSessionId: () => chat.getSessionId()
};

