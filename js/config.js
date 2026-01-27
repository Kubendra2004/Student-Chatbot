/* ========================================
   CONFIGURATION FILE
   ======================================== */

const CONFIG = {
    // SheetDB API Configuration
    // Replace 'YOUR_API_ID' with your actual SheetDB API ID
    SHEETDB_API_URL: 'https://sheetdb.io/api/v1/5k35gbb74g1k5',
    
    // Greetings - Bot will randomly pick one
    GREETINGS: [
        "Hi there! 👋",
        "Hello! How are you doing? 😊",
        "Hey! What's up? 🎉",
        "Greetings, friend! 🌟",
        "Welcome! Great to see you! 🙌",
        "Hello there! Ready to help! 💪",
        "Hey hey! How can I assist you today? 🤖",
        "Hi! Nice to meet you! ✨",
        "Hello, human! 🤝",
        "Howdy! What can I do for you? 🤠",
        "Good to see you! Let's get started! 🚀",
        "Hey there, superstar! ⭐"
    ],
    
    // Facts - Bot will share when asked
    FACTS: [
        "Why don't programmers like nature? It has too many bugs. 🐛",
        "Did you know? The first computer virus was created in 1986. 💻",
        "A computer once beat me at chess, but it was no match for me at kickboxing. 🥊",
        "The first website ever created is still online: http://info.cern.ch 🌐",
        "Did you know? The longest hiccuping spree lasted 68 years! 😮",
        "Why was the math book sad? Because it had too many problems. 📚",
        "There are more stars in the universe than grains of sand on all Earth's beaches. ⭐",
        "Honey never spoils. Archaeologists found 3000-year-old honey that's still edible! 🍯",
        "A single cloud can weigh more than 1 million pounds. ☁️",
        "The first email was sent by Ray Tomlinson to himself in 1971. 📧",
        "Octopuses have three hearts and blue blood! 🐙",
        "A day on Venus is longer than a year on Venus! 🪐",
        "Bananas are berries, but strawberries aren't! 🍌🍓"
    ],
    
    // Help text
    HELP_TEXT: `
Here's what I can help you with:

📝 **Student Management**
• "add a student" - Add a new student record
• "update student" - Update existing student info
• "get student [name]" - Retrieve student info
• "get total [name]" - Get marks and percentage

📊 **View Data**
• "show all students" - View all student records

💬 **Chat**
• "hi" or "hello" - Say hello!
• "tell me a fact" - Get a random fun fact
• "help" - Show this help message

Type any command to get started!
    `.trim(),
    
    // Loading messages
    LOADING_MESSAGES: [
        "Let me check... 🔍",
        "Looking that up... 📚",
        "Processing... ⚙️",
        "One moment... ⏳",
        "Fetching data... 📡"
    ],
    
    // Error messages
    ERROR_MESSAGES: {
        networkError: "Oops! I'm having trouble connecting. Please check your internet and try again. 🔌",
        notFound: "I couldn't find any student with that name. Would you like to add them? 🤔",
        invalidInput: "I didn't quite understand that. Could you try again? 💭",
        saveError: "There was an issue saving the data. Please try again. 💾"
    }
};

// Freeze config to prevent modifications
Object.freeze(CONFIG);
Object.freeze(CONFIG.GREETINGS);
Object.freeze(CONFIG.FACTS);
Object.freeze(CONFIG.LOADING_MESSAGES);
Object.freeze(CONFIG.ERROR_MESSAGES);
