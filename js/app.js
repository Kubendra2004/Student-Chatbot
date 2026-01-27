/* ========================================
   MAIN APPLICATION - UI Controller
   ======================================== */

const App = {
    elements: {},
    
    init() {
        this.cacheElements();
        this.bindEvents();
        this.showWelcomeMessage();
        this.checkApiConfig();
        console.log('🚀 Student Bot initialized!');
    },
    
    cacheElements() {
        this.elements = {
            chatMessages: document.getElementById('chatMessages'),
            userInput: document.getElementById('userInput'),
            sendBtn: document.getElementById('sendBtn'),
            typingIndicator: document.getElementById('typingIndicator'),
            helpBtn: document.getElementById('helpBtn'),
            studentFormModal: document.getElementById('studentFormModal'),
            studentForm: document.getElementById('studentForm'),
            modalClose: document.getElementById('modalClose'),
            cancelForm: document.getElementById('cancelForm'),
            toastContainer: document.getElementById('toastContainer')
        };
    },
    
    bindEvents() {
        // Send message
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
        this.elements.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        
        // Help button
        this.elements.helpBtn.addEventListener('click', () => {
            this.elements.userInput.value = 'help';
            this.sendMessage();
        });
        
        // Modal controls
        this.elements.modalClose.addEventListener('click', () => this.closeModal());
        this.elements.cancelForm.addEventListener('click', () => this.closeModal());
        this.elements.studentFormModal.addEventListener('click', (e) => {
            if (e.target === this.elements.studentFormModal) this.closeModal();
        });
        
        // Form submission
        this.elements.studentForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeModal();
        });
    },
    
    checkApiConfig() {
        if (!StudentAPI.isConfigured()) {
            setTimeout(() => {
                this.addBotMessage("⚠️ **API Not Configured**\n\nTo connect to your Google Sheet, open `js/config.js` and replace `YOUR_API_ID` with your SheetDB API ID.");
            }, 1500);
        }
    },
    
    showWelcomeMessage() {
        const greeting = CONFIG.GREETINGS[Math.floor(Math.random() * CONFIG.GREETINGS.length)];
        this.addBotMessage(`${greeting}\n\nI'm your Student Information Assistant! 🎓\n\nI can help you manage student records. Type **help** to see what I can do, or just start chatting!`);
    },
    
    async sendMessage() {
        const message = this.elements.userInput.value.trim();
        if (!message) return;
        
        // Add user message
        this.addUserMessage(message);
        this.elements.userInput.value = '';
        
        // Show typing indicator
        this.showTyping();
        
        // Process message
        try {
            const response = await Chatbot.processMessage(message);
            await this.delay(800 + Math.random() * 700);
            this.hideTyping();
            this.handleResponse(response);
        } catch (error) {
            this.hideTyping();
            this.addBotMessage(CONFIG.ERROR_MESSAGES.networkError);
        }
    },
    
    handleResponse(response) {
        switch (response.type) {
            case 'text':
                this.addBotMessage(response.content);
                break;
            case 'table':
                this.addBotMessage(response.content);
                this.addStudentTable(response.data);
                break;
            case 'multiTable':
                this.addBotMessage(response.content);
                this.addMultiStudentTable(response.data);
                break;
            case 'action':
                this.addBotMessage(response.content);
                if (response.action === 'openAddModal') {
                    setTimeout(() => this.openModal(), 500);
                }
                break;
            default:
                this.addBotMessage(response.content);
        }
    },
    
    addUserMessage(text) {
        const html = `
            <div class="message user">
                <div class="message-content">
                    <div class="message-text">${this.escapeHtml(text)}</div>
                    <div class="message-time">${this.getTime()}</div>
                </div>
                <div class="message-avatar">👤</div>
            </div>
        `;
        this.elements.chatMessages.insertAdjacentHTML('beforeend', html);
        this.scrollToBottom();
    },
    
    addBotMessage(text) {
        const html = `
            <div class="message bot">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <div class="message-text">${this.formatMessage(text)}</div>
                    <div class="message-time">${this.getTime()}</div>
                </div>
            </div>
        `;
        this.elements.chatMessages.insertAdjacentHTML('beforeend', html);
        this.scrollToBottom();
    },
    
    addStudentTable(student) {
        const gradeClass = this.getGradeClass(student.Percentage);
        const html = `
            <div class="message bot">
                <div class="message-avatar">📊</div>
                <div class="message-content">
                    <div class="data-table-wrapper">
                        <table class="data-table">
                            <tr><th>Field</th><th>Value</th></tr>
                            <tr><td>Name</td><td><strong>${this.escapeHtml(student.Name)}</strong></td></tr>
                            <tr><td>Department</td><td>${this.escapeHtml(student.Department)}</td></tr>
                            <tr><td>Year</td><td>${this.escapeHtml(student.Year)}</td></tr>
                            <tr><td>Section</td><td>${this.escapeHtml(student.Section)}</td></tr>
                            <tr><td>Math</td><td>${student.Math}</td></tr>
                            <tr><td>Science</td><td>${student.Science}</td></tr>
                            <tr><td>English</td><td>${student.English}</td></tr>
                            <tr><td>Programming</td><td>${student.Programming}</td></tr>
                            <tr><td>Total</td><td><strong>${student.Total}/400</strong></td></tr>
                            <tr><td>Percentage</td><td class="${gradeClass}"><strong>${student.Percentage}%</strong></td></tr>
                            ${student.Info ? `<tr><td>Info</td><td>${this.escapeHtml(student.Info)}</td></tr>` : ''}
                        </table>
                    </div>
                </div>
            </div>
        `;
        this.elements.chatMessages.insertAdjacentHTML('beforeend', html);
        this.scrollToBottom();
    },
    
    addMultiStudentTable(students) {
        let rows = students.map(s => `
            <tr>
                <td><strong>${this.escapeHtml(s.Name)}</strong></td>
                <td>${this.escapeHtml(s.Department)}</td>
                <td>${s.Year}</td>
                <td>${s.Section}</td>
                <td>${s.Total}</td>
                <td class="${this.getGradeClass(s.Percentage)}">${s.Percentage}%</td>
            </tr>
        `).join('');
        
        const html = `
            <div class="message bot">
                <div class="message-avatar">📚</div>
                <div class="message-content" style="max-width: 100%; overflow-x: auto;">
                    <div class="data-table-wrapper">
                        <table class="data-table">
                            <tr><th>Name</th><th>Dept</th><th>Year</th><th>Sec</th><th>Total</th><th>%</th></tr>
                            ${rows}
                        </table>
                    </div>
                </div>
            </div>
        `;
        this.elements.chatMessages.insertAdjacentHTML('beforeend', html);
        this.scrollToBottom();
    },
    
    getGradeClass(percentage) {
        const p = parseFloat(percentage);
        if (p >= 80) return 'grade-a';
        if (p >= 60) return 'grade-b';
        if (p >= 40) return 'grade-c';
        return 'grade-d';
    },
    
    formatMessage(text) {
        // Convert markdown-like syntax to HTML
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    },
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    getTime() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },
    
    showTyping() {
        this.elements.typingIndicator.classList.add('active');
        this.scrollToBottom();
    },
    
    hideTyping() {
        this.elements.typingIndicator.classList.remove('active');
    },
    
    scrollToBottom() {
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    },
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },
    
    // Modal functions
    openModal() {
        this.elements.studentFormModal.classList.add('active');
        document.getElementById('studentName').focus();
    },
    
    closeModal() {
        this.elements.studentFormModal.classList.remove('active');
        this.elements.studentForm.reset();
    },
    
    async handleFormSubmit(e) {
        e.preventDefault();
        
        const submitBtn = this.elements.studentForm.querySelector('.btn-primary');
        submitBtn.classList.add('loading');
        
        const studentData = {
            Name: document.getElementById('studentName').value,
            Department: document.getElementById('studentDept').value,
            Year: document.getElementById('studentYear').value,
            Section: document.getElementById('studentSection').value.toUpperCase(),
            Math: document.getElementById('marksMath').value,
            Science: document.getElementById('marksScience').value,
            English: document.getElementById('marksEnglish').value,
            Programming: document.getElementById('marksProgramming').value,
            Info: document.getElementById('studentInfo').value
        };
        
        try {
            await StudentAPI.addStudent(studentData);
            submitBtn.classList.remove('loading');
            this.closeModal();
            this.addBotMessage(`✅ **Success!** Student "${studentData.Name}" has been added to the database!`);
            Toast.show('Student added successfully!', 'success');
        } catch (error) {
            submitBtn.classList.remove('loading');
            this.addBotMessage(`❌ Error: ${error.message}`);
            Toast.show('Failed to add student', 'error');
        }
    }
};

// Toast notifications
const Toast = {
    show(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close">&times;</button>
        `;
        
        container.appendChild(toast);
        
        toast.querySelector('.toast-close').addEventListener('click', () => this.remove(toast));
        setTimeout(() => this.remove(toast), 4000);
    },
    
    remove(toast) {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }
};

window.Toast = Toast;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => App.init());
