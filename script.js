const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }
let currentSettings = {};
let currentRules = [];

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadSettings();
    document.getElementById('test_mode').addEventListener('change', function() {
        document.getElementById('test_hint').style.display = this.checked ? 'block' : 'none';
    });
});

function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });
    document.querySelectorAll('input[name="reply_mode"]').forEach(input => {
        input.addEventListener('change', () => {
            document.getElementById('list-input').style.display =
                (input.value === 'whitelist' || input.value === 'blacklist') ? 'flex' : 'none';
        });
    });
}

async function loadSettings() {
    currentSettings = {
        enabled: true, notifications: true, test_mode: false,
        reply_mode: 'all', owner_name: '', webapp_url: '',
        ai_prompt: '', whitelist_users: '', blacklist_users: ''
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
}

function updateUI() {
    document.getElementById('enabled').checked = currentSettings.enabled;
    document.getElementById('notifications').checked = currentSettings.notifications;
    document.getElementById('test_mode').checked = currentSettings.test_mode;
    document.getElementById('test_hint').style.display = currentSettings.test_mode ? 'block' : 'none';
    document.getElementById('owner_name').value = currentSettings.owner_name || '';
    document.getElementById('webapp_url').value = currentSettings.webapp_url || '';
    const modeInput = document.querySelector('input[name="reply_mode"][value="' + currentSettings.reply_mode + '"]');
    if (modeInput) modeInput.checked = true;
    document.getElementById('user_list').value =
        currentSettings.reply_mode === 'whitelist' ? currentSettings.whitelist_users :
        currentSettings.reply_mode === 'blacklist' ? currentSettings.blacklist_users : '';
    document.getElementById('ai_prompt').value = currentSettings.ai_prompt || '';
    renderRules();
}

function renderRules() {
    document.getElementById('rules-list').innerHTML = currentRules.map(rule =>
        '<div class="rule-item"><div class="rule-info"><div class="rule-phrase">"' + rule.phrase + '"</div>' +
        '<div class="rule-answer">→ ' + rule.answer + '</div>' +
        '<div class="rule-type">' + (rule.match_type === 'exact' ? 'Точное' : 'Частичное') + '</div></div>' +
        '<button class="delete-btn" onclick="deleteRule(' + rule.id + ')">✕</button></div>'
    ).join('');
}

function saveSettings() {
    const mode = document.querySelector('input[name="reply_mode"]:checked').value;
    const listValue = document.getElementById('user_list').value;
    const settings = {
        enabled: document.getElementById('enabled').checked,
        notifications: document.getElementById('notifications').checked,
        test_mode: document.getElementById('test_mode').checked,
        owner_name: document.getElementById('owner_name').value,
        webapp_url: document.getElementById('webapp_url').value,
        reply_mode: mode,
        ai_prompt: document.getElementById('ai_prompt').value,
        whitelist_users: mode === 'whitelist' ? listValue : currentSettings.whitelist_users,
        blacklist_users: mode === 'blacklist' ? listValue : currentSettings.blacklist_users
    };
    currentSettings = Object.assign(currentSettings, settings);
    if (tg) tg.sendData(JSON.stringify({ action: 'save_settings', settings: settings }));
    showToast('✅ Настройки сохранены');
}

function addRule() {
    const phrase = document.getElementById('new_phrase').value.trim();
    const answer = document.getElementById('new_answer').value.trim();
    const matchType = document.querySelector('input[name="match_type"]:checked').value;
    if (!phrase || !answer) { showToast('❌ Заполните фразу и ответ'); return; }
    if (tg) tg.sendData(JSON.stringify({ action: 'add_rule', phrase: phrase, answer: answer, match_type: matchType }));
    currentRules.push({ id: Math.max.apply(null, currentRules.map(function(r){return r.id})) + 1, phrase: phrase, answer: answer, match_type: matchType });
    renderRules();
    document.getElementById('new_phrase').value = '';
    document.getElementById('new_answer').value = '';
    showToast('✅ Правило добавлено');
}

function deleteRule(id) {
    if (tg) tg.sendData(JSON.stringify({ action: 'delete_rule', rule_id: id }));
    currentRules = currentRules.filter(function(r){return r.id !== id});
    renderRules();
    showToast('✅ Правило удалено');
}

function showToast(message) {
    var toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(function(){ toast.classList.remove('show'); }, 2000);
}
