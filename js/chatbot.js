/* ========================================
   CHATBOT LOGIC - Message Handling
   ======================================== */

const Chatbot = {
    conversationState: null,
    pendingStudentData: {},
    
    // Process user message
    async processMessage(message) {
        const lowerMessage = message.toLowerCase().trim();
        
        // Handle conversation state (multi-step flows)
        if (this.conversationState) {
            return await this.handleConversationFlow(message);
        }
        
        // Command matching
        if (lowerMessage === 'help' || lowerMessage === '?') {
            return { type: 'text', content: CONFIG.HELP_TEXT };
        }
        
        if (lowerMessage === 'hi' || lowerMessage === 'hello' || lowerMessage === 'hey') {
            return { type: 'text', content: this.getRandomItem(CONFIG.GREETINGS) };
        }
        
        if (lowerMessage.includes('fact') || lowerMessage.includes('joke')) {
            return { type: 'text', content: this.getRandomItem(CONFIG.FACTS) };
        }
        
        if (lowerMessage.includes('add a student') || lowerMessage.includes('add student')) {
            return this.startAddStudentFlow();
        }
        
        if (lowerMessage.includes('update student')) {
            return this.startUpdateFlow();
        }
        
        if (lowerMessage.includes('get student') || lowerMessage.includes('retrieve student') || lowerMessage.includes('find student')) {
            const name = this.extractName(lowerMessage, ['get student', 'retrieve student', 'find student']);
            if (name) {
                return await this.getStudent(name);
            }
            this.conversationState = 'awaiting_search_name';
            return { type: 'text', content: "What's the student's name you're looking for? 🔍" };
        }
        
        if (lowerMessage.includes('get total') || lowerMessage.includes('retrieve total')) {
            const name = this.extractName(lowerMessage, ['get total', 'retrieve total']);
            if (name) {
                return await this.getStudentTotal(name);
            }
            this.conversationState = 'awaiting_total_name';
            return { type: 'text', content: "Whose total marks would you like to see? 📊" };
        }
        
        if (lowerMessage.includes('show all') || lowerMessage.includes('all students') || lowerMessage.includes('list students')) {
            return await this.getAllStudents();
        }
        
        // Default response
        return { 
            type: 'text', 
            content: "I'm not sure how to respond to that. 🤔\n\nType **help** to see what I can do!" 
        };
    },
    
    // Handle multi-step conversation
    async handleConversationFlow(message) {
        const state = this.conversationState;
        
        switch (state) {
            case 'awaiting_search_name':
                this.conversationState = null;
                return await this.getStudent(message.trim());
            
            case 'awaiting_total_name':
                this.conversationState = null;
                return await this.getStudentTotal(message.trim());
            
            default:
                this.conversationState = null;
                return { type: 'text', content: "Let's start fresh. How can I help you?" };
        }
    },
    
    // Start add student flow (opens modal)
    startAddStudentFlow() {
        return { 
            type: 'action', 
            action: 'openAddModal',
            content: "I'll open a form for you to add a new student. Please fill in the details! 📝" 
        };
    },
    
    startUpdateFlow() {
        this.conversationState = 'awaiting_update_name';
        return {
            type: 'action',
            action: 'openUpdateModal',
            content: "I'll open the form for updating a student. Enter the student's name to load their current data! ✏️"
        };
    },
    
    // Get student info
    async getStudent(name) {
        try {
            const student = await StudentAPI.getStudentByName(name);
            
            if (!student) {
                return { 
                    type: 'text', 
                    content: `I couldn't find anyone named "${name}". 😕\n\nWould you like to **add a student** with this name?` 
                };
            }
            
            return {
                type: 'table',
                title: `📋 Student Information: ${student.Name}`,
                data: student,
                content: `Here's what I found for **${student.Name}**:`
            };
        } catch (error) {
            console.error('Error:', error);
            return { type: 'text', content: CONFIG.ERROR_MESSAGES.networkError };
        }
    },
    
    // Get student total
    async getStudentTotal(name) {
        try {
            const result = await StudentAPI.getStudentTotal(name);
            
            if (!result) {
                return { type: 'text', content: `No student found with the name "${name}". 😕` };
            }
            
            const grade = this.getGrade(result.percentage);
            
            return {
                type: 'text',
                content: `📊 **Marks Summary for ${result.name}**\n\n` +
                    `| Subject | Marks |\n|---------|-------|\n` +
                    `| Math | ${result.math} |\n` +
                    `| Science | ${result.science} |\n` +
                    `| English | ${result.english} |\n` +
                    `| Programming | ${result.programming} |\n\n` +
                    `**Total:** ${result.total}/400\n` +
                    `**Percentage:** ${result.percentage}%\n` +
                    `**Grade:** ${grade}`
            };
        } catch (error) {
            return { type: 'text', content: CONFIG.ERROR_MESSAGES.networkError };
        }
    },
    
    // Get all students
    async getAllStudents() {
        try {
            const students = await StudentAPI.getAllStudents();
            
            if (!students || students.length === 0) {
                return { type: 'text', content: "No students in the database yet. Would you like to **add a student**? 📝" };
            }
            
            return {
                type: 'multiTable',
                title: `📚 All Students (${students.length} records)`,
                data: students,
                content: `Found **${students.length}** student records:`
            };
        } catch (error) {
            return { type: 'text', content: CONFIG.ERROR_MESSAGES.networkError };
        }
    },
    
    // Helper functions
    extractName(message, triggers) {
        for (const trigger of triggers) {
            if (message.includes(trigger)) {
                const name = message.split(trigger)[1].trim();
                return name || null;
            }
        }
        return null;
    },
    
    getRandomItem(array) {
        return array[Math.floor(Math.random() * array.length)];
    },
    
    getGrade(percentage) {
        const p = parseFloat(percentage);
        if (p >= 90) return '🏆 A+ (Outstanding!)';
        if (p >= 80) return '🌟 A (Excellent!)';
        if (p >= 70) return '👍 B (Good)';
        if (p >= 60) return '📗 C (Average)';
        if (p >= 50) return '📙 D (Pass)';
        return '📕 F (Needs Improvement)';
    }
};

window.Chatbot = Chatbot;
