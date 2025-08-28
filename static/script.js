// Apple-Inspired Portfolio JavaScript

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
  scrollPosition: 0
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
  // Debounce function for performance optimization
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

  // Throttle function for scroll events
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

  // Smooth easing function
  easeOutQuart(t) {
    return 1 - (--t) * t * t * t;
  },

  // Generate unique ID
  generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  },

  // Format timestamp
  formatTime(date) {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
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
    
    if (targetSection) {
      this.scrollToSection(targetSection);
    }
  },

  scrollToSection(section) {
    const headerOffset = 80;
    const elementPosition = section.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
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
    const navlogo = document.querySelector('#nav-logo')

    if (window.pageYOffset > 750) {
      nav.style.background = 'rgba(255, 255, 255, 0.95)';
      links.forEach(link => link.style.color = 'rgba(0, 68, 255, 0.92)');
      navlogo.style.color = 'rgb(4, 33, 194)'
    } else {
      nav.style.background = 'rgba(0, 0, 0, 0.8)';
      links.forEach(link => link.style.color = "#aeaeb2");
      navlogo.style.color = 'rgb(76, 121, 212)'
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
  init() {
    elements.chatInput = document.getElementById('chat-input');
    elements.chatMessages = document.getElementById('chat-messages');
    elements.sendButton = document.getElementById('send-button');
    
    this.bindEvents();
    this.showWelcomeMessage();
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
    
    // Auto-resize input (if needed for textarea)
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

    // Add user message
    this.addMessage(message, 'user');
    elements.chatInput.value = '';
    elements.sendButton.disabled = true;

    // Show typing indicator
    const typingId = this.showTypingIndicator();
    state.isTyping = true;

    try {
      // Send to backend
      const response = await this.sendToBackend(message);
      
      // Remove typing indicator
      this.removeTypingIndicator(typingId);
      
      // Add AI response with typing animation
      await this.addMessageWithTyping(response, 'assistant');
      
    } catch (error) {
      console.error('Chat error:', error);
      this.removeTypingIndicator(typingId);
      this.addMessage('I apologize, but I\'m having trouble processing your request. Please try again.', 'assistant');
    } finally {
      state.isTyping = false;
      this.handleInputChange({ target: elements.chatInput });
      elements.chatInput.focus();
    }
  },

  async sendToBackend(message) {
    const response = await fetch(CONFIG.API_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        timestamp: new Date().toISOString(),
        session_id: this.getSessionId()
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

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
    
    // Store in history
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
    
    // Parse markdown if it's from assistant
    let processedContent = content;
    if (sender === 'assistant' && typeof marked !== 'undefined') {
      processedContent = marked.parse(content);
      contentElement.innerHTML = '';
    }
    
    // Typing animation
    if (sender === 'assistant') {
      await this.typeText(contentElement, processedContent, sender === 'assistant');
    } else {
      contentElement.textContent = content;
    }
    
    this.scrollToBottom();
    
    // Store in history
    state.chatHistory.push({
      id: utils.generateId(),
      content,
      sender,
      timestamp: new Date()
    });
  },

  async typeText(element, text, isHTML = false) {
    if (isHTML) {
      // For HTML content, show it all at once with a slight delay
      await new Promise(resolve => setTimeout(resolve, 300));
      element.innerHTML = text;
      return;
    }
    
    // Character by character typing for plain text
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
    if (typingElement) {
      typingElement.remove();
    }
  },

  scrollToBottom() {
    if (CONFIG.CHAT_AUTO_SCROLL) {
      elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }
  },

  showWelcomeMessage() {
    setTimeout(() => {
      this.addMessage(
          'Hello! I\'m Priyansh\,\n feel free to ask me about anything you\'d like to know about me.'
      );
    }, 1000);
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
    // Lazy load images when they come into viewport
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
    // Preload critical fonts
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
    // Enhanced keyboard navigation for chat
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        elements.chatInput.blur();
      }
      
      // Quick navigation shortcuts
      if (event.altKey) {
        switch (event.key) {
          case '1':
            navigation.scrollToSection(document.querySelector('#home'));
            break;
          case '2':
            navigation.scrollToSection(document.querySelector('#projects'));
            break;
          case '3':
            navigation.scrollToSection(document.querySelector('#skills'));
            break;
          case '4':
            navigation.scrollToSection(document.querySelector('#contact'));
            break;
        }
      }
    });
  },

  setupFocusManagement() {
    // Improve focus visibility
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Tab') {
        document.body.classList.add('keyboard-navigation');
      }
    });

    document.addEventListener('mousedown', () => {
      document.body.classList.remove('keyboard-navigation');
    });
  },

  setupReducedMotion() {
    // Respect user's motion preferences
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    
    if (prefersReducedMotion.matches) {
      document.documentElement.style.setProperty('--transition-base', 'none');
      document.documentElement.style.setProperty('--transition-smooth', 'none');
      CONFIG.TYPING_SPEED = 10; // Faster typing if reduced motion is preferred
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
    // In a production environment, you would send this to your logging service
    const errorLog = {
      type,
      message: error.message || error,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    };
    
    console.log('Error logged:', errorLog);
  }
};

// Main initialization
document.addEventListener('DOMContentLoaded', () => {
  try {
    // Initialize core functionality
    navigation.init();
    chat.init();
    performance.init();
    accessibility.init();
    errorHandler.init();
    
    // Add smooth loading animation
    document.body.classList.add('loaded');
    
    // Focus chat input after a delay
    setTimeout(() => {
      if (elements.chatInput) {
        elements.chatInput.focus();
      }
    }, 2000);
    
    console.log('Portfolio initialized successfully');
    
  } catch (error) {
    console.error('Initialization error:', error);
    errorHandler.logError('Initialization Error', error);
  }
});

// Export for potential external use
window.PortfolioApp = {
  navigation,
  chat,
  performance,
  accessibility,
  utils,
  state,
  CONFIG
};