/* ========================================
   SHEETDB API INTEGRATION
   ======================================== */

const StudentAPI = {
    getApiUrl() {
        return CONFIG.SHEETDB_API_URL;
    },
    
    isConfigured() {
        const url = this.getApiUrl();
        return url && !url.includes('YOUR_API_ID');
    },
    
    // Helper: Capitalize first letter of each word
    capitalizeName(name) {
        if (!name) return '';
        return name
            .toLowerCase()
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ')
            .trim();
    },
    
    // Helper: Capitalize first letter only
    capitalizeFirst(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    },
    
    async getAllStudents() {
        if (!this.isConfigured()) {
            throw new Error('API not configured');
        }
        const response = await fetch(this.getApiUrl());
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        return await response.json();
    },
    
    async getStudentByName(name) {
        if (!this.isConfigured()) throw new Error('API not configured');
        const searchUrl = `${this.getApiUrl()}/search?Name=*${encodeURIComponent(name)}*&casesensitive=false`;
        const response = await fetch(searchUrl);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        const data = await response.json();
        return data.length > 0 ? data[0] : null;
    },
    
    async addStudent(studentData) {
        if (!this.isConfigured()) throw new Error('API not configured');
        
        const math = parseInt(studentData.Math) || 0;
        const science = parseInt(studentData.Science) || 0;
        const english = parseInt(studentData.English) || 0;
        const programming = parseInt(studentData.Programming) || 0;
        const total = math + science + english + programming;
        const percentage = ((total / 400) * 100).toFixed(2);
        
        const dataToSend = {
            data: [{
                Name: this.capitalizeName(studentData.Name),
                Department: this.capitalizeFirst(studentData.Department),
                Year: studentData.Year,
                Section: studentData.Section.toUpperCase(),
                Math: math, Science: science, English: english, Programming: programming,
                Info: studentData.Info || '',
                Total: total, Percentage: percentage
            }]
        };
        
        const response = await fetch(this.getApiUrl(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dataToSend)
        });
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        return await response.json();
    },
    
    async updateStudent(name, updateData) {
        if (!this.isConfigured()) throw new Error('API not configured');
        
        const currentStudent = await this.getStudentByName(name);
        if (!currentStudent) throw new Error(`Student "${name}" not found`);
        
        const mergedData = { ...currentStudent, ...updateData };
        
        if (updateData.Math || updateData.Science || updateData.English || updateData.Programming) {
            const m = parseInt(mergedData.Math) || 0;
            const s = parseInt(mergedData.Science) || 0;
            const e = parseInt(mergedData.English) || 0;
            const p = parseInt(mergedData.Programming) || 0;
            mergedData.Total = m + s + e + p;
            mergedData.Percentage = ((mergedData.Total / 400) * 100).toFixed(2);
        }
        
        const updateUrl = `${this.getApiUrl()}/Name/${encodeURIComponent(currentStudent.Name)}`;
        const response = await fetch(updateUrl, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data: mergedData })
        });
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        return await response.json();
    },
    
    async getStudentTotal(name) {
        const student = await this.getStudentByName(name);
        if (!student) return null;
        return {
            name: student.Name, total: student.Total, percentage: student.Percentage,
            math: student.Math, science: student.Science, english: student.English, programming: student.Programming
        };
    }
};

window.StudentAPI = StudentAPI;
