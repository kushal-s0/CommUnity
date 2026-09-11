/* CommUnity — shared front-end behaviour (no dependencies). */
(function () {
    'use strict';

    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

    window.getCSRFToken = function () {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    };

    window.postJSON = async function (url, body) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRFToken': window.getCSRFToken(),
            },
            body: JSON.stringify(body || {}),
        });
        const data = await response.json().catch(() => ({}));
        return { ok: response.ok, status: response.status, data };
    };

    /* ---- Toasts ---- */
    const TOAST_ICONS = {
        success: 'fa-circle-check', error: 'fa-circle-exclamation',
        warning: 'fa-triangle-exclamation', info: 'fa-circle-info',
    };

    function dismissToast(toast) {
        toast.classList.add('leaving');
        setTimeout(() => toast.remove(), 250);
    }

    function armToast(toast) {
        $('.toast-close', toast)?.addEventListener('click', () => dismissToast(toast));
        if (!toast.classList.contains('toast-error')) {
            setTimeout(() => dismissToast(toast), 7000);
        }
    }

    window.showToast = function (message, kind = 'info') {
        let stack = $('.toast-stack');
        if (!stack) {
            stack = document.createElement('div');
            stack.className = 'toast-stack';
            stack.setAttribute('role', 'status');
            stack.setAttribute('aria-live', 'polite');
            document.body.appendChild(stack);
        }
        const toast = document.createElement('div');
        toast.className = `toast toast-${kind}`;
        toast.innerHTML = `<i class="fa-solid ${TOAST_ICONS[kind] || TOAST_ICONS.info}"></i>
            <div class="toast-body"></div><button type="button" class="toast-close" aria-label="Dismiss">&times;</button>`;
        $('.toast-body', toast).textContent = message;
        stack.appendChild(toast);
        armToast(toast);
    };

    $$('.toast').forEach(armToast);

    /* ---- Navigation ---- */
    const navToggle = $('[data-toggle="nav"]');
    const nav = $('#mainnav');
    navToggle?.addEventListener('click', () => {
        const open = nav.classList.toggle('open');
        navToggle.setAttribute('aria-expanded', String(open));
    });

    $$('[data-toggle="dropdown"]').forEach((button) => {
        button.addEventListener('click', (event) => {
            event.stopPropagation();
            const dropdown = button.closest('.dropdown');
            const open = dropdown.classList.toggle('open');
            button.setAttribute('aria-expanded', String(open));
        });
    });

    function closeDropdowns(except) {
        $$('.dropdown.open').forEach((dropdown) => {
            if (dropdown !== except) {
                dropdown.classList.remove('open');
                $('[data-toggle="dropdown"]', dropdown)?.setAttribute('aria-expanded', 'false');
            }
        });
    }

    document.addEventListener('click', (event) => closeDropdowns(event.target.closest('.dropdown')));

    /* ---- Confirmation for destructive forms ---- */
    document.addEventListener('submit', (event) => {
        const message = event.target.dataset.confirm;
        if (message && !window.confirm(message)) {
            event.preventDefault();
        }
    }, true);

    /* ---- Follow / unfollow ---- */
    $$('[data-follow]').forEach((button) => {
        button.addEventListener('click', async (event) => {
            event.preventDefault();
            button.disabled = true;
            const { ok, status, data } = await window.postJSON(button.dataset.follow);
            button.disabled = false;
            if (status === 401) {
                window.location = `${data.login_url}?next=${encodeURIComponent(window.location.pathname)}`;
                return;
            }
            if (!ok) {
                window.showToast(data.message || 'Something went wrong.', 'error');
                return;
            }
            button.classList.toggle('is-following', data.following);
            button.setAttribute('aria-pressed', String(data.following));
            const icon = $('i', button);
            if (icon) icon.className = `${data.following ? 'fa-solid' : 'fa-regular'} fa-star`;
            const label = $('.follow-label', button);
            if (label) label.textContent = data.following ? 'Following' : 'Follow';
            window.showToast(data.message, 'success');
        });
    });

    /* ---- Tabs ---- */
    $$('[data-tabs]').forEach((group) => {
        const tabs = $$('[role="tab"]', group);
        tabs.forEach((tab) => {
            tab.addEventListener('click', () => {
                tabs.forEach((other) => {
                    const selected = other === tab;
                    other.setAttribute('aria-selected', String(selected));
                    const panel = document.getElementById(other.getAttribute('aria-controls'));
                    if (panel) panel.hidden = !selected;
                });
                const url = new URL(window.location);
                url.searchParams.set('tab', tab.dataset.tab);
                history.replaceState(null, '', url);
            });
        });
    });

    /* ---- Lightbox for galleries ---- */
    let lightbox = null;
    function closeLightbox() {
        lightbox?.remove();
        lightbox = null;
    }
    $$('[data-lightbox]').forEach((link) => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            closeLightbox();
            lightbox = document.createElement('div');
            lightbox.className = 'lightbox';
            lightbox.innerHTML = '<img alt=""><button type="button" class="lightbox-close" aria-label="Close">&times;</button>';
            const image = $('img', lightbox);
            image.src = link.href;
            image.alt = link.dataset.caption || '';
            lightbox.addEventListener('click', closeLightbox);
            document.body.appendChild(lightbox);
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeDropdowns();
            closeLightbox();
        }
    });

    /* ---- Selected file names under file inputs ---- */
    $$('input[type="file"]').forEach((input) => {
        input.addEventListener('change', () => {
            let output = input.parentElement.querySelector('.file-names');
            if (!output) {
                output = document.createElement('p');
                output.className = 'help file-names';
                input.after(output);
            }
            output.textContent = Array.from(input.files).map((file) => file.name).join(', ');
        });
    });

    /* ---- Client-side list filter ---- */
    $$('[data-filter-input]').forEach((input) => {
        const target = document.querySelector(input.dataset.filterInput);
        if (!target) return;
        input.addEventListener('input', () => {
            const query = input.value.trim().toLowerCase();
            $$('[data-filter-item]', target).forEach((item) => {
                item.hidden = Boolean(query) && !item.textContent.toLowerCase().includes(query);
            });
        });
    });

    /* ---- People search used by team-management pages ---- */
    window.initPeopleSearch = function ({ input, results, searchUrl, renderRow }) {
        let timer = null;
        let latest = 0;

        async function run() {
            const query = input.value.trim();
            if (query.length < 2) {
                results.innerHTML = '<p class="muted small">Type at least 2 characters of a name or e-mail.</p>';
                return;
            }
            const requestId = ++latest;
            results.innerHTML = '<p class="muted small">Searching…</p>';
            const { data } = await window.postJSON(searchUrl, { query });
            if (requestId !== latest) return;
            results.innerHTML = '';
            if (!data.students || !data.students.length) {
                results.innerHTML = '<p class="muted small">No matching students.</p>';
                return;
            }
            data.students.forEach((student) => results.appendChild(renderRow(student)));
        }

        input.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(run, 250);
        });
    };

    window.personRow = function (student, actions) {
        const row = document.createElement('div');
        row.className = 'person search-row';
        const initials = (student.name || '?').split(/\s+/).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
        row.innerHTML = `<span class="avatar avatar-sm" aria-hidden="true"></span>
            <div class="person-text"><strong></strong><span class="muted small"></span></div>
            <div class="person-actions"></div>`;
        $('.avatar', row).textContent = initials;
        $('strong', row).textContent = student.name;
        $('.muted', row).textContent = `${student.email}${student.status ? ' · ' + student.status : ''}`;
        const holder = $('.person-actions', row);
        actions.forEach((action) => holder.appendChild(action));
        return row;
    };
})();
