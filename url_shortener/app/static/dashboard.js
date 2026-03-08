const API_URL = ""; 

// login/register
let isLoginMode = true;

function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    document.getElementById('formTitle').innerText = isLoginMode ? "Log In" : "Sign Up";
    document.getElementById('authBtn').innerText = isLoginMode ? "Log In" : "Sign Up";
    document.getElementById('switchText').innerText = isLoginMode ? "Don't have an account?" : "Already have an account?";
    document.getElementById('switchBtn').innerText = isLoginMode ? "Sign Up" : "Log In";
}

async function handleAuth() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorMsg = document.getElementById('errorMsg');
    
    const endpoint = isLoginMode ? "/token" : "/register";
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) throw new Error(data.detail || "Error");

        // сохраняем токен
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', username);
        
        // редирект в дашборд
        window.location.href = "/dashboard";
        
    } catch (e) {
        errorMsg.innerText = e.message;
        errorMsg.classList.remove('hidden');
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    window.location.href = "/";
}

// логика для dashboard

// проверка токена при загрузке страницы
document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname === "/dashboard") {
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = "/login";
            return;
        }
        document.getElementById('userDisplay').innerText = localStorage.getItem('username');
        loadLinks();
    }
});

// функция копирования текста в буфер обмена
function copyToClipboard(text, btnElement) {
    navigator.clipboard.writeText(text).then(() => {
        // меняем текст кнопки на "Copied!" на 2 секунды
        const originalText = btnElement.innerText;
        btnElement.innerText = "Copied!";
        btnElement.style.background = "#4CAF50";
        
        setTimeout(() => {
            btnElement.innerText = originalText;
            btnElement.style.background = "";
        }, 2000);
    });
}

async function loadLinks() {
    const token = localStorage.getItem('token');
    const response = await fetch('/links/my', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.status === 401) {
        logout(); 
        return;
    }

    const links = await response.json();
    const tbody = document.getElementById('linksList');
    tbody.innerHTML = '';

    links.forEach(link => {
        // собираем полную ссылку: протокол + домен + код
        const fullUrl = `${window.location.origin}/${link.short_code}`;
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <div class="short-link-wrapper">
                    <a href="${fullUrl}" target="_blank" class="short-link">${fullUrl}</a>
                    <button onclick="copyToClipboard('${fullUrl}', this)" class="btn-copy">Copy</button>
                </div>
            </td>
            <td class="orig-url" title="${link.original_url}">${link.original_url}</td>
            <td>${link.click_count}</td>
            <td>${link.is_active ? '<span class="status-active">Active</span>' : '<span class="status-expired">Expired</span>'}</td>
            <td>
                <button onclick="deleteLink('${link.short_code}')" class="btn-delete">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function createLinkFromDash() {
    const originalUrl = document.getElementById('dashOriginalUrl').value;
    const alias = document.getElementById('dashAlias').value;
    const token = localStorage.getItem('token');

    const body = { original_url: originalUrl };
    if (alias) body.custom_alias = alias;

    const response = await fetch('/links/shorten', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
    });

    if (response.ok) {
        document.getElementById('dashOriginalUrl').value = '';
        document.getElementById('dashAlias').value = '';
        loadLinks(); // перезагрузить список
    } else {
        alert("Error creating link");
    }
}

async function deleteLink(shortCode) {
    if(!confirm("Are you sure?")) return;
    
    const token = localStorage.getItem('token');
    await fetch(`/links/${shortCode}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    loadLinks();
}