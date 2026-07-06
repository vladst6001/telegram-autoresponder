// Инициализация Telegram WebApp
const tg = window.Telegram?.WebApp;

if (tg) {
    tg.ready();
    tg.expand();
}

// Текущие настройки
let currentSettings = {};
let currentRules = [];

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadSettings();
});

// Переключение вкладок
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });

    // Показать/скрыть поле списка
    const replyModeInputs = document.querySelectorAll('input[name="reply_mode"]');
    replyModeInputs.forEach(input => {
        input.addEventListener('change', () => {
            const listInput = document.getElementById('list-input');
            if (input.value === 'whitelist' || input.value === 'blacklist') {
                listInput.style.display = 'flex';
            } else {
                listInput.style.display = 'none';
            }
        });
    });
}

// Загрузка настроек
async function loadSettings() {
    try {
        // В реальном приложении данные загружаются через bot API
        // Здесь используем дефолтные значения
        currentSettings = {
            enabled: true,
            notifications: true,
            reply_mode: 'all',
            owner_name: '',
            webapp_url: '',
            ai_prompt: 'Ты — вежливый помощник. Отвечай кратко, дружелюбно, но с лёгкой дистанцией. Если вопрос личный или ты не знаешь ответа — скажи: "Я передамOWNER_NAME, как только он появится". Не ври и не придумывай факты.',
            whitelist_users: '',
            blacklist_users: ''
        };

        currentRules = [
            { id: 1, phrase: 'привет', answer: 'Здравствуйте! Рад познакомиться 😊', match_type: 'exact' },
            { id: 2, phrase: 'как дела', answer: 'У меня всё хорошо, спасибо! А у вас?', match_type: 'partial' },
            { id: 3, phrase: 'ты кто', answer: 'Я — помощник OWNER_NAME. Отвечаю, когда он занят', match_type: 'exact' },
            { id: 4, phrase: 'когда он вернётся', answer: 'Точно не знаю, но я передам, что вы спрашивали', match_type: 'exact' },
            { id: 5, phrase: 'что ты умеешь', answer: 'Могу ответить на простые вопросы или передать сообщение', match_type: 'exact' },
            { id: 6, phrase: 'ты ии', answer: 'Да, меня настроили помогать с ответами', match_type: 'exact' },
            { id: 7, phrase: 'я тебя люблю', answer: 'Ой, я всего лишь бот 😅 Передам ваши тёплые слова!', match_type: 'exact' },
            { id: 8, phrase: 'ты глупый', answer: 'Возможно, но я стараюсь помочь 😄', match_type: 'exact' }
        ];

        updateUI();
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
    }
}

// Обновление UI
function updateUI() {
    // Главная
    document.getElementById('enabled').checked = currentSettings.enabled;
    document.getElementById('notifications').checked = currentSettings.notifications;
    document.getElementById('owner_name').value = currentSettings.owner_name || '';
    document.getElementById('webapp_url').value = currentSettings.webapp_url || '';

    // Режим
    const modeInput = document.querySelector(`input[name="reply_mode"][value="${currentSettings.reply_mode}"]`);
    if (modeInput) modeInput.checked = true;

    // Списки
    document.getElementById('user_list').value =
        currentSettings.reply_mode === 'whitelist'
            ? currentSettings.whitelist_users
            : currentSettings.blacklist_users || '';

    // ИИ
    document.getElementById('ai_prompt').value = currentSettings.ai_prompt || '';

    // Правила
    renderRules();
}

// Отрисовка правил
function renderRules() {
    const container = document.getElementById('rules-list');
    container.innerHTML = currentRules.map(rule => `
        <div class="rule-item">
            <div class="rule-info">
                <div class="rule-phrase">"${rule.phrase}"</div>
                <div class="rule-answer">→ ${rule.answer}</div>
                <div class="rule-type">${rule.match_type === 'exact' ? 'Точное' : 'Частичное'}</div>
            </div>
            <button class="delete-btn" onclick="deleteRule(${rule.id})">✕</button>
        </div>
    `).join('');
}

// Сохранение настроек
function saveSettings() {
    const mode = document.querySelector('input[name="reply_mode"]:checked').value;
    const listValue = document.getElementById('user_list').value;

    const settings = {
        enabled: document.getElementById('enabled').checked,
        notifications: document.getElementById('notifications').checked,
        owner_name: document.getElementById('owner_name').value,
        webapp_url: document.getElementById('webapp_url').value,
        reply_mode: mode,
        ai_prompt: document.getElementById('ai_prompt').value,
        whitelist_users: mode === 'whitelist' ? listValue : currentSettings.whitelist_users,
        blacklist_users: mode === 'blacklist' ? listValue : currentSettings.blacklist_users
    };

    currentSettings = { ...currentSettings, ...settings };

    // Отправка данных в бот
    if (tg) {
        tg.sendData(JSON.stringify({
            action: 'save_settings',
            settings: settings
        }));
    }

    showToast('✅ Настройки сохранены');
}

// Добавление правила
function addRule() {
    const phrase = document.getElementById('new_phrase').value.trim();
    const answer = document.getElementById('new_answer').value.trim();
    const matchType = document.querySelector('input[name="match_type"]:checked').value;

    if (!phrase || !answer) {
        showToast('❌ Заполните фразу и ответ');
        return;
    }

    // Отправка в бот
    if (tg) {
        tg.sendData(JSON.stringify({
            action: 'add_rule',
            phrase: phrase,
            answer: answer,
            match_type: matchType
        }));
    }

    // Локальное обновление
    const newId = Math.max(...currentRules.map(r => r.id), 0) + 1;
    currentRules.push({ id: newId, phrase, answer, match_type: matchType });
    renderRules();

    // Очистка формы
    document.getElementById('new_phrase').value = '';
    document.getElementById('new_answer').value = '';

    showToast('✅ Правило добавлено');
}

// Удаление правила
function deleteRule(id) {
    if (tg) {
        tg.sendData(JSON.stringify({
            action: 'delete_rule',
            rule_id: id
        }));
    }

    currentRules = currentRules.filter(r => r.id !== id);
    renderRules();
    showToast('✅ Правило удалено');
}

// Тест ИИ
function testAI() {
    if (tg) {
        tg.sendData(JSON.stringify({
            action: 'test_ai'
        }));
    }

    const resultDiv = document.getElementById('ai-test-result');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '⏳ Генерация ответа...';

    // Симуляция для демо
    setTimeout(() => {
        resultDiv.innerHTML = `
            <strong>Вопрос:</strong> Привет, как дела?<br>
            <strong>Ответ:</strong> У меня всё хорошо, спасибо! А у вас?
        `;
    }, 1500);
}

// Toast уведомление
function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 2000);
}
